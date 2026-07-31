"""
Error Level Analysis Module — Visualization Layer

The ``ElaVisualizer`` converts the raw ELA numpy array into a base64-encoded
image suitable for inclusion in API responses and frontend rendering.

The visualization uses a grayscale representation of the ELA difference,
which clearly highlights regions of inconsistent compression.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from backend.modules.ela.constants import ELA_IMAGE_MAX_DIMENSION
from backend.modules.ela.models import ElaImageData
from backend.modules.ela.utils import array_to_base64, resize_for_visualization

logger = logging.getLogger("veritasx.modules.ela.visualization")


class ElaVisualizer:
    """Generates the ELA visualization image from the processing result.

    This class is stateless and safe to reuse across requests.
    """

    def __init__(self) -> None:
        """Initialise the ELA visualizer."""
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_ela_image(
        self,
        ela_array: np.ndarray,
        request_id: str,
    ) -> Optional[ElaImageData]:
        """Generate a base64-encoded ELA visualization image.

        :param ela_array: ELA image as a numpy array (uint8, H×W×C or H×W).
        :param request_id: Request ID for tracing.
        :return: ``ElaImageData`` containing the base64 string, or ``None``
                 if the array is empty / invalid.
        """
        if ela_array is None or ela_array.size == 0:
            logger.warning(f"[{request_id}] ELA array is empty — skipping visualization.")
            return None

        try:
            # Resize for visualization if the image is large
            # (keeps base64 payload reasonable for API responses)
            resized = resize_for_visualization(ela_array, ELA_IMAGE_MAX_DIMENSION)

            # Encode as PNG (lossless — preserves the full ELA detail)
            base64_str = array_to_base64(resized, fmt="PNG")

            height = int(resized.shape[0])
            width = int(resized.shape[1])

            logger.info(
                f"[{request_id}] ELA image generated: {width}×{height}, "
                f"base64 length={len(base64_str)} chars"
            )

            return ElaImageData(
                base64=base64_str,
                format="PNG",
                width=width,
                height=height,
            )

        except Exception as exc:
            logger.error(
                f"[{request_id}] Failed to generate ELA visualization: {exc}",
                exc_info=True,
            )
            return None
