"""
Frequency Analysis Forensic Module

This module is the main entry point for the Frequency Domain Analysis
forensic engine.  It integrates the processing, visualization, analysis,
and scoring layers into a single ``FrequencyAnalysisModule`` that plugs
into the VeritasX Orchestrator.

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
from backend.modules.frequency.analyzer import FrequencyAnalyzer
from backend.modules.frequency.constants import (
    APPLY_HANN_WINDOW,
    FFT_MAX_DIMENSION,
    MODULE_DESCRIPTION,
    MODULE_NAME,
)
from backend.modules.frequency.models import (
    FrequencyObservation,
    FrequencyResult,
)
from backend.modules.frequency.processor import FrequencyProcessor
from backend.modules.frequency.scorer import FrequencyScorer
from backend.modules.frequency.visualization import FrequencyVisualizer
from backend.schemas.models import ModuleResult, ModuleStatus

logger = logging.getLogger("veritasx.modules.frequency")


class FrequencyAnalysisModule(BaseForensicModule):
    """Frequency Domain Analysis module for the VeritasX platform.

    Performs FFT-based frequency-domain analysis to detect periodic
    structures, checkerboard artifacts, aliasing, banding, ringing,
    and other frequency-domain anomalies that may indicate AI synthesis
    or digital manipulation.

    The module is completely offline and does not require external APIs.

    Architecture
    ------------
    The module delegates to four independent layers:

    1. **Processor** — Implements the FFT pipeline: decode, grayscale
       convert, optional Hann windowing, 2D FFT, fftshift, log-scaled
       magnitude spectrum, and frequency-domain metric computation.
    2. **Visualizer** — Converts the magnitude spectrum numpy array into
       a base64-encoded PNG for API/frontend consumption.
    3. **Analyzer** — Rule-based forensic observation engine operating
       on the computed metrics.
    4. **Scorer** — Calculates frequency_score (0.0 = suspicious,
       1.0 = consistent) and confidence_score.

    Each layer is injected via the constructor, allowing for easy testing
    and customisation.
    """

    def __init__(
        self,
        enabled: bool = True,
        max_dimension: int = FFT_MAX_DIMENSION,
        apply_hann: bool = APPLY_HANN_WINDOW,
        processor: Optional[FrequencyProcessor] = None,
        analyzer: Optional[FrequencyAnalyzer] = None,
        scorer: Optional[FrequencyScorer] = None,
        visualizer: Optional[FrequencyVisualizer] = None,
    ) -> None:
        """Initialise the Frequency Analysis module.

        :param enabled: Whether the module is enabled for execution.
        :param max_dimension: Maximum width/height for FFT processing.
        :param apply_hann: Whether to apply a Hann window before FFT.
        :param processor: Frequency processor instance (default: new instance).
        :param analyzer: Frequency analyzer instance (default: new instance).
        :param scorer: Frequency scorer instance (default: new instance).
        :param visualizer: Frequency visualizer instance (default: new instance).
        """
        super().__init__(
            name=MODULE_NAME,
            description=MODULE_DESCRIPTION,
            enabled=enabled,
        )
        self._max_dimension: int = max_dimension
        self._apply_hann: bool = apply_hann
        self._processor: FrequencyProcessor = processor or FrequencyProcessor(
            max_dimension=max_dimension,
            apply_hann=apply_hann,
        )
        self._analyzer: FrequencyAnalyzer = analyzer or FrequencyAnalyzer()
        self._scorer: FrequencyScorer = scorer or FrequencyScorer()
        self._visualizer: FrequencyVisualizer = visualizer or FrequencyVisualizer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze(self, image_data: bytes, request_id: str) -> ModuleResult:
        """Perform frequency domain analysis on the provided image bytes.

        This method is called by the Orchestrator via the ``execute`` wrapper
        in ``BaseForensicModule``.  It orchestrates the processing,
        visualization, analysis, and scoring layers, and returns a
        standardised ``ModuleResult``.

        :param image_data: Raw image bytes to analyse.
        :param request_id: Unique request identifier for tracing.
        :return: ``ModuleResult`` containing the analysis output.
        """
        logger.info(f"[{request_id}] Frequency Analysis module started.")

        try:
            # 1. Processing (core FFT pipeline)
            processing_start = time.perf_counter()
            processing_result = self._processor.process(
                image_data=image_data,
                request_id=request_id,
            )
            processing_time_ms = round((time.perf_counter() - processing_start) * 1000, 2)
            logger.info(f"[{request_id}] Processing time: {processing_time_ms}ms")

            # 2. Visualization (generate base64 FFT spectrum image)
            viz_start = time.perf_counter()
            spectrum_image = self._visualizer.generate_spectrum_image(
                magnitude_spectrum=processing_result.magnitude_spectrum,
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
            score_result = self._scorer.calculate_scores(
                processing_result=processing_result,
                request_id=request_id,
            )

            # 5. Build the final result
            frequency_result = self._build_frequency_result(
                processing_result=processing_result,
                observations=observations,
                spectrum_image=spectrum_image,
                score_result=score_result,
            )

            # The ModuleResult score is inverted: 0 = Real, 1 = Fake (AI-generated)
            # frequency_score is 0 = suspicious, 1 = consistent natural spectrum
            # So: score = 1.0 - frequency_score
            module_score = round(1.0 - score_result.frequency_score, 4)

            # Determine status message
            message = self._build_message(
                metrics=processing_result.metrics,
                observation_count=len(observations),
            )

            logger.info(
                f"[{request_id}] Frequency Analysis complete | "
                f"frequency_score={score_result.frequency_score:.4f} | "
                f"confidence={score_result.confidence_score:.4f} | "
                f"score={module_score:.4f} | "
                f"observations={len(observations)} | "
                f"energy_ratio={processing_result.metrics.energy_ratio:.4f}"
            )

            return ModuleResult(
                module=self.name,
                status=ModuleStatus.SUCCESS,
                score=module_score,
                confidence=score_result.confidence_score,
                message=message,
                data=frequency_result.model_dump(),
            )

        except Exception as exc:
            # This should never happen due to the exception safety in
            # BaseForensicModule, but we catch here as a final safety net.
            logger.error(
                f"[{request_id}] Frequency Analysis module failed: {exc}",
                exc_info=True,
            )
            return ModuleResult(
                module=self.name,
                status=ModuleStatus.ERROR,
                score=0.0,
                confidence=0.0,
                message=f"Frequency analysis failed: {str(exc)}",
                error_details=str(exc),
            )

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    def _build_frequency_result(
        self,
        processing_result,
        observations: list,
        spectrum_image,
        score_result,
    ):
        """Build the final ``FrequencyResult`` data structure.

        :param processing_result: Frequency processing result.
        :param observations: Generated observations.
        :param spectrum_image: Base64 FFT spectrum image (or None).
        :param score_result: Calculated scores.
        :return: Populated ``FrequencyResult``.
        """
        return FrequencyResult(
            metrics=processing_result.metrics,
            observations=observations,
            fft_spectrum=spectrum_image,
            frequency_score=score_result.frequency_score,
            confidence_score=score_result.confidence_score,
        )

    @staticmethod
    def _build_message(
        metrics,
        observation_count: int,
    ) -> str:
        """Build a human-readable status message.

        :param metrics: Frequency metrics.
        :param observation_count: Number of observations generated.
        :return: Status message string.
        """
        parts: list[str] = []

        parts.append(
            f"Energy ratio: {metrics.energy_ratio:.2f}, "
            f"spectral entropy: {metrics.spectral_entropy:.4f}"
        )

        if observation_count > 0:
            parts.append(f"generated {observation_count} observation(s)")

        return "Frequency analysis completed successfully: " + ", ".join(parts) + "."
