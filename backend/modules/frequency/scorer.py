"""
Frequency Analysis Module — Scoring Engine

The ``FrequencyScorer`` calculates two scores from the frequency-domain
metrics:

* **frequency_score** — 0.0 (suspicious/synthetic) → 1.0 (consistent natural spectrum)
* **confidence_score** — 0.0 (low confidence) → 1.0 (high confidence)

Scoring factors include the energy ratio, spectral entropy, magnitude standard
deviation, horizontal/vertical balance, peak-to-mean ratio, and radial
symmetry.  Confidence is based on image size (more pixels = more data =
higher confidence) and whether the spectrum is analyzable.
"""

from __future__ import annotations

import logging
import time

from backend.modules.frequency.constants import (
    ENERGY_RATIO_HIGH_THRESHOLD,
    ENERGY_RATIO_LOW_THRESHOLD,
    FREQUENCY_PIXEL_TIER_1,
    FREQUENCY_PIXEL_TIER_2,
    FREQUENCY_PIXEL_TIER_3,
    FREQ_CONFIDENCE_MIN_HEIGHT,
    FREQ_CONFIDENCE_MIN_WIDTH,
    HV_BALANCE_ASYMMETRY_THRESHOLD,
    JPEG_FORMATS,
    MAGNITUDE_STD_HIGH_THRESHOLD,
    MAGNITUDE_STD_LOW_THRESHOLD,
    PEAK_TO_MEAN_HIGH_THRESHOLD,
    PEAK_TO_MEAN_LOW_THRESHOLD,
    PNG_FORMATS,
    RADIAL_SYMMETRY_HIGH_THRESHOLD,
    RADIAL_SYMMETRY_LOW_THRESHOLD,
    SPECTRAL_ENTROPY_HIGH_THRESHOLD,
    SPECTRAL_ENTROPY_LOW_THRESHOLD,
    WEBP_FORMATS,
    WEIGHT_ENERGY_RATIO,
    WEIGHT_HV_BALANCE,
    WEIGHT_MAGNITUDE_STD,
    WEIGHT_PEAK_TO_MEAN,
    WEIGHT_RADIAL_SYMMETRY,
    WEIGHT_SPECTRAL_ENTROPY,
)
from backend.modules.frequency.models import (
    FrequencyMetrics,
    ProcessingResult,
    ScoreResult,
)

logger = logging.getLogger("veritasx.modules.frequency.scorer")


