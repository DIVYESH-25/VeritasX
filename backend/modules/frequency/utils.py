"""
Frequency Analysis Module — Utility Functions

Provides low-level helper functions for:
- Image loading and conversion from raw bytes
- Grayscale conversion
- Base64 encoding of image data for visualization
- Safe image dimension retrieval and resizing

These utilities mirror the patterns used in the ELA module, adapted for
frequency-domain (FFT) processing.
"""

from __future__ import annotations

import base64
import io
import logging
from typing import Optional, Tuple

import numpy as np
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger("veritasx.modules.frequency.utils")


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


def convert_to_grayscale(image: Image.Image) -> np.ndarray:
    """Convert a Pillow image to a grayscale numpy array (float32).

    Handles RGB, RGBA, L (grayscale), P (palette), and other modes by
    converting to grayscale ('L') via Pillow, then to a float32 numpy array.

    :param image: Pillow image (any mode).
    :return: Grayscale image as a float32 numpy array of shape (H, W).
    """
    if image.mode == "L":
        gray_img = image
    elif image.mode in ("RGB", "RGBA"):
        gray_img = image.convert("L")
    else:
        gray_img = image.convert("L")

    return np.asarray(gray_img, dtype=np.float32)


# ---------------------------------------------------------------------------
# Base64 Encoding
# ---------------------------------------------------------------------------

def image_to_base64(image: Image.Image, fmt: str = "PNG") -> str:
    """Convert a Pillow image to a base64-encoded string.

    :param image: Pillow image to encode.
    :param fmt: Output format (e.g. ``"PNG"``).
    :return: Base64-encoded string (without data URI prefix).
    """
    buf = io.BytesIO()
    image.save(buf, format=fmt)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return encoded


def array_to_base64(arr: np.ndarray, fmt: str = "PNG") -> str:
    """Convert a numpy array (H×W or H×W×C) to a base64-encoded image string.

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
        elif arr_u8.ndim == 3 and arr_u8.shape[2] == 4:
            bgra = cv2.cvtColor(arr_u8, cv2.COLOR_RGBA2BGRA)
            success, enc = cv2.imencode(ext, bgra)
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
    max_dimension: int = 512,
) -> np.ndarray:
    """Resize a numpy image array so its largest dimension does not exceed *max_dimension*.

    Uses nearest-neighbour for speed (sufficient for visualization).

    :param arr: Numpy array (H×W or H×W×C).
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
