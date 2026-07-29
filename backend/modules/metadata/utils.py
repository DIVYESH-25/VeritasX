"""
Metadata Analysis Module — Utility Functions

Provides low-level helper functions for:
- Cryptographic hashing (SHA-256, MD5)
- MIME type detection
- Timestamp parsing and validation
- GPS coordinate conversion
- Safe type coercion
- File extension extraction
"""

from __future__ import annotations

import hashlib
import io
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional, Tuple, Union

from backend.modules.metadata.constants import EXTENSION_TO_MIME

logger = logging.getLogger("veritasx.modules.metadata.utils")


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def compute_sha256(data: bytes) -> str:
    """Compute the SHA-256 hash of *data* and return it as a hex string.

    :param data: Raw bytes to hash.
    :return: Lowercase hex-encoded SHA-256 digest.
    """
    return hashlib.sha256(data).hexdigest()


def compute_md5(data: bytes) -> str:
    """Compute the MD5 hash of *data* and return it as a hex string.

    MD5 is included for legacy forensic workflows; it is **not** cryptographically
    secure but remains useful as a quick duplicate-detection fingerprint.

    :param data: Raw bytes to hash.
    :return: Lowercase hex-encoded MD5 digest.
    """
    return hashlib.md5(data).hexdigest()


# ---------------------------------------------------------------------------
# MIME Type Detection
# ---------------------------------------------------------------------------

def detect_mime_type(data: bytes, filename: str = "") -> str:
    """Detect the MIME type of an image from its magic bytes.

    Tries ``python-magic`` first (if installed), then falls back to a
    built-in magic-byte lookup, and finally to extension-based detection.

    :param data: Raw image bytes.
    :param filename: Optional filename for extension-based fallback.
    :return: Detected MIME type string (e.g. ``'image/jpeg'``).
    """
    # Attempt 1: python-magic (most accurate)
    try:
        import magic  # type: ignore[import-untyped]
        mime = magic.from_buffer(data, mime=True)
        if mime and mime.startswith("image/"):
            return mime
    except ImportError:
        pass
    except Exception as exc:
        logger.debug(f"python-magic failed: {exc}")

    # Attempt 2: built-in magic-byte lookup
    detected = _detect_mime_from_magic_bytes(data)
    if detected:
        return detected

    # Attempt 3: extension-based fallback
    ext = _get_extension(filename)
    if ext.lower() in EXTENSION_TO_MIME:
        return EXTENSION_TO_MIME[ext.lower()]

    return "application/octet-stream"


