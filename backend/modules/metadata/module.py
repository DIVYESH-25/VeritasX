"""
Metadata Analysis Forensic Module

This module is the main entry point for the Metadata Analysis forensic engine.
It integrates the extraction, validation, analysis, and scoring layers into a
single ``MetadataAnalysisModule`` that plugs into the VeritasX Orchestrator.

Public Interface
----------------
    async def analyze(image_data: bytes, request_id: str) -> ModuleResult

The module follows Clean Architecture principles:
- Extraction, validation, analysis, and scoring are independent layers.
- Dependencies are injected (with sensible defaults).
- The public interface is stable and can be extended without modification.
"""

from __future__ import annotations

import io
import logging
import time
from typing import Any, Dict, Optional

from backend.modules.base import BaseForensicModule
from backend.modules.metadata.analyzer import MetadataAnalyzer
from backend.modules.metadata.constants import (
    MODULE_DESCRIPTION,
    MODULE_NAME,
)
from backend.modules.metadata.extractor import MetadataExtractor
from backend.modules.metadata.models import (
    ExifData,
    ExtractionResult,
    FileInfo,
    ImageInfo,
    MetadataResult,
    Observation,
    ValidationResult,
)
from backend.modules.metadata.scorer import MetadataScorer
from backend.modules.metadata.validator import MetadataValidator
from backend.schemas.models import ModuleResult, ModuleStatus

logger = logging.getLogger("veritasx.modules.metadata")