class FrequencyScorer:
    """Calculates frequency_score and confidence_score from analysis results.

    This class is stateless and safe to reuse across requests.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_scores(
        self,
        processing_result: ProcessingResult,
        request_id: str,
    ) -> ScoreResult:
        """Calculate frequency_score and confidence_score.

        :param processing_result: The result of frequency processing.
        :param request_id: Request ID for tracing.
        :return: ``ScoreResult`` containing both scores.
        """
        start = time.perf_counter()
        logger.info(f"[{request_id}] Starting frequency scoring...")

        metrics = processing_result.metrics

        # --- frequency_score calculation ---
        frequency_score = self._calculate_frequency_score(metrics=metrics)

        # --- confidence_score calculation ---
        confidence_score = self._calculate_confidence_score(processing_result=processing_result)

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            f"[{request_id}] Scoring complete in {elapsed_ms}ms | "
            f"frequency_score={frequency_score:.4f} | "
            f"confidence_score={confidence_score:.4f}"
        )

        return ScoreResult(
            frequency_score=frequency_score,
            confidence_score=confidence_score,
        )

    # ------------------------------------------------------------------
    # Frequency Score (0.0 = suspicious, 1.0 = consistent natural spectrum)
    # ------------------------------------------------------------------

    def _calculate_frequency_score(
        self,
        metrics: FrequencyMetrics,
    ) -> float:
        """Calculate the frequency_score (0.0 = suspicious, 1.0 = consistent).

        Each factor is normalised to 0–1 where 1.0 = consistent natural spectrum
        and 0.0 = suspicious/synthetic.  Factors are combined via weighted sum.

        :param metrics: Computed frequency-domain metrics.
        :return: Score between 0.0 and 1.0.
        """
        # 1. Energy ratio (higher = more natural; lower = suspiciously flat)
        #    Normalise: ratio >= HIGH_THRESHOLD → 1.0, ratio <= LOW_THRESHOLD → 0.0
        energy_ratio_component = self._normalize_ratio(
            metrics.energy_ratio, ENERGY_RATIO_LOW_THRESHOLD, ENERGY_RATIO_HIGH_THRESHOLD
        )

        # 2. Spectral entropy (moderate is natural; extreme high or low is suspicious)
        #    Optimal range: 0.45–0.85; penalise outside this range
        entropy_component = self._score_spectral_entropy(metrics.spectral_entropy)

        # 3. Standard deviation of magnitude (higher = natural texture variation)
        #    Normalise: higher std = more natural, up to a threshold
        std_component = self._normalize_proportional(
            metrics.std_magnitude, MAGNITUDE_STD_HIGH_THRESHOLD
        )

        # 4. HV balance (balanced = natural; very asymmetric = suspicious)
        #    Normalise: ratio = 1.0 → 1.0; ratio >= HV_THRESHOLD → 0.0
        hv_component = self._normalize_inverse_threshold(
            abs(metrics.hv_balance_ratio - 1.0),
            HV_BALANCE_ASYMMETRY_THRESHOLD - 1.0,
        )

        # 5. Peak-to-mean ratio (moderate is natural; extremes are suspicious)
        #    Too high = periodic/structured; too low = overly smooth
        peak_component = self._score_peak_to_mean(metrics.peak_to_mean_ratio)

        # 6. Radial symmetry (moderate symmetry is natural; too high = synthetic)
        symmetry_component = self._score_radial_symmetry(metrics.radial_symmetry_score)

        # Weighted sum
        score = (
            energy_ratio_component * WEIGHT_ENERGY_RATIO
            + entropy_component * WEIGHT_SPECTRAL_ENTROPY
            + std_component * WEIGHT_MAGNITUDE_STD
            + hv_component * WEIGHT_HV_BALANCE
            + peak_component * WEIGHT_PEAK_TO_MEAN
            + symmetry_component * WEIGHT_RADIAL_SYMMETRY
        )

        return round(max(0.0, min(1.0, score)), 4)

    # ------------------------------------------------------------------
    # Confidence Score (0.0 = low confidence, 1.0 = high confidence)
    # ------------------------------------------------------------------

    def _calculate_confidence_score(
        self,
        processing_result: ProcessingResult,
    ) -> float:
        """Calculate the confidence_score (0.0 = low, 1.0 = high).

        Confidence is based on:
        1. Image size (more pixels = more data = higher confidence)
        2. Image format (JPEG is native for many forensic workflows)
        3. Signal clarity (non-zero metrics indicate analyzable data)
        4. Degenerate case handling (zero-size or corrupted images)

        :param processing_result: The result of frequency processing.
        :return: Score between 0.0 and 1.0.
        """
        score = 0.4  # Base confidence

        metrics = processing_result.metrics
        total_pixels = processing_result.image_width * processing_result.image_height

        # 1. Image size factor
        if total_pixels >= FREQUENCY_PIXEL_TIER_3:
            score += 0.20
        elif total_pixels >= FREQUENCY_PIXEL_TIER_2:
            score += 0.15
        elif total_pixels >= FREQUENCY_PIXEL_TIER_1:
            score += 0.10

        # 2. Minimum dimension check (too small = unreliable)
        if processing_result.image_width < FREQ_CONFIDENCE_MIN_WIDTH or processing_result.image_height < FREQ_CONFIDENCE_MIN_HEIGHT:
            score -= 0.15

        # 3. Format factor (JPEG is native for many forensic workflows)
        if processing_result.image_format in JPEG_FORMATS:
            score += 0.15
        elif processing_result.image_format in PNG_FORMATS or processing_result.image_format in WEBP_FORMATS:
            score += 0.10

        # 4. Signal clarity (non-zero metrics indicate analyzable data)
        if metrics.max_magnitude > 0 or metrics.mean_magnitude > 0:
            score += 0.10

        # 5. Degenerate case: if all metrics are zero, very low confidence
        if (
            metrics.mean_magnitude == 0.0
            and metrics.max_magnitude == 0.0
            and total_pixels == 0
        ):
            score = 0.1

        return round(max(0.0, min(1.0, score)), 4)

    # ------------------------------------------------------------------
    # Helper Methods
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_ratio(value: float, low: float, high: float) -> float:
        """Normalise *value* where values >= *high* score 1.0 and values <= *low* score 0.0.

        Linear interpolation between *low* and *high* thresholds.

        :param value: The metric value.
        :param low: Threshold below which score = 0.0.
        :param high: Threshold at or above which score = 1.0.
        :return: Normalised score in [0.0, 1.0].
        """
        if high <= low:
            return 0.5
        if value <= low:
            return 0.0
        if value >= high:
            return 1.0
        return (value - low) / (high - low)

    @staticmethod
    def _normalize_proportional(value: float, threshold: float) -> float:
        """Normalise *value* where higher values score higher, capped at threshold.

        Returns 1.0 when *value* >= *threshold*, else ``value / threshold``.

        :param value: The metric value (non-negative).
        :param threshold: The value at which the score reaches 1.0.
        :return: Normalised score in [0.0, 1.0].
        """
        if threshold <= 0:
            return 0.0
        if value <= 0:
            return 0.0
        return max(0.0, min(1.0, value / threshold))

    @staticmethod
    def _normalize_inverse(value: float, threshold: float) -> float:
        """Normalise *value* where lower values score higher.

        Returns 1.0 when *value* is 0, 0.0 when *value* >= *threshold*.

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

    @staticmethod
    def _normalize_inverse_threshold(value: float, threshold: float) -> float:
        """Alias for :meth:`_normalize_inverse` for clarity in HV balance scoring.

        :param value: The absolute deviation from ideal (e.g. abs(ratio - 1.0)).
        :param threshold: The deviation at which the score reaches 0.0.
        :return: Normalised score in [0.0, 1.0].
        """
        return FrequencyScorer._normalize_inverse(value, threshold)

    @staticmethod
    def _score_spectral_entropy(entropy: float) -> float:
        """Score spectral entropy where moderate values are more natural.

        Optimal range: 0.45–0.85.  Values outside this range are penalised.

        :param entropy: Normalised spectral entropy in [0, 1].
        :return: Score in [0.0, 1.0].
        """
        if 0.45 <= entropy <= 0.85:
            # Full score in the optimal range
            return 1.0
        elif entropy < 0.45:
            # Scale up from 0 to 0.45
            return entropy / 0.45
        else:
            # Scale down from 0.85 to 1.0
            return max(0.0, 1.0 - (entropy - 0.85) / 0.15)

    @staticmethod
    def _score_peak_to_mean(ratio: float) -> float:
        """Score peak-to-mean ratio where moderate values indicate natural texture.

        Too high (> HIGH_THRESHOLD) = periodic/structured (suspicious)
        Too low (< LOW_THRESHOLD) = overly smooth (suspicious for AI images)
        Moderate in between = natural

        :param ratio: Peak-to-mean ratio.
        :return: Score in [0.0, 1.0].
        """
        if ratio > PEAK_TO_MEAN_HIGH_THRESHOLD:
            # Linear penalty for excessive peaks
            excess = (ratio - PEAK_TO_MEAN_HIGH_THRESHOLD) / PEAK_TO_MEAN_HIGH_THRESHOLD
            return max(0.0, 1.0 - excess)
        elif ratio < PEAK_TO_MEAN_LOW_THRESHOLD:
            # Penalty for being too flat
            if ratio <= 0:
                return 0.0
            return ratio / PEAK_TO_MEAN_LOW_THRESHOLD
        else:
            # Optimal range - full score
            return 1.0

    @staticmethod
    def _score_radial_symmetry(symmetry: float) -> float:
        """Score radial symmetry where moderate symmetry is natural.

        Too high (> HIGH_THRESHOLD) = overly symmetric (can indicate synthetic)
        Too low (< LOW_THRESHOLD) = asymmetric (can indicate artifacts)

        :param symmetry: Radial symmetry score in [0, 1].
        :return: Score in [0.0, 1.0].
        """
        if symmetry < RADIAL_SYMMETRY_LOW_THRESHOLD:
            return 0.5
        elif symmetry > RADIAL_SYMMETRY_HIGH_THRESHOLD:
            # Penalise excessive symmetry
            excess = (symmetry - RADIAL_SYMMETRY_HIGH_THRESHOLD) / (1.0 - RADIAL_SYMMETRY_HIGH_THRESHOLD)
            return max(0.0, 0.5 - excess * 0.5)
        else:
            return 1.0
