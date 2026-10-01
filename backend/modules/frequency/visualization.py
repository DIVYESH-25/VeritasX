"""
Frequency Analysis Module — Visualization Layer

The ``FrequencyVisualizer`` converts the raw FFT magnitude spectrum (a
numpy array) into a base64-encoded image suitable for inclusion in API
responses and frontend rendering.

The visualization uses a normalised log-magnitude representation, displayed
with a dark-to-bright colormap (grayscale with inverted intensity so that
high-energy frequencies appear bright).
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from backend.modules.frequency.constants import FFT_IMAGE_MAX_DIMENSION
from backend.modules.frequency.models import FrequencyImageData
from backend.modules.frequency.utils import array_to_base64, resize_for_visualization

logger = logging.getLogger("veritasx.modules.frequency.visualization")


class FrequencyVisualizer:
    """Generates the FFT magnitude spectrum visualization from the processing result.

    This class is stateless and safe to reuse across requests.
    """

    def __init__(self) -> None:
        """Initialise the Frequency visualizer."""
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_spectrum_image(
        self,
        magnitude_spectrum: np.ndarray,
        request_id: str,
    ) -> Optional[FrequencyImageData]:
        """Generate a base64-encoded FFT magnitude spectrum visualization.

        The visualization applies the following pipeline:
        1. Normalise the log-magnitude spectrum to [0, 255].
        2. Apply a colormap for visual clarity (using a "viridis"-like
           grayscale mapping via simple linear scaling).
        3. Resize if too large (keeps base64 payload reasonable).
        4. Encode as PNG base64.

        :param magnitude_spectrum: Log-scaled, normalised magnitude spectrum
            (float64 array of shape (H, W)).
        :param request_id: Request ID for tracing.
        :return: ``FrequencyImageData`` containing the base64 string, or
            ``None`` if the array is empty / invalid.
        """
        if magnitude_spectrum is None or magnitude_spectrum.size == 0:
            logger.warning(f"[{request_id}] Magnitude spectrum is empty — skipping visualization.")
            return None

        try:
            # Work on a copy to avoid modifying the original
            spectrum = np.array(magnitude_spectrum, dtype=np.float64)

            # Normalise to [0, 1] range
            min_val = float(spectrum.min())
            max_val = float(spectrum.max())
            val_range = max_val - min_val

            if val_range > 0:
                spectrum = (spectrum - min_val) / val_range
            else:
                spectrum = np.zeros_like(spectrum)

            # Scale to [0, 255]
            spectrum_u8 = (spectrum * 255.0).astype(np.uint8)

            # Resize for visualization if the spectrum is large
            # (keeps base64 payload reasonable for API responses)
            resized = resize_for_visualization(spectrum_u8, FFT_IMAGE_MAX_DIMENSION)

            # Encode as PNG (lossless — preserves the full spectral detail)
            base64_str = array_to_base64(resized, fmt="PNG")

            height = int(resized.shape[0])
            width = int(resized.shape[1])

            logger.info(
                f"[{request_id}] FFT spectrum image generated: {width}×{height}, "
                f"base64 length={len(base64_str)} chars"
            )

            return FrequencyImageData(
                base64=base64_str,
                format="PNG",
                width=width,
                height=height,
            )

        except Exception as exc:
            logger.error(
                f"[{request_id}] Failed to generate FFT visualization: {exc}",
                exc_info=True,
            )
            return None
