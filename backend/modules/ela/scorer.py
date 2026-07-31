"""
Error Level Analysis Module — Scoring Engine

The ``ElaScorer`` calculates two scores from the ELA metrics and suspicious
regions:

* **ela_score** — 0.0 (highly suspicious) → 1.0 (consistent compression)
* **confidence_score** — 0.0 (low confidence) → 1.0 (high confidence)

Scoring factors include average error, standard deviation, high-error pixel
percentage, dynamic range, and suspicious region count.
"""

from __future__ import annotations

import logging
import time
from typing import List

from backend.modules.ela.constants import (
    AVG_ERROR_THRESHOLD,
    DYNAMIC_RANGE_THRESHOLD,
    HIGH_ERROR_PIXEL_PERCENTAGE_THRESHOLD,
    STD_DEV_THRESHOLD,
    WEIGHT_AVERAGE_ERROR,
    WEIGHT_DYNAMIC_RANGE,
    WEIGHT_HIGH_ERROR_PIXELS,
    WEIGHT_STD_DEV,
    WEIGHT_SUSPICIOUS_REGIONS,
    CONFIDENCE_PIXEL_TIER_1,
    CONFIDENCE_PIXEL_TIER_2,
    CONFIDENCE_PIXEL_TIER_3,
    JPEG_FORMATS,
    MAX_SUSPICIOUS_REGIONS,
)
from backend.modules.ela.models import (
    ElaMetrics,
    ElaProcessingResult,
    ScoreResult,
    SuspiciousRegion,
)

logger = logging.getLogger("veritasx.modules.ela.scorer")


class ElaScorer:
    """Calculates ELA score and confidence score from analysis results.

    This class is stateless and safe to reuse across requests.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_scores(
        self,
        processing_result: ElaProcessingResult,
        request_id: str,
    ) -> ScoreResult:
        """Calculate ela_score and confidence_score.

        :param processing_result: The result of ELA processing.
        :param request_id: Request ID for tracing.
        :return: ``ScoreResult`` containing both scores.
        """
        start = time.perf_counter()
        logger.info(f"[{request_id}] Starting ELA scoring...")

        metrics = processing_result.metrics
        regions = processing_result.suspicious_regions

        # --- ela_score calculation ---
        ela_score = self._calculate_ela_score(
            metrics=metrics,
            suspicious_regions=regions,
        )

        # --- confidence_score calculation ---
        confidence_score = self._calculate_confidence_score(
            processing_result=processing_result,
        )

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            f"[{request_id}] Scoring complete in {elapsed_ms}ms | "
            f"ela_score={ela_score:.4f} | "
            f"confidence_score={confidence_score:.4f}"
        )

        return ScoreResult(
            ela_score=ela_score,
            confidence_score=confidence_score,
        )

    # ------------------------------------------------------------------
    # ELA Score (0.0 = highly suspicious, 1.0 = consistent compression)
    # ------------------------------------------------------------------

    def _calculate_ela_score(
        self,
        metrics: ElaMetrics,
        suspicious_regions: List[SuspiciousRegion],
    ) -> float:
        """Calculate the ela_score (0.0 = suspicious, 1.0 = consistent).

        Each factor is normalised to 0–1 where 1.0 = consistent and 0.0 =
        suspicious, then combined via weighted sum.

        :param metrics: Computed ELA metrics.
        :param suspicious_regions: Detected suspicious regions.
        :return: Score between 0.0 and 1.0.
        """
        # 1. Average error (lower = more consistent)
        avg_error_component = self._normalize_inverse(
            metrics.average_error, AVG_ERROR_THRESHOLD
        )

        # 2. Standard deviation (lower = more consistent)
        std_dev_component = self._normalize_inverse(
            metrics.standard_deviation, STD_DEV_THRESHOLD
        )

        # 3. High error pixel percentage (lower = more consistent)
        high_error_pct_component = self._normalize_inverse(
            metrics.percentage_high_error_pixels,
            HIGH_ERROR_PIXEL_PERCENTAGE_THRESHOLD,
        )

        # 4. Dynamic range (lower = more consistent)
        dynamic_range_component = self._normalize_inverse(
            metrics.dynamic_range, DYNAMIC_RANGE_THRESHOLD
        )

        # 5. Suspicious regions (fewer = more consistent)
        region_component = self._normalize_inverse(
            len(suspicious_regions), MAX_SUSPICIOUS_REGIONS
        )

        # Weighted sum
        score = (
            avg_error_component * WEIGHT_AVERAGE_ERROR
            + std_dev_component * WEIGHT_STD_DEV
            + high_error_pct_component * WEIGHT_HIGH_ERROR_PIXELS
            + dynamic_range_component * WEIGHT_DYNAMIC_RANGE
            + region_component * WEIGHT_SUSPICIOUS_REGIONS
        )

        return round(max(0.0, min(1.0, score)), 4)

    # ------------------------------------------------------------------
    # Confidence Score (0.0 = low confidence, 1.0 = high confidence)
    # ------------------------------------------------------------------

    def _calculate_confidence_score(
        self,
        processing_result: ElaProcessingResult,
    ) -> float:
        """Calculate the confidence_score (0.0 = low, 1.0 = high).

        Confidence is based on:
        1. Image size (more pixels = more data = higher confidence)
        2. Image format (JPEG is native for ELA)
        3. Signal clarity (non-zero differences indicate analyzable data)

        :param processing_result: The result of ELA processing.
        :return: Score between 0.0 and 1.0.
        """
        score = 0.4  # Base confidence

        metrics = processing_result.metrics

        # 1. Image size factor
        total_pixels = processing_result.image_width * processing_result.image_height
        if total_pixels >= CONFIDENCE_PIXEL_TIER_3:
            score += 0.20
        elif total_pixels >= CONFIDENCE_PIXEL_TIER_2:
            score += 0.15
        elif total_pixels >= CONFIDENCE_PIXEL_TIER_1:
            score += 0.10

        # 2. Format factor (JPEG is native for ELA)
        if processing_result.image_format in JPEG_FORMATS:
            score += 0.20
        elif processing_result.image_format in ("PNG", "WEBP"):
            score += 0.10

        # 3. Signal clarity (non-zero differences)
        if metrics.maximum_error > 0:
            score += 0.10

        # 4. Degenerate case: if all metrics are zero, very low confidence
        if (
            metrics.average_error == 0.0
            and metrics.maximum_error == 0.0
            and total_pixels == 0
        ):
            score = 0.1

        return round(max(0.0, min(1.0, score)), 4)

    # ------------------------------------------------------------------
    # Helper Methods
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_inverse(value: float, threshold: float) -> float:
        """Normalise *value* against *threshold* where lower value → higher score.

        Returns 1.0 when value is 0, 0.0 when value >= threshold, and a
        linear interpolation in between.

        :param value: The metric value (non-negative).
        :param threshold: The value at which the score reaches 0.0.
        :return: Normalised score in [0.0, 1.0].
        """
        if threshold <= 0:
            return 0.0
        if value <= 0:
            return 1.0
        ratio = value / threshold
        return max(0.0, min(1.0, 1.0 - ratio))
