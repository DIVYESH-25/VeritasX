"""
Error Level Analysis Module — Processing Layer

The ``ElaProcessor`` implements the standard ELA algorithm:

1.  Decode the image (Pillow).
2.  Convert to RGB.
3.  Save a temporary JPEG at a configurable quality.
4.  Reload the compressed image.
5.  Compute the absolute pixel-wise difference.
6.  Normalize the differences to the 0–255 range.
7.  Enhance visibility of compression artifacts.
8.  Produce the final ELA image (RGB uint8 array).
9.  Compute statistical metrics.
10. Detect suspicious regions via connected-component analysis.

The implementation is deterministic and configurable.  No temporary files
are written to disk — all intermediate JPEG data is held in memory
(``BytesIO``), which serves as the "temporary JPEG" and is garbage
collected automatically.
"""

from __future__ import annotations

import io
import logging
import time
from typing import List, Tuple

import cv2
import numpy as np
from PIL import Image

from backend.modules.ela.constants import (
    ELA_JPEG_QUALITY,
    HIGH_ERROR_PIXEL_THRESHOLD,
    MAX_SUSPICIOUS_REGIONS,
    REGION_THRESHOLD_SIGMA,
    SUSPICIOUS_REGION_MIN_AREA,
    SUSPICIOUS_REGION_MIN_INTENSITY,
)
from backend.modules.ela.models import (
    BoundingBox,
    ElaMetrics,
    ElaProcessingResult,
    SuspiciousRegion,
)
from backend.modules.ela.utils import (
    convert_to_rgb,
    load_image_from_bytes,
    pil_image_to_array,
)

logger = logging.getLogger("veritasx.modules.ela.processor")