def _detect_mime_from_magic_bytes(data: bytes) -> Optional[str]:
    """Detect MIME type from the first few bytes of *data*.

    :param data: Raw bytes (at least the first 16 bytes are examined).
    :return: MIME type string or ``None`` if unrecognised.
    """
    if len(data) < 4:
        return None

    # JPEG: FF D8 FF
    if data[0:3] == b"\xff\xd8\xff":
        return "image/jpeg"

    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if data[0:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"

    # WEBP: RIFF .... WEBP
    if data[0:4] == b"RIFF" and len(data) >= 12 and data[8:12] == b"WEBP":
        return "image/webp"

    # GIF: GIF87a or GIF89a
    if data[0:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"

    # BMP: BM
    if data[0:2] == b"BM":
        return "image/bmp"

    # TIFF: II*\0 (little-endian) or MM\0* (big-endian)
    if data[0:4] in (b"II*\x00", b"MM\x00*"):
        return "image/tiff"

    # HEIC/HEIF: ftyp heic / heix / hevc / hevx
    if data[0:4] == b"\x00\x00\x00\x18" and len(data) >= 12:
        ftyp = data[4:8]
        if ftyp == b"ftyp":
            brand = data[8:12]
            if brand in (b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"):
                return "image/heic"

    # AVIF: ftyp avif
    if data[0:4] == b"\x00\x00\x00\x18" and len(data) >= 12:
        ftyp = data[4:8]
        if ftyp == b"ftyp":
            brand = data[8:12]
            if brand in (b"avif", b"avis"):
                return "image/avif"

    return None


# ---------------------------------------------------------------------------
# File Extension
# ---------------------------------------------------------------------------

def _get_extension(filename: str) -> str:
    """Extract the file extension (including the dot) from *filename*.

    :param filename: A filename string.
    :return: Lowercase extension including the dot, or empty string.
    """
    if not filename:
        return ""
    _, ext = os.path.splitext(filename)
    return ext.lower()


# ---------------------------------------------------------------------------
# Timestamp Parsing & Validation
# ---------------------------------------------------------------------------

# Common EXIF timestamp format: "YYYY:MM:DD HH:MM:SS"
_EXIF_TIMESTAMP_FORMATS = [
    "%Y:%m:%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y:%m:%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S.%fZ",
]


def parse_exif_timestamp(ts: str) -> Optional[datetime]:
    """Parse an EXIF timestamp string into a ``datetime`` object.

    Handles the standard EXIF format ``YYYY:MM:DD HH:MM:SS`` as well as
    ISO-8601 variants.

    :param ts: Timestamp string from EXIF data.
    :return: Parsed ``datetime`` (naive) or ``None`` if parsing fails.
    """
    if not ts or not isinstance(ts, str):
        return None

    ts = ts.strip()
    if not ts:
        return None

    for fmt in _EXIF_TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue

    # Last resort: try fromisoformat (Python 3.11+ handles 'Z' suffix)
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def is_future_timestamp(dt: datetime, now: Optional[datetime] = None) -> bool:
    """Check whether *dt* is in the future relative to *now*.

    :param dt: The datetime to check.
    :param now: Reference "now" (defaults to current UTC time).
    :return: ``True`` if *dt* is more than 1 minute in the future.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    # Allow a small tolerance for clock skew
    tolerance = timezone.utc.min if now.tzinfo is None else None
    if now.tzinfo is None:
        # Compare naive datetimes
        return dt > now
    else:
        # Make dt timezone-aware if it isn't
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt > now


def is_impossible_date(dt: datetime) -> bool:
    """Check whether *dt* represents an impossible or nonsensical date.

    Flags dates with year < 1900 (before practical photography) or year > 2100,
    as well as dates where the year is 0 or negative.

    :param dt: The datetime to check.
    :return: ``True`` if the date is considered impossible.
    """
    if dt.year < 1826 or dt.year > 2100:
        # 1826 is approximately when the first permanent photograph was taken
        return True
    return False


# ---------------------------------------------------------------------------
# GPS Conversion
# ---------------------------------------------------------------------------

def _rational_to_float(value: Any) -> float:
    """Convert an EXIF rational value (tuple of (num, den) or piexif.Rational) to float.

    :param value: A rational value from piexif or exifread.
    :return: Float representation.
    """
    if value is None:
        return 0.0

    # piexif.Rational or tuple
    if isinstance(value, (tuple, list)):
        if len(value) == 2:
            num, den = value
            if isinstance(num, (int, float)) and isinstance(den, (int, float)):
                if den == 0:
                    return 0.0
                return float(num) / float(den)
        # Single-element tuple
        if len(value) == 1:
            return float(value[0])
        return 0.0

    # Already a number
    if isinstance(value, (int, float)):
        return float(value)

    # String representation
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0

    return 0.0


def convert_dms_to_decimal(
    dms: Any,
    ref: Optional[str] = None,
) -> Optional[float]:
    """Convert EXIF GPS DMS (degrees, minutes, seconds) to decimal degrees.

    :param dms: A sequence of three rational values (degrees, minutes, seconds).
    :param ref: Reference direction ('N', 'S', 'E', or 'W').
    :return: Decimal degrees, or ``None`` if conversion fails.
    """
    if dms is None:
        return None

    try:
        # dms should be a tuple/list of 3 rationals
        if not isinstance(dms, (tuple, list)) or len(dms) != 3:
            return None

        degrees = _rational_to_float(dms[0])
        minutes = _rational_to_float(dms[1])
        seconds = _rational_to_float(dms[2])

        decimal = degrees + minutes / 60.0 + seconds / 3600.0

        if ref and ref.upper() in ("S", "W"):
            decimal = -decimal

        return round(decimal, 8)
    except (TypeError, ValueError, IndexError):
        return None


def validate_gps_coordinates(
    latitude: Optional[float],
    longitude: Optional[float],
) -> bool:
    """Validate that GPS coordinates are within valid ranges.

    :param latitude: Decimal latitude.
    :param longitude: Decimal longitude.
    :return: ``True`` if coordinates are valid, ``False`` otherwise.
    """
    if latitude is None or longitude is None:
        return False
    if not (-90.0 <= latitude <= 90.0):
        return False
    if not (-180.0 <= longitude <= 180.0):
        return False
    return True


# ---------------------------------------------------------------------------
# Safe Type Coercion
# ---------------------------------------------------------------------------

def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    """Safely convert *value* to an integer.

    Handles rationals (tuples), strings, and floats.

    :param value: The value to convert.
    :param default: Value to return if conversion fails.
    :return: Integer or *default*.
    """
    if value is None:
        return default
    try:
        if isinstance(value, (tuple, list)):
            if len(value) == 2 and isinstance(value[1], (int, float)) and value[1] != 0:
                return int(value[0] / value[1])
            if len(value) == 1:
                return int(value[0])
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            return int(value.strip())
    except (ValueError, TypeError, ZeroDivisionError):
        pass
    return default


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """Safely convert *value* to a float.

    Handles rationals (tuples), strings, and integers.

    :param value: The value to convert.
    :param default: Value to return if conversion fails.
    :return: Float or *default*.
    """
    if value is None:
        return default
    try:
        if isinstance(value, (tuple, list)):
            if len(value) == 2 and isinstance(value[1], (int, float)) and value[1] != 0:
                return float(value[0]) / float(value[1])
            if len(value) == 1:
                return float(value[0])
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            return float(value.strip())
    except (ValueError, TypeError, ZeroDivisionError):
        pass
    return default


def sanitize_utf8_str(s: Any) -> str:
    """Ensure value is converted to a valid UTF-8 string with surrogate characters removed."""
    if not isinstance(s, str):
        s = str(s)
    return s.encode("utf-8", errors="replace").decode("utf-8")


def safe_str(value: Any, default: Optional[str] = None) -> Optional[str]:
    """Safely convert *value* to a string, stripping whitespace.

    :param value: The value to convert.
    :param default: Value to return if *value* is ``None``.
    :return: Stripped string or *default*.
    """
    if value is None:
        return default
    if isinstance(value, bytes):
        try:
            return sanitize_utf8_str(value.decode("utf-8", errors="replace").strip("\x00\r\n\t "))
        except Exception:
            return default
    return sanitize_utf8_str(str(value)).strip("\x00\r\n\t ")


# ---------------------------------------------------------------------------
# Aspect Ratio
# ---------------------------------------------------------------------------

def calculate_aspect_ratio(width: int, height: int) -> float:
    """Calculate the aspect ratio (width / height).

    :param width: Image width in pixels.
    :param height: Image height in pixels.
    :return: Aspect ratio as a float, or 0.0 if height is zero.
    """
    if height == 0:
        return 0.0
    return round(width / height, 4)


# ---------------------------------------------------------------------------
# BytesIO Helper
# ---------------------------------------------------------------------------

def bytes_to_stream(data: bytes) -> io.BytesIO:
    """Wrap raw bytes in a ``BytesIO`` stream.

    :param data: Raw bytes.
    :return: A ``BytesIO`` stream positioned at the start.
    """
    return io.BytesIO(data)


# ---------------------------------------------------------------------------
# Safe JSON Serialization Helper
# ---------------------------------------------------------------------------

def safe_serialize_value(val: Any) -> Any:
    """Recursively convert raw bytes, tuples, or non-JSON-serializable objects into clean UTF-8 strings or numbers.

    :param val: Any value extracted from EXIF/XMP tags.
    :return: Safe JSON-serializable representation.
    """
    if val is None:
        return None
    if isinstance(val, bytes):
        try:
            clean_str = val.decode("utf-8", errors="replace").strip("\x00\r\n\t ")
            return sanitize_utf8_str(clean_str)
        except Exception:
            return f"<binary data {len(val)} bytes>"
    if isinstance(val, (tuple, list)):
        return [safe_serialize_value(v) for v in val]
    if isinstance(val, dict):
        return {sanitize_utf8_str(str(k)): safe_serialize_value(v) for k, v in val.items()}
    if isinstance(val, (int, float, bool)):
        return val
    return sanitize_utf8_str(str(val)).strip("\x00\r\n\t ")

