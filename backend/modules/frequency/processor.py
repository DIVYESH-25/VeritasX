"""
Frequency Analysis Module — Processing Layer

The ``FrequencyProcessor`` implements a deterministic FFT-based forensic
analysis pipeline:

1.  Decode the image (Pillow).
2.  Convert to grayscale.
3.  Optionally apply a 2-D Hann window to reduce spectral leakage.
4.  Compute the 2-D Fast Fourier Transform (FFT).
5.  Shift the zero-frequency component to the center.
6.  Compute the magnitude spectrum with logarithmic scaling.
7.  Normalize the spectrum for visualization and analysis.
8.  Calculate frequency-domain statistics (metrics).

The implementation is deterministic and configurable.  No temporary files
are written to disk — all processing is performed in-memory using
vectorised NumPy / SciPy operations for speed.

Key Formulas
------------
* **FFT**: ``F(u, v) = sum(sum(f(x, y) * exp(-j*2*pi*(ux/M + vy/N))))``
  Computed via ``np.fft.fft2``.
* **Magnitude**: ``|F(u, v)| = sqrt(Re(F)^2 + Im(F)^2)``
  Computed via ``np.abs``.
* **Log-scaled magnitude**: ``log(1 + |F(u, v)|)``
  Compresses the dynamic range so both strong and weak components are visible.
* **Spectral entropy**: ``H = -sum(p_i * log(p_i))`` where ``p_i = |F_i| / sum(|F|)``
  Normalised by ``log(N)`` so the result is in [0, 1].
* **Radial energy**: Energy integrated over annular rings centred at the
  zero-frequency point, as a fraction of total spectral energy.
* **H/V balance**: Compare the energy concentration along the horizontal axis
  (sum over columns of the central row band) vs the vertical axis.
* **Radial symmetry**: Correlation between the spectrum and its 180° rotation.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Tuple

import numpy as np
from PIL import Image

from backend.modules.frequency.constants import (
    APPLY_HANN_WINDOW,
    FFT_MAX_DIMENSION,
    HIGH_FREQ_RADIUS_FRACTION,
    LOW_FREQ_RADIUS_FRACTION,
)
from backend.modules.frequency.models import (
    FrequencyMetrics,
    ProcessingResult,
)
from backend.modules.frequency.utils import (
    convert_to_grayscale,
    load_image_from_bytes,
)

logger = logging.getLogger("veritasx.modules.frequency.processor")


class FrequencyProcessor:
    """Performs the core FFT-based frequency domain analysis.

    This class is stateless (apart from configuration) and safe to reuse
    across requests.
    """

    def __init__(
        self,
        max_dimension: int = FFT_MAX_DIMENSION,
        apply_hann: bool = APPLY_HANN_WINDOW,
    ) -> None:
        """Initialise the Frequency processor.

        :param max_dimension: Maximum width/height for FFT processing.
            Larger images are downsampled to fit within this bound.
        :param apply_hann: Whether to apply a 2-D Hann window before FFT.
        """
        self._max_dimension: int = max_dimension
        self._apply_hann: bool = apply_hann

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        image_data: bytes,
        request_id: str,
    ) -> ProcessingResult:
        """Run the full frequency analysis pipeline on *image_data*.

        :param image_data: Raw image bytes (JPEG, PNG, WEBP, etc.).
        :param request_id: Unique request identifier for tracing.
        :return: ``ProcessingResult`` containing the magnitude spectrum,
            metrics, and source image metadata.
        """
        start = time.perf_counter()
        logger.info(
            f"[{request_id}] Frequency processing started ({len(image_data)} bytes)"
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

        # 2. Convert to grayscale
        gray_array = convert_to_grayscale(pil_image)

        # 3. Downsample if necessary (FFT is O(N log N) but memory grows with size)
        if max(gray_array.shape) > self._max_dimension:
            scale = self._max_dimension / max(gray_array.shape)
            new_w = max(1, int(width * scale))
            new_h = max(1, int(height * scale))
            pil_gray = Image.fromarray(gray_array.astype(np.uint8), mode="L")
            pil_gray = pil_gray.resize((new_w, new_h), Image.Resampling.NEAREST)
            gray_array = np.asarray(pil_gray, dtype=np.float32)
            logger.info(f"[{request_id}] Downsampled to {new_h}×{new_w} for FFT processing")
        else:
            new_h, new_w = gray_array.shape
            logger.info(f"[{request_id}] Using original size {new_h}×{new_w} for FFT processing")

        # 4. Subtract mean (remove DC component for better spectral analysis)
        gray_float = gray_array.astype(np.float64) - np.mean(gray_array)

        # 5. Apply Hann window (optional, reduces spectral leakage)
        if self._apply_hann:
            window = self._hann_window_2d(gray_float.shape)
            windowed = gray_float * window
        else:
            windowed = gray_float

        # 6. Compute 2D FFT
        fft_complex = np.fft.fft2(windowed)

        # 7. Shift zero-frequency component to center
        fft_shifted = np.fft.fftshift(fft_complex)

        # 8. Compute magnitude spectrum
        magnitude = np.abs(fft_shifted)

        # 9. Log-scaled magnitude (log(1 + |F|))
        magnitude_log = np.log1p(magnitude)

        # 10. Normalise for analysis (divide by max)
        max_mag = float(magnitude_log.max())
        if max_mag > 0:
            magnitude_normalised = magnitude_log / max_mag
        else:
            magnitude_normalised = magnitude_log.copy()

        # 11. Compute metrics
        metrics = self._compute_metrics(magnitude, magnitude_normalised, new_h, new_w)

        # Preserve original dimensions for reporting
        metrics.image_width = width
        metrics.image_height = height
        metrics.image_format = image_format
        metrics.image_mode = image_mode
        metrics.fft_size = (new_h, new_w)

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            f"[{request_id}] Frequency processing complete in {elapsed_ms}ms | "
            f"low_freq_energy={metrics.low_frequency_energy:.4f} | "
            f"high_freq_energy={metrics.high_frequency_energy:.4f} | "
            f"energy_ratio={metrics.energy_ratio:.4f} | "
            f"spectral_entropy={metrics.spectral_entropy:.4f} | "
            f"peak_to_mean={metrics.peak_to_mean_ratio:.4f}"
        )

        return ProcessingResult(
            magnitude_spectrum=magnitude_normalised.astype(np.float64),
            magnitude_original=magnitude.astype(np.float64),
            metrics=metrics,
            image_width=width,
            image_height=height,
            image_format=image_format,
            image_mode=image_mode,
        )

    # ------------------------------------------------------------------
    # FFT Pipeline
    # ------------------------------------------------------------------

    @staticmethod
    def _hann_window_2d(shape: Tuple[int, int]) -> np.ndarray:
        """Create a 2-D Hann window of the given shape.

        The 2-D Hann window is the outer product of 1-D Hann windows:
        ``w(x, y) = w(x) * w(y)``

        :param shape: (rows, cols) of the desired window.
        :return: 2-D Hann window array of shape (rows, cols).
        """
        rows, cols = shape
        win_1d_rows = np.hanning(rows)
        win_1d_cols = np.hanning(cols)
        window_2d = np.outer(win_1d_rows, win_1d_cols)
        return window_2d

    # ------------------------------------------------------------------
    # Metrics Computation
    # ------------------------------------------------------------------

    def _compute_metrics(
        self,
        magnitude: np.ndarray,
        magnitude_normalised: np.ndarray,
        height: int,
        width: int,
    ) -> FrequencyMetrics:
        """Compute frequency-domain metrics from the FFT magnitude spectrum.

        :param magnitude: Raw FFT magnitude (after fftshift, before log scaling).
        :param magnitude_normalised: Log-scaled, normalised magnitude spectrum.
        :param height: Height of the FFT input.
        :param width: Width of the FFT input.
        :return: Populated ``FrequencyMetrics``.
        """
        h, w = magnitude.shape
        center_y, center_x = h // 2, w // 2
        max_radius = min(center_y, center_x)

        # Distance from center for each pixel
        y_coords, x_coords = np.ogrid[:h, :w]
        distances = np.sqrt(
            (x_coords - center_x) ** 2 + (y_coords - center_y) ** 2
        )

        # --- Energy distribution ---
        total_energy = float(np.sum(magnitude))
        if total_energy <= 0:
            # Degenerate case
            total_energy = 1.0

        # Low-frequency region: within LOW_FREQ_RADIUS_FRACTION of min(h, w)
        low_radius = max(1, int(LOW_FREQ_RADIUS_FRACTION * min(h, w)))
        low_mask = distances <= low_radius
        low_freq_energy = float(np.sum(magnitude[low_mask]))

        # High-frequency region: outside HIGH_FREQ_RADIUS_FRACTION of max_radius
        high_radius = int(HIGH_FREQ_RADIUS_FRACTION * max_radius)
        high_mask = distances >= high_radius
        high_freq_energy = float(np.sum(magnitude[high_mask]))

        energy_ratio = low_freq_energy / (high_freq_energy + 1e-10)

        # --- Magnitude statistics ---
        mean_magnitude = float(np.mean(magnitude_log_safe(magnitude)))
        std_magnitude = float(np.std(magnitude_log_safe(magnitude)))
        min_magnitude = float(np.min(magnitude_log_safe(magnitude)))
        max_magnitude = float(np.max(magnitude_log_safe(magnitude)))

        # --- Spectral entropy ---
        spectral_entropy = self._compute_spectral_entropy(magnitude, magnitude_normalised)

        # --- Peak-to-mean ratio ---
        peak_to_mean_ratio = float(
            np.max(magnitude) / (mean_magnitude + 1e-10)
        )

        # --- Radial energy distribution ---
        # Divide into 3 annular regions: inner (0-25%), mid (25-75%), outer (75-100%)
        radius_25 = int(0.25 * max_radius)
        radius_75 = int(0.75 * max_radius)

        inner_mask = distances <= radius_25
        mid_mask = (distances > radius_25) & (distances <= radius_75)
        outer_mask = distances > radius_75

        inner_energy = float(np.sum(magnitude[inner_mask]))
        mid_energy = float(np.sum(magnitude[mid_mask]))
        outer_energy = float(np.sum(magnitude[outer_mask]))

        radial_inner = inner_energy / total_energy
        radial_mid = mid_energy / total_energy
        radial_outer = outer_energy / total_energy

        # --- Horizontal/Vertical energy balance ---
        # Sum energy along rows (horizontal frequencies) and columns (vertical frequencies)
        # Horizontal energy: energy concentrated along the horizontal axis (varying in y)
        # Vertical energy: energy concentrated along the vertical axis (varying in x)
        row_sums = np.sum(magnitude, axis=1)  # varies with y → horizontal freq content
        col_sums = np.sum(magnitude, axis=0)  # varies with x → vertical freq content

        horizontal_energy = float(np.sum(row_sums[center_y - low_radius:center_y + low_radius + 1]))
        vertical_energy = float(np.sum(col_sums[center_x - low_radius:center_x + low_radius + 1]))
        hv_total = horizontal_energy + vertical_energy
        if hv_total > 0:
            horizontal_fraction = horizontal_energy / hv_total
            vertical_fraction = vertical_energy / hv_total
            hv_ratio = horizontal_energy / (vertical_energy + 1e-10)
        else:
            horizontal_fraction = 0.5
            vertical_fraction = 0.5
            hv_ratio = 1.0

        # --- Radial symmetry score ---
        radial_symmetry = self._compute_radial_symmetry(magnitude)

        return FrequencyMetrics(
            low_frequency_energy=round(low_freq_energy, 6),
            high_frequency_energy=round(high_freq_energy, 6),
            energy_ratio=round(energy_ratio, 4),
            mean_magnitude=round(mean_magnitude, 4),
            std_magnitude=round(std_magnitude, 4),
            min_magnitude=round(min_magnitude, 4),
            max_magnitude=round(max_magnitude, 4),
            spectral_entropy=round(spectral_entropy, 4),
            peak_to_mean_ratio=round(peak_to_mean_ratio, 4),
            radial_energy_innner=round(radial_inner, 4),
            radial_energy_mid=round(radial_mid, 4),
            radial_energy_outer=round(radial_outer, 4),
            horizontal_energy_fraction=round(horizontal_fraction, 4),
            vertical_energy_fraction=round(vertical_fraction, 4),
            hv_balance_ratio=round(hv_ratio, 4),
            radial_symmetry_score=round(radial_symmetry, 4),
            image_width=0,  # Will be set by caller
            image_height=0,
            image_format="UNKNOWN",
            image_mode="unknown",
            fft_size=(h, w),
        )

    @staticmethod
    def _compute_spectral_entropy(
        magnitude: np.ndarray,
        magnitude_normalised: np.ndarray,
    ) -> float:
        """Compute the normalised spectral entropy of the magnitude spectrum.

        Spectral entropy measures how concentrated or spread out the energy
        is in the frequency domain:

        ``H = -sum(p_i * log(p_i)) / log(N)``

        where ``p_i = energy_i / total_energy`` and ``N`` is the number of
        frequency bins.  The result is normalised to [0, 1] where:
        - 0 indicates all energy is concentrated in a single bin
        - 1 indicates perfectly uniform energy distribution.

        :param magnitude: Raw FFT magnitude spectrum.
        :param magnitude_normalised: Normalised version (for edge cases).
        :return: Normalised spectral entropy in [0, 1].
        """
        # Build probability distribution from magnitude
        prob = magnitude / (np.sum(magnitude) + 1e-10)

        # Avoid log(0)
        prob_nonzero = prob[prob > 1e-15]

        if len(prob_nonzero) == 0:
            return 0.0

        entropy = -np.sum(prob_nonzero * np.log(prob_nonzero))
        num_bins = magnitude.size

        # Normalise by log(num_bins) so max entropy = 1
        max_entropy = np.log(num_bins)
        if max_entropy > 0:
            return float(entropy / max_entropy)
        return 0.0

    @staticmethod
    def _compute_radial_symmetry(magnitude: np.ndarray) -> float:
        """Compute a radial symmetry score for the magnitude spectrum.

        The score measures how similar the spectrum is to its 180° rotation.
        Natural images often exhibit approximate conjugate symmetry in the
        Fourier domain, but perfectly symmetric spectra can indicate synthetic
        generation (e.g., periodic patterns from diffusion models).

        ``symmetry = corr(M, rotate180(M))``

        where ``corr`` is the normalised cross-correlation.

        :param magnitude: 2D FFT magnitude spectrum.
        :return: Symmetry score in [0, 1].
        """
        # Rotate 180 degrees
        rotated = np.rot90(magnitude, 2)

        # Compute normalised cross-correlation (cosine similarity)
        numerator = float(np.sum(magnitude * rotated))
        denominator = float(np.linalg.norm(magnitude) * np.linalg.norm(rotated) + 1e-10)

        if denominator > 0:
            return max(0.0, min(1.0, numerator / denominator))
        return 0.0

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    def _fallback_result(
        self,
        image_data: bytes,
        request_id: str,
    ) -> ProcessingResult:
        """Build a minimal ``ProcessingResult`` when the image cannot be decoded.

        :param image_data: Raw image bytes (for size estimation).
        :param request_id: Request ID for tracing.
        :return: ``ProcessingResult`` with zeroed arrays and metrics.
        """
        logger.warning(
            f"[{request_id}] Using fallback Frequency result (image undecodable). "
            f"Data size: {len(image_data)} bytes"
        )

        # Create minimal arrays (1x1 to satisfy FFT requirements)
        magnitude_spectrum = np.zeros((1, 1), dtype=np.float64)
        magnitude_original = np.zeros((1, 1), dtype=np.float64)

        metrics = FrequencyMetrics(
            low_frequency_energy=0.0,
            high_frequency_energy=0.0,
            energy_ratio=0.0,
            mean_magnitude=0.0,
            std_magnitude=0.0,
            min_magnitude=0.0,
            max_magnitude=0.0,
            spectral_entropy=0.0,
            peak_to_mean_ratio=0.0,
            radial_energy_innner=0.0,
            radial_energy_mid=0.0,
            radial_energy_outer=0.0,
            horizontal_energy_fraction=0.0,
            vertical_energy_fraction=0.0,
            hv_balance_ratio=1.0,
            radial_symmetry_score=0.0,
            image_width=0,
            image_height=0,
            image_format="UNKNOWN",
            image_mode="unknown",
            fft_size=(1, 1),
        )

        return ProcessingResult(
            magnitude_spectrum=magnitude_spectrum,
            magnitude_original=magnitude_original,
            metrics=metrics,
            image_width=0,
            image_height=0,
            image_format="UNKNOWN",
            image_mode="unknown",
        )


def magnitude_log_safe(magnitude: np.ndarray) -> np.ndarray:
    """Apply log scaling to the magnitude, safely handling zero values.

    Uses ``log1p`` (log(1 + x)) which is numerically stable for small values
    and zero.

    :param magnitude: Raw FFT magnitude array.
    :return: Log-scaled magnitude array.
    """
    return np.log1p(np.maximum(magnitude, 0))