class ElaProcessor:
    """Performs the core Error Level Analysis algorithm.

    This class is stateless (apart from the configurable JPEG quality) and
    safe to reuse across requests.
    """

    def __init__(self, jpeg_quality: int = ELA_JPEG_QUALITY) -> None:
        """Initialise the ELA processor.

        :param jpeg_quality: JPEG quality (1–100) used for re-compression.
        """
        self._jpeg_quality: int = jpeg_quality

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        image_data: bytes,
        request_id: str,
    ) -> ElaProcessingResult:
        """Run the full ELA pipeline on *image_data*.

        :param image_data: Raw image bytes (JPEG, PNG, WEBP, etc.).
        :param request_id: Unique request identifier for tracing.
        :return: ``ElaProcessingResult`` containing the ELA arrays, metrics,
                 suspicious regions, and source image metadata.
        """
        start = time.perf_counter()
        logger.info(
            f"[{request_id}] ELA processing started "
            f"({len(image_data)} bytes, JPEG quality={self._jpeg_quality})"
        )

        # 1. Decode image
        pil_image = load_image_from_bytes(image_data)
        if pil_image is None:
            logger.warning(f"[{request_id}] Image could not be decoded. Using fallback.")
            return self._fallback_result(image_data, request_id)

        # Record source metadata
        image_format = pil_image.format or "UNKNOWN"
        image_mode = pil_image.mode
        width, height = pil_image.size

        # 2. Convert to RGB
        rgb_image = convert_to_rgb(pil_image)

        # 3-8. Compute ELA image and difference
        ela_image, ela_gray, diff = self._compute_ela(rgb_image, self._jpeg_quality)

        # Pre-compute 2D max channel difference matrix ONCE for metrics and region detection
        diff_max = diff.max(axis=2)

        # 9. Compute metrics
        metrics = self._compute_metrics(diff, ela_gray, diff_max)

        # 10. Detect suspicious regions
        regions = self._detect_suspicious_regions(ela_gray, diff_max)

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            f"[{request_id}] ELA processing complete in {elapsed_ms}ms | "
            f"avg_error={metrics.average_error:.2f} | "
            f"max_error={metrics.maximum_error:.2f} | "
            f"std={metrics.standard_deviation:.2f} | "
            f"regions={len(regions)}"
        )

        return ElaProcessingResult(
            ela_image=ela_image,
            ela_gray=ela_gray,
            diff=diff,
            metrics=metrics,
            suspicious_regions=regions,
            image_width=width,
            image_height=height,
            image_format=image_format,
            image_mode=image_mode,
        )

    # ------------------------------------------------------------------
    # ELA Algorithm
    # ------------------------------------------------------------------

    def _compute_ela(
        self,
        rgb_image: Image.Image,
        jpeg_quality: int,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Execute the core ELA algorithm.

        Steps:
        1. Save the RGB image as a JPEG at *jpeg_quality* (temporary, in-memory).
        2. Reload the compressed JPEG.
        3. Compute the absolute pixel-wise difference.
        4. Normalize to 0–255.
        5. Enhance for visibility.
        6. Convert to grayscale.

        :param rgb_image: Pillow RGB image.
        :param jpeg_quality: JPEG quality for re-compression.
        :return: Tuple of (ela_image_rgb_uint8, ela_gray_uint8, diff_float32).
        """
        # 3. Save temporary JPEG (in-memory BytesIO — no disk files)
        jpeg_buf = io.BytesIO()
        rgb_image.save(jpeg_buf, format="JPEG", quality=jpeg_quality)
        jpeg_buf.seek(0)

        # 4. Reload compressed image
        recompressed = Image.open(jpeg_buf)
        if recompressed.mode != "RGB":
            recompressed = recompressed.convert("RGB")

        # 5. Compute absolute difference (OpenCV SIMD uint8)
        orig_np = np.asarray(rgb_image)
        recomp_np = np.asarray(recompressed)

        # Ensure shapes match (re-compression can change dimensions slightly)
        if orig_np.shape != recomp_np.shape:
            recompressed = recompressed.resize(rgb_image.size)
            recomp_np = np.asarray(recompressed)

        diff_uint8 = cv2.absdiff(orig_np, recomp_np)
        diff = diff_uint8.astype(np.float32)

        # 6. Normalize differences to 0–255
        max_diff = float(diff.max())
        if max_diff > 0:
            scale = 255.0 / max_diff
            normalized = diff * scale
        else:
            normalized = diff.copy()

        # 7. Enhance visibility
        gain = self._calculate_enhancement_gain(jpeg_quality)
        enhanced = normalized * gain

        # Clip and convert to uint8
        ela_image = np.clip(enhanced, 0, 255).astype(np.uint8)

        # 8. Convert to grayscale for analysis
        ela_gray = cv2.cvtColor(ela_image, cv2.COLOR_RGB2GRAY)

        return ela_image, ela_gray, diff

    @staticmethod
    def _calculate_enhancement_gain(jpeg_quality: int) -> float:
        """Calculate the enhancement gain factor.

        Lower JPEG quality produces larger compression differences, so less
        gain is needed.  Higher quality produces smaller differences, so more
        gain is applied.

        :param jpeg_quality: JPEG quality (1–100).
        :return: Gain multiplier (≥ 1.0).
        """
        if jpeg_quality >= 95:
            return 10.0
        elif jpeg_quality >= 90:
            return 1.0
        elif jpeg_quality >= 80:
            return 1.0
        else:
            return 1.0

    # ------------------------------------------------------------------
    # Metrics Computation
    # ------------------------------------------------------------------

    def _compute_metrics(
        self,
        diff: np.ndarray,
        ela_gray: np.ndarray,
        diff_max: np.ndarray,
    ) -> ElaMetrics:
        """Compute statistical metrics from the ELA difference and grayscale images.

        :param diff: Raw absolute difference array (float32, 3-channel).
        :param ela_gray: Normalized grayscale ELA image (uint8).
        :param diff_max: Pre-computed 2D max channel difference array.
        :return: Populated ``ElaMetrics``.
        """
        # High error pixels: pixels in the difference array exceeding the threshold
        high_error_mask = diff_max > HIGH_ERROR_PIXEL_THRESHOLD
        high_error_count = int(np.count_nonzero(high_error_mask))

        total_pixels = diff.shape[0] * diff.shape[1]
        pct_high_error = round((high_error_count / total_pixels) * 100.0, 4) if total_pixels > 0 else 0.0

        mean_ela_gray = float(np.mean(ela_gray))
        min_ela_gray = float(np.min(ela_gray))
        max_ela_gray = float(np.max(ela_gray))

        return ElaMetrics(
            average_error=round(float(np.mean(diff)), 4),
            maximum_error=round(float(np.max(diff)), 4),
            minimum_error=round(float(np.min(diff)), 4),
            standard_deviation=round(float(np.std(diff)), 4),
            high_error_pixel_count=high_error_count,
            percentage_high_error_pixels=pct_high_error,
            mean_brightness=round(mean_ela_gray, 4),
            dynamic_range=round(max_ela_gray - min_ela_gray, 4),
        )

    # ------------------------------------------------------------------
    # Suspicious Region Detection
    # ------------------------------------------------------------------

    def _detect_suspicious_regions(
        self,
        ela_gray: np.ndarray,
        diff_max: np.ndarray,
    ) -> List[SuspiciousRegion]:
        """Detect suspicious regions using connected-component analysis.

        Thresholds the grayscale ELA image at ``mean + sigma * std``,
        finds connected components, and reports those exceeding the minimum
        area and intensity thresholds.

        :param ela_gray: Normalized grayscale ELA image (uint8).
        :param diff_max: Pre-computed 2D max channel difference array.
        :return: List of ``SuspiciousRegion`` objects.
        """
        # Compute threshold: mean + 2*std
        mean_val = float(np.mean(ela_gray))
        std_val = float(np.std(ela_gray))
        threshold = max(mean_val + REGION_THRESHOLD_SIGMA * std_val, SUSPICIOUS_REGION_MIN_INTENSITY)

        # Threshold the image
        binary = (ela_gray > threshold).astype(np.uint8) * 255

        # Morphological closing to merge nearby regions
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # Find connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            binary, connectivity=8
        )

        regions: List[SuspiciousRegion] = []

        # Skip label 0 (background)
        for i in range(1, num_labels):
            area = int(stats[i, cv2.CC_STAT_AREA])
            if area < SUSPICIOUS_REGION_MIN_AREA:
                continue

            x = int(stats[i, cv2.CC_STAT_LEFT])
            y = int(stats[i, cv2.CC_STAT_TOP])
            w = int(stats[i, cv2.CC_STAT_WIDTH])
            h = int(stats[i, cv2.CC_STAT_HEIGHT])

            # Compute mean intensity of the difference within this region
            mask = labels == i
            region_diff = diff_max[mask]
            intensity = float(np.mean(region_diff)) if len(region_diff) > 0 else 0.0

            if intensity < SUSPICIOUS_REGION_MIN_INTENSITY:
                continue

            regions.append(SuspiciousRegion(
                bounding_box=BoundingBox(
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                ),
                coordinates=[x, y, x + w, y + h],
                area=float(area),
                intensity=round(intensity, 4),
            ))

        # Sort by intensity (descending) and limit
        regions.sort(key=lambda r: r.intensity, reverse=True)
        return regions[:MAX_SUSPICIOUS_REGIONS]

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    def _fallback_result(
        self,
        image_data: bytes,
        request_id: str,
    ) -> ElaProcessingResult:
        """Build a minimal ``ElaProcessingResult`` when the image cannot be decoded.

        :param image_data: Raw image bytes (for size estimation).
        :param request_id: Request ID for tracing.
        :return: ``ElaProcessingResult`` with zeroed arrays and metrics.
        """
        logger.warning(
            f"[{request_id}] Using fallback ELA result (image undecodable). "
            f"Data size: {len(image_data)} bytes"
        )

        # Create minimal arrays
        ela_image = np.zeros((1, 1, 3), dtype=np.uint8)
        ela_gray = np.zeros((1, 1), dtype=np.uint8)
        diff = np.zeros((1, 1, 3), dtype=np.float64)

        metrics = ElaMetrics(
            average_error=0.0,
            maximum_error=0.0,
            minimum_error=0.0,
            standard_deviation=0.0,
            high_error_pixel_count=0,
            percentage_high_error_pixels=0.0,
            mean_brightness=0.0,
            dynamic_range=0.0,
        )

        return ElaProcessingResult(
            ela_image=ela_image,
            ela_gray=ela_gray,
            diff=diff,
            metrics=metrics,
            suspicious_regions=[],
            image_width=0,
            image_height=0,
            image_format="UNKNOWN",
            image_mode="unknown",
        )


