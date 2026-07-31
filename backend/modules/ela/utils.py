"""
Error Level Analysis Module — Utility Functions

Provides low-level helper functions for:
- Image loading and conversion from raw bytes
- Base64 encoding of image data
- NumPy array ↔ Pillow image conversion
- Safe image dimension retrieval
"""

from __future__ import annotations

import base64
import io
import logging
from typing import Optional, Tuple

import numpy as np
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger("veritasx.modules.ela.utils")


# ---------------------------------------------------------------------------
# Image Loading
# ---------------------------------------------------------------------------

def load_image_from_bytes(image_data: bytes) -> Optional[Image.Image]:
    """Load a Pillow image from raw bytes.

    :param image_data: Raw image bytes.
    :return: Pillow ``Image`` object, or ``None`` if the data cannot be decoded.
    """
    if not image_data:
        logger.warning("Empty image data provided to load_image_from_bytes.")
        return None

    try:
        stream = io.BytesIO(image_data)
        img = Image.open(stream)
        img.load()  # Force full decode
        return img
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        logger.warning(f"Pillow could not decode image: {exc}")
        return None
    except Exception as exc:
        logger.error(f"Unexpected error loading image: {exc}", exc_info=True)
        return None


def convert_to_rgb(image: Image.Image) -> Image.Image:
    """Convert a Pillow image to RGB mode.

    :param image: Pillow image (any mode).
    :return: RGB-mode Pillow image.
    """
    if image.mode == "RGB":
        return image
    return image.convert("RGB")


# ---------------------------------------------------------------------------
# Base64 Encoding
# ---------------------------------------------------------------------------

def image_to_base64(image: Image.Image, fmt: str = "PNG") -> str:
    """Convert a Pillow image to a base64-encoded string.

    :param image: Pillow image to encode.
    :param fmt: Output format (e.g. ``"PNG"``, ``"JPEG"``).
    :return: Base64-encoded string (without data URI prefix).
    """
    buf = io.BytesIO()
    image.save(buf, format=fmt)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return encoded


def array_to_base64(arr: np.ndarray, fmt: str = "PNG") -> str:
    """Convert a numpy array (H×W×C or H×W) to a base64-encoded image string.

    :param arr: Numpy array representing an image (uint8).
    :param fmt: Output format for encoding.
    :return: Base64-encoded string.
    """
    try:
        import cv2
        arr_u8 = np.asarray(arr)
        if arr_u8.dtype != np.uint8:
            arr_u8 = np.clip(arr_u8, 0, 255).astype(np.uint8)

        ext = f".{fmt.lower()}"
        if arr_u8.ndim == 3 and arr_u8.shape[2] == 3:
            bgr = cv2.cvtColor(arr_u8, cv2.COLOR_RGB2BGR)
            success, enc = cv2.imencode(ext, bgr)
        else:
            success, enc = cv2.imencode(ext, arr_u8)

        if success:
            return base64.b64encode(enc.tobytes()).decode("ascii")
    except Exception as exc:
        logger.debug(f"OpenCV base64 encoding fallback: {exc}")

    img = array_to_pil_image(arr)
    return image_to_base64(img, fmt)


# ---------------------------------------------------------------------------
# NumPy ↔ Pillow Conversion
# ---------------------------------------------------------------------------

def array_to_pil_image(arr: np.ndarray) -> Image.Image:
    """Convert a numpy array to a Pillow image.

    Handles both grayscale (2-D) and RGB (3-D) arrays.

    :param arr: Numpy array (uint8 or convertible).
    :return: Pillow ``Image`` object.
    """
    arr = np.asarray(arr)

    # Ensure uint8
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)

    if arr.ndim == 2:
        return Image.fromarray(arr, mode="L")
    elif arr.ndim == 3:
        # Determine mode from channel count
        channels = arr.shape[2]
        if channels == 3:
            return Image.fromarray(arr, mode="RGB")
        elif channels == 4:
            return Image.fromarray(arr, mode="RGBA")
        elif channels == 1:
            return Image.fromarray(arr[:, :, 0], mode="L")
        else:
            raise ValueError(f"Unsupported channel count: {channels}")
    else:
        raise ValueError(f"Unsupported array shape: {arr.shape}")


def pil_image_to_array(image: Image.Image) -> np.ndarray:
    """Convert a Pillow image to a numpy array (float32 for computation).

    :param image: Pillow image (should be RGB).
    :return: Numpy array of shape (H, W, 3) with dtype float32.
    """
    return np.asarray(image, dtype=np.float32)


# ---------------------------------------------------------------------------
# Dimension Helpers
# ---------------------------------------------------------------------------

def get_image_dimensions(image: Image.Image) -> Tuple[int, int]:
    """Safely retrieve image dimensions.

    :param image: Pillow image.
    :return: ``(width, height)`` tuple.
    """
    return image.size


def resize_for_visualization(
    arr: np.ndarray,
    max_dimension: int = 1024,
) -> np.ndarray:
    """Resize a numpy image array so its largest dimension does not exceed *max_dimension*.

    Uses nearest-neighbour for speed (sufficient for visualization).

    :param arr: Numpy array (H×W×C or H×W).
    :param max_dimension: Maximum width or height in pixels.
    :return: Resized array.
    """
    if arr.ndim == 2:
        h, w = arr.shape
    elif arr.ndim == 3:
        h, w = arr.shape[:2]
    else:
        return arr

    if max(h, w) <= max_dimension:
        return arr

    scale = max_dimension / max(h, w)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))

    try:
        import cv2
        return cv2.resize(arr, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
    except Exception:
        pil_img = array_to_pil_image(arr)
        resized = pil_img.resize((new_w, new_h), Image.Resampling.NEAREST)
        return np.array(resized)