class MetadataAnalysisModule(BaseForensicModule):
    """Metadata Analysis forensic module for the VeritasX platform.

    Extracts, validates, and analyses image metadata (EXIF, XMP, ICC profiles,
    and AI generator signatures) to assess media provenance and detect
    forensic anomalies.

    This module is completely offline and does not require external APIs.

    Architecture
    ------------
    The module delegates to four independent layers:

    1. **Extractor** — Extracts file info, image info, and EXIF data from raw bytes.
    2. **Validator** — Validates extracted metadata and generates validation issues.
    3. **Analyzer** — Runs rule-based analysis to generate forensic observations.
    4. **Scorer** — Calculates metadata_score and confidence_score.

    Each layer is injected via the constructor, allowing for easy testing
    and customisation.
    """

    def __init__(
        self,
        enabled: bool = True,
        extractor: Optional[MetadataExtractor] = None,
        validator: Optional[MetadataValidator] = None,
        analyzer: Optional[MetadataAnalyzer] = None,
        scorer: Optional[MetadataScorer] = None,
    ) -> None:
        """Initialise the Metadata Analysis module.

        :param enabled: Whether the module is enabled for execution.
        :param extractor: Metadata extractor instance (default: new instance).
        :param validator: Metadata validator instance (default: new instance).
        :param analyzer: Metadata analyzer instance (default: new instance).
        :param scorer: Metadata scorer instance (default: new instance).
        """
        super().__init__(
            name=MODULE_NAME,
            description=MODULE_DESCRIPTION,
            enabled=enabled,
        )
        self._extractor: MetadataExtractor = extractor or MetadataExtractor()
        self._validator: MetadataValidator = validator or MetadataValidator()
        self._analyzer: MetadataAnalyzer = analyzer or MetadataAnalyzer()
        self._scorer: MetadataScorer = scorer or MetadataScorer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze(self, image_data: bytes, request_id: str) -> ModuleResult:
        """Perform metadata analysis on the provided image bytes.

        This method is called by the Orchestrator via the ``execute`` wrapper
        in ``BaseForensicModule``.  It orchestrates the extraction, validation,
        analysis, and scoring layers, and returns a standardised ``ModuleResult``.

        :param image_data: Raw image bytes to analyse.
        :param request_id: Unique request identifier for tracing.
        :return: ``ModuleResult`` containing the analysis output.
        """
        logger.info(f"[{request_id}] Metadata Analysis module started.")

        # Determine filename (not available in the interface, use a default)
        filename = "uploaded_image"

        try:
            # 1. Extraction
            extraction_start = time.perf_counter()
            extraction_result = self._extractor.extract(
                image_bytes=image_data,
                request_id=request_id,
                filename=filename,
            )
            extraction_time_ms = round((time.perf_counter() - extraction_start) * 1000, 2)
            logger.info(f"[{request_id}] Extraction time: {extraction_time_ms}ms")

            # 2. Validation
            validation_start = time.perf_counter()
            validation_result = self._validator.validate(extraction_result, request_id)
            validation_time_ms = round((time.perf_counter() - validation_start) * 1000, 2)
            logger.info(
                f"[{request_id}] Validation time: {validation_time_ms}ms | "
                f"Issues: {validation_result.total_issues}"
            )

            # 3. Analysis
            analysis_start = time.perf_counter()
            observations = self._analyzer.analyze(extraction_result, validation_result, request_id)
            analysis_time_ms = round((time.perf_counter() - analysis_start) * 1000, 2)
            logger.info(
                f"[{request_id}] Analysis time: {analysis_time_ms}ms | "
                f"Observations: {len(observations)}"
            )

            # 4. Scoring
            score_result = self._scorer.calculate_scores(
                extraction_result=extraction_result,
                validation_result=validation_result,
                observations=observations,
                request_id=request_id,
            )

            # 5. Build the final result
            metadata_result = self._build_metadata_result(
                extraction_result=extraction_result,
                validation_result=validation_result,
                observations=observations,
                metadata_score=score_result.metadata_score,
                confidence_score=score_result.confidence_score,
            )

            # The ModuleResult score is inverted: 0 = Real, 1 = Fake (AI-generated)
            # metadata_score is 0 = suspicious, 1 = trustworthy
            # So: score = 1.0 - metadata_score
            module_score = round(1.0 - score_result.metadata_score, 4)

            # Determine status message
            message = self._build_message(
                exif_field_count=extraction_result.exif_data.exif_field_count,
                observation_count=len(observations),
                validation_issue_count=validation_result.total_issues,
            )

            logger.info(
                f"[{request_id}] Metadata Analysis complete | "
                f"metadata_score={score_result.metadata_score:.4f} | "
                f"confidence={score_result.confidence_score:.4f} | "
                f"score={module_score:.4f} | "
                f"EXIF fields={extraction_result.exif_data.exif_field_count} | "
                f"observations={len(observations)}"
            )

            return ModuleResult(
                module=self.name,
                status=ModuleStatus.SUCCESS,
                score=module_score,
                confidence=score_result.confidence_score,
                message=message,
                data=metadata_result.model_dump(),
            )

        except Exception as exc:
            # This should never happen due to the exception safety in BaseForensicModule,
            # but we catch here as a final safety net.
            logger.error(
                f"[{request_id}] Metadata Analysis module failed: {exc}",
                exc_info=True,
            )
            return ModuleResult(
                module=self.name,
                status=ModuleStatus.ERROR,
                score=0.0,
                confidence=0.0,
                message=f"Metadata analysis failed: {str(exc)}",
                error_details=str(exc),
            )

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    def _build_metadata_result(
        self,
        extraction_result: ExtractionResult,
        validation_result: ValidationResult,
        observations: list[Observation],
        metadata_score: float,
        confidence_score: float,
    ) -> MetadataResult:
        """Build the final ``MetadataResult`` data structure.

        :param extraction_result: Extraction output.
        :param validation_result: Validation output.
        :param observations: Generated observations.
        :param metadata_score: Calculated metadata score.
        :param confidence_score: Calculated confidence score.
        :return: Populated ``MetadataResult``.
        """
        # Serialise validation result to dict
        validation_dict: Dict[str, Any] = {
            "total_issues": validation_result.total_issues,
            "issues_by_severity": validation_result.issues_by_severity,
            "issues": [issue.model_dump() for issue in validation_result.issues],
        }

        return MetadataResult(
            file=extraction_result.file_info,
            image=extraction_result.image_info,
            exif=extraction_result.exif_data,
            validation=validation_dict,
            observations=observations,
            metadata_score=metadata_score,
            confidence_score=confidence_score,
        )

    @staticmethod
    def _build_message(
        exif_field_count: int,
        observation_count: int,
        validation_issue_count: int,
    ) -> str:
        """Build a human-readable status message.

        :param exif_field_count: Number of EXIF fields extracted.
        :param observation_count: Number of observations generated.
        :param validation_issue_count: Number of validation issues found.
        :return: Status message string.
        """
        parts: list[str] = []

        if exif_field_count == 0:
            parts.append("No EXIF metadata found")
        else:
            parts.append(f"Extracted {exif_field_count} EXIF field(s)")

        if observation_count > 0:
            parts.append(f"generated {observation_count} observation(s)")

        if validation_issue_count > 0:
            parts.append(f"found {validation_issue_count} validation issue(s)")

        return "Metadata analysis completed successfully: " + ", ".join(parts) + "."
