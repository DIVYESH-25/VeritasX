"""
Error Level Analysis Forensic Module

This module is the main entry point for the Error Level Analysis forensic
engine.  It integrates the processing, visualization, analysis, and scoring
layers into a single ``ErrorLevelAnalysisModule`` that plugs into the
VeritasX Orchestrator.

Public Interface
----------------
    async def analyze(image_data: bytes, request_id: str) -> ModuleResult

The module follows Clean Architecture principles:
- Processing, visualization, analysis, and scoring are independent layers.
- Dependencies are injected (with sensible defaults).
- The public interface is stable and can be extended without modification.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from backend.modules.base import BaseForensicModule
from backend.modules.ela.analyzer import ElaAnalyzer
from backend.modules.ela.constants import (
    ELA_JPEG_QUALITY,
    MODULE_DESCRIPTION,
    MODULE_NAME,
)
from backend.modules.ela.models import (
    ElaResult,
    ScoreResult,
)
from backend.modules.ela.processor import ElaProcessor
from backend.modules.ela.scorer import ElaScorer
from backend.modules.ela.visualization import ElaVisualizer
from backend.schemas.models import ModuleResult, ModuleStatus

logger = logging.getLogger("veritasx.modules.ela")


class ErrorLevelAnalysisModule(BaseForensicModule):
    """Error Level Analysis (ELA) forensic module for the VeritasX platform.

    Performs Error Level Analysis to detect compression-level anomalies
    across image regions, identifying potential localised editing,
    re-compression, and synthetic generation indicators.

    The module is completely offline and does not require external APIs.

    Architecture
    ------------
    The module delegates to four independent layers:

    1. **Processor** — Implements the standard ELA algorithm: decode,
       RGB-convert, JPEG re-compress at configurable quality, compute
       absolute pixel differences, normalise, enhance, and produce the ELA
       image.  Also computes statistical metrics and detects suspicious
       regions.
    2. **Visualizer** — Converts the ELA numpy array into a base64-encoded
       image for API/frontend consumption.
    3. **Analyzer** — Generates forensic observations from the metrics and
       suspicious regions.
    4. **Scorer** — Calculates ela_score (0.0 = suspicious, 1.0 =
       consistent) and confidence_score.

    Each layer is injected via the constructor, allowing for easy testing
    and customisation.
    """

    def __init__(
        self,
        enabled: bool = True,
        jpeg_quality: int = ELA_JPEG_QUALITY,
        processor: Optional[ElaProcessor] = None,
        analyzer: Optional[ElaAnalyzer] = None,
        scorer: Optional[ElaScorer] = None,
        visualizer: Optional[ElaVisualizer] = None,
    ) -> None:
        """Initialise the Error Level Analysis module.

        :param enabled: Whether the module is enabled for execution.
        :param jpeg_quality: JPEG quality (1–100) for ELA re-compression.
        :param processor: ELA processor instance (default: new instance).
        :param analyzer: ELA analyzer instance (default: new instance).
        :param scorer: ELA scorer instance (default: new instance).
        :param visualizer: ELA visualizer instance (default: new instance).
        """
        super().__init__(
            name=MODULE_NAME,
            description=MODULE_DESCRIPTION,
            enabled=enabled,
        )
        self._jpeg_quality: int = jpeg_quality
        self._processor: ElaProcessor = processor or ElaProcessor(jpeg_quality=jpeg_quality)
        self._analyzer: ElaAnalyzer = analyzer or ElaAnalyzer()
        self._scorer: ElaScorer = scorer or ElaScorer()
        self._visualizer: ElaVisualizer = visualizer or ElaVisualizer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze(self, image_data: bytes, request_id: str) -> ModuleResult:
        """Perform Error Level Analysis on the provided image bytes.

        This method is called by the Orchestrator via the ``execute`` wrapper
        in ``BaseForensicModule``.  It orchestrates the processing,
        visualization, analysis, and scoring layers, and returns a
        standardised ``ModuleResult``.

        :param image_data: Raw image bytes to analyse.
        :param request_id: Unique request identifier for tracing.
        :return: ``ModuleResult`` containing the analysis output.
        """
        logger.info(f"[{request_id}] Error Level Analysis module started.")

        try:
            # 1. Processing (core ELA algorithm)
            processing_start = time.perf_counter()
            processing_result = self._processor.process(
                image_data=image_data,
                request_id=request_id,
            )
            processing_time_ms = round((time.perf_counter() - processing_start) * 1000, 2)
            logger.info(f"[{request_id}] Processing time: {processing_time_ms}ms")

            # 2. Visualization (generate base64 ELA image)
            viz_start = time.perf_counter()
            ela_image_data = self._visualizer.generate_ela_image(
                ela_array=processing_result.ela_image,
                request_id=request_id,
            )
            viz_time_ms = round((time.perf_counter() - viz_start) * 1000, 2)
            logger.info(f"[{request_id}] Visualization time: {viz_time_ms}ms")

            # 3. Analysis (generate observations)
            analysis_start = time.perf_counter()
            observations = self._analyzer.analyze(
                processing_result=processing_result,
                request_id=request_id,
            )
            analysis_time_ms = round((time.perf_counter() - analysis_start) * 1000, 2)
            logger.info(
                f"[{request_id}] Analysis time: {analysis_time_ms}ms | "
                f"Observations: {len(observations)}"
            )

            # 4. Scoring
            score_result: ScoreResult = self._scorer.calculate_scores(
                processing_result=processing_result,
                request_id=request_id,
            )

            # 5. Build the final result
            ela_result = self._build_ela_result(
                processing_result=processing_result,
                observations=observations,
                ela_image_data=ela_image_data,
                score_result=score_result,
            )

            # The ModuleResult score is inverted: 0 = Real, 1 = Fake (AI-generated)
            # ela_score is 0 = suspicious, 1 = consistent compression
            # So: score = 1.0 - ela_score
            module_score = round(1.0 - score_result.ela_score, 4)

            # Determine status message
            message = self._build_message(
                metrics=processing_result.metrics,
                observation_count=len(observations),
                region_count=len(processing_result.suspicious_regions),
            )

            logger.info(
                f"[{request_id}] ELA complete | "
                f"ela_score={score_result.ela_score:.4f} | "
                f"confidence={score_result.confidence_score:.4f} | "
                f"score={module_score:.4f} | "
                f"observations={len(observations)} | "
                f"regions={len(processing_result.suspicious_regions)}"
            )

            return ModuleResult(
                module=self.name,
                status=ModuleStatus.SUCCESS,
                score=module_score,
                confidence=score_result.confidence_score,
                message=message,
                data=ela_result.model_dump(),
            )

        except Exception as exc:
            # This should never happen due to the exception safety in
            # BaseForensicModule, but we catch here as a final safety net.
            logger.error(
                f"[{request_id}] ELA module failed: {exc}",
                exc_info=True,
            )
            return ModuleResult(
                module=self.name,
                status=ModuleStatus.ERROR,
                score=0.0,
                confidence=0.0,
                message=f"ELA analysis failed: {str(exc)}",
                error_details=str(exc),
            )

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    def _build_ela_result(
        self,
        processing_result,
        observations: list,
        ela_image_data,
        score_result: ScoreResult,
    ) -> ElaResult:
        """Build the final ``ElaResult`` data structure.

        :param processing_result: ELA processing result.
        :param observations: Generated observations.
        :param ela_image_data: Base64 ELA image data (or None).
        :param score_result: Calculated scores.
        :return: Populated ``ElaResult``.
        """
        return ElaResult(
            jpeg_quality=self._jpeg_quality,
            metrics=processing_result.metrics,
            observations=observations,
            ela_image=ela_image_data,
            suspicious_regions=processing_result.suspicious_regions,
            ela_score=score_result.ela_score,
            confidence_score=score_result.confidence_score,
        )

    @staticmethod
    def _build_message(
        metrics,
        observation_count: int,
        region_count: int,
    ) -> str:
        """Build a human-readable status message.

        :param metrics: ELA metrics.
        :param observation_count: Number of observations generated.
        :param region_count: Number of suspicious regions detected.
        :return: Status message string.
        """
        parts: list[str] = []

        parts.append(
            f"Average error: {metrics.average_error:.2f}, "
            f"std dev: {metrics.standard_deviation:.2f}"
        )

        if observation_count > 0:
            parts.append(f"generated {observation_count} observation(s)")

        if region_count > 0:
            parts.append(f"detected {region_count} suspicious region(s)")

        return "ELA completed successfully: " + ", ".join(parts) + "."
