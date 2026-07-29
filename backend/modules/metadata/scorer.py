"""
Metadata Analysis Module — Scoring Engine

The ``MetadataScorer`` calculates two scores from the extracted metadata,
validation issues, and observations:

* **metadata_score** — 0.0 (suspicious) → 1.0 (trustworthy)
* **confidence_score** — 0.0 (low confidence) → 1.0 (high confidence)

Scoring factors include EXIF field richness, timestamp validity, camera
information presence, GPS data, AI-generator signatures, and validation
issue severity.
"""

from __future__ import annotations

import logging
import time
from typing import List

from backend.modules.metadata.constants import (
    OBS_METADATA_REMOVED,
    OBS_SAVED_MIDJOURNEY,
    OBS_SAVED_STABLE_DIFFUSION,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)
from backend.modules.metadata.models import (
    ExifData,
    ExtractionResult,
    Observation,
    ScoreResult,
    ValidationIssue,
    ValidationResult,
)

logger = logging.getLogger("veritasx.modules.metadata.scorer")


class MetadataScorer:
    """Calculates metadata and confidence scores from analysis results.

    This class is stateless and safe to reuse across requests.
    """

    # Scoring weights (must sum to 1.0 for metadata_score components)
    WEIGHT_EXIF_RICHNESS: float = 0.25
    WEIGHT_CAMERA_INFO: float = 0.20
    WEIGHT_TIMESTAMPS: float = 0.15
    WEIGHT_GPS: float = 0.10
    WEIGHT_VALIDATION: float = 0.15
    WEIGHT_AI_SIGNATURES: float = 0.15

    # AI signature penalty (subtracted from metadata_score)
    AI_SIGNATURE_PENALTY: float = 0.50

    # Metadata removed penalty
    METADATA_REMOVED_PENALTY: float = 0.40

    def __init__(self) -> None:
        """Initialise the scorer."""
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_scores(
        self,
        extraction_result: ExtractionResult,
        validation_result: ValidationResult,
        observations: List[Observation],
        request_id: str,
    ) -> ScoreResult:
        """Calculate metadata_score and confidence_score.

        :param extraction_result: The result of metadata extraction.
        :param validation_result: The result of metadata validation.
        :param observations: List of forensic observations.
        :param request_id: Request ID for tracing.
        :return: ``ScoreResult`` containing both scores.
        """
        start = time.perf_counter()
        logger.info(f"[{request_id}] Starting metadata scoring...")

        exif = extraction_result.exif_data
        file_info = extraction_result.file_info

        # --- metadata_score calculation ---
        metadata_score = self._calculate_metadata_score(
            exif=exif,
            file_info=file_info,
            validation_result=validation_result,
            observations=observations,
        )

        # --- confidence_score calculation ---
        confidence_score = self._calculate_confidence_score(
            exif=exif,
            validation_result=validation_result,
            observations=observations,
        )

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            f"[{request_id}] Scoring complete in {elapsed_ms}ms | "
            f"metadata_score={metadata_score:.4f} | "
            f"confidence_score={confidence_score:.4f}"
        )

        return ScoreResult(
            metadata_score=metadata_score,
            confidence_score=confidence_score,
        )

    # ------------------------------------------------------------------
    # Metadata Score
    # ------------------------------------------------------------------

    def _calculate_metadata_score(
        self,
        exif: ExifData,
        file_info,
        validation_result: ValidationResult,
        observations: List[Observation],
    ) -> float:
        """Calculate the metadata_score (0.0 = suspicious, 1.0 = trustworthy).

        :param exif: Extracted EXIF data.
        :param file_info: File information.
        :param validation_result: Validation issues.
        :param observations: Forensic observations.
        :return: Score between 0.0 and 1.0.
        """
        score = 0.5  # Start at neutral

        # 1. EXIF richness (0 to WEIGHT_EXIF_RICHNESS)
        score += self._score_exif_richness(exif)

        # 2. Camera information presence (0 to WEIGHT_CAMERA_INFO)
        score += self._score_camera_info(exif)

        # 3. Timestamp validity (0 to WEIGHT_TIMESTAMPS)
        score += self._score_timestamps(exif)

        # 4. GPS presence (0 to WEIGHT_GPS)
        score += self._score_gps(exif)

        # 5. Validation issues (penalty, -WEIGHT_VALIDATION to 0)
        score += self._score_validation_issues(validation_result)

        # 6. AI signatures (major penalty)
        score += self._score_ai_signatures(observations)

        # Clamp to [0.0, 1.0]
        return round(max(0.0, min(1.0, score)), 4)

    def _score_exif_richness(self, exif: ExifData) -> float:
        """Score based on how many EXIF fields are present.

        :param exif: Extracted EXIF data.
        :return: Score contribution (0 to WEIGHT_EXIF_RICHNESS).
        """
        if not exif.has_exif:
            return -self.WEIGHT_EXIF_RICHNESS  # Full penalty for no EXIF

        # Score based on field count
        # 0-5 fields: 0% of weight
        # 6-10 fields: 50% of weight
        # 11-20 fields: 75% of weight
        # 21+ fields: 100% of weight
        field_count = exif.exif_field_count

        if field_count >= 21:
            return self.WEIGHT_EXIF_RICHNESS
        elif field_count >= 11:
            return self.WEIGHT_EXIF_RICHNESS * 0.75
        elif field_count >= 6:
            return self.WEIGHT_EXIF_RICHNESS * 0.50
        elif field_count >= 1:
            return self.WEIGHT_EXIF_RICHNESS * 0.25
        else:
            return -self.WEIGHT_EXIF_RICHNESS

    def _score_camera_info(self, exif: ExifData) -> float:
        """Score based on camera information presence.

        :param exif: Extracted EXIF data.
        :return: Score contribution (0 to WEIGHT_CAMERA_INFO).
        """
        has_make = exif.camera_make is not None and exif.camera_make != ""
        has_model = exif.camera_model is not None and exif.camera_model != ""

        if has_make and has_model:
            return self.WEIGHT_CAMERA_INFO
        elif has_make or has_model:
            return self.WEIGHT_CAMERA_INFO * 0.50
        else:
            return -self.WEIGHT_CAMERA_INFO * 0.50  # Penalty for missing camera info

    def _score_timestamps(self, exif: ExifData) -> float:
        """Score based on timestamp validity and presence.

        :param exif: Extracted EXIF data.
        :return: Score contribution (0 to WEIGHT_TIMESTAMPS).
        """
        from backend.modules.metadata.utils import parse_exif_timestamp, is_future_timestamp, is_impossible_date
        from datetime import datetime

        has_original = exif.datetime_original is not None and exif.datetime_original != ""
        has_digitized = exif.datetime_digitized is not None and exif.datetime_digitized != ""
        has_modified = exif.datetime_modified is not None and exif.datetime_modified != ""

        timestamp_count = sum([has_original, has_digitized, has_modified])

        if timestamp_count == 0:
            return -self.WEIGHT_TIMESTAMPS * 0.50  # Penalty for no timestamps

        # Check for invalid timestamps
        now = datetime.now()
        invalid_count = 0

        for ts_str in [exif.datetime_original, exif.datetime_digitized, exif.datetime_modified]:
            if ts_str:
                dt = parse_exif_timestamp(ts_str)
                if dt is None or is_impossible_date(dt) or is_future_timestamp(dt, now):
                    invalid_count += 1

        if invalid_count > 0:
            # Partial penalty for invalid timestamps
            return self.WEIGHT_TIMESTAMPS * (timestamp_count / 3) * 0.30

        # Full score for valid timestamps
        return self.WEIGHT_TIMESTAMPS * (timestamp_count / 3)

    def _score_gps(self, exif: ExifData) -> float:
        """Score based on GPS data presence.

        :param exif: Extracted EXIF data.
        :return: Score contribution (0 to WEIGHT_GPS).
        """
        if exif.gps is None:
            return -self.WEIGHT_GPS * 0.25  # Small penalty for no GPS (GPS is optional)
        elif exif.gps.latitude is not None and exif.gps.longitude is not None:
            return self.WEIGHT_GPS  # Full score for valid GPS
        else:
            return self.WEIGHT_GPS * 0.25  # Partial score for partial GPS

    def _score_validation_issues(self, validation_result: ValidationResult) -> float:
        """Score based on validation issues (penalty).

        :param validation_result: Validation issues.
        :return: Score contribution (0 to -WEIGHT_VALIDATION).
        """
        if validation_result.total_issues == 0:
            return self.WEIGHT_VALIDATION  # Bonus for no issues

        # Calculate penalty based on severity
        severity_weights = {
            SEVERITY_CRITICAL: 1.0,
            SEVERITY_HIGH: 0.7,
            SEVERITY_MEDIUM: 0.4,
            SEVERITY_LOW: 0.1,
        }

        penalty = 0.0
        for issue in validation_result.issues:
            weight = severity_weights.get(issue.severity, 0.3)
            penalty += weight * 0.15  # Each issue contributes up to 15% penalty

        penalty = min(penalty, self.WEIGHT_VALIDATION)
        return -penalty

    def _score_ai_signatures(self, observations: List[Observation]) -> float:
        """Score based on AI generator signatures (major penalty).

        :param observations: Forensic observations.
        :return: Score contribution (0 to -AI_SIGNATURE_PENALTY).
        """
        ai_observation_types = {
            OBS_SAVED_STABLE_DIFFUSION,
            OBS_SAVED_MIDJOURNEY,
        }

        for obs in observations:
            if obs.observation_type in ai_observation_types:
                # Major penalty for AI generator signatures
                return -self.AI_SIGNATURE_PENALTY

        # Check for metadata removed observation
        for obs in observations:
            if obs.observation_type == OBS_METADATA_REMOVED:
                return -self.METADATA_REMOVED_PENALTY

        return 0.0

    # ------------------------------------------------------------------
    # Confidence Score
    # ------------------------------------------------------------------

    def _calculate_confidence_score(
        self,
        exif: ExifData,
        validation_result: ValidationResult,
        observations: List[Observation],
    ) -> float:
        """Calculate the confidence_score (0.0 = low confidence, 1.0 = high confidence).

        Confidence is based on how much metadata is available and how
        clear the signals are.

        :param exif: Extracted EXIF data.
        :param validation_result: Validation issues.
        :param observations: Forensic observations.
        :return: Score between 0.0 and 1.0.
        """
        score = 0.5  # Start at neutral

        # 1. EXIF field count (more fields = higher confidence)
        field_count = exif.exif_field_count
        if field_count >= 21:
            score += 0.25
        elif field_count >= 11:
            score += 0.15
        elif field_count >= 6:
            score += 0.10
        elif field_count >= 1:
            score += 0.05
        else:
            score -= 0.15  # Low confidence when no EXIF

        # 2. Validation issues (fewer issues = higher confidence)
        if validation_result.total_issues == 0:
            score += 0.15
        else:
            # Penalty based on issue count
            penalty = min(validation_result.total_issues * 0.05, 0.20)
            score -= penalty

        # 3. Observations (clear observations = higher confidence)
        if observations:
            # More observations with high confidence = higher confidence
            avg_obs_confidence = sum(o.confidence for o in observations) / len(observations)
            score += 0.10 * avg_obs_confidence
        else:
            # No observations can mean either clean metadata or insufficient data
            # If we have rich EXIF, no observations is fine
            if field_count >= 10:
                score += 0.05
            else:
                score -= 0.05

        # 4. AI signature detection (high confidence when detected)
        ai_types = {OBS_SAVED_STABLE_DIFFUSION, OBS_SAVED_MIDJOURNEY}
        has_ai_obs = any(o.observation_type in ai_types for o in observations)
        if has_ai_obs:
            score += 0.15  # High confidence when AI signature is detected

        # Clamp to [0.0, 1.0]
        return round(max(0.0, min(1.0, score)), 4)
