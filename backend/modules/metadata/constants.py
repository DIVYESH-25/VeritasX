"""
Metadata Analysis Module — Static Constants & Lookup Tables

Contains all static data used by the Metadata Analysis module:
- EXIF tag name mappings
- Software / AI-generator signature strings
- Severity levels
- Validation issue type identifiers
- Observation type identifiers
- MIME type mappings
- Camera manufacturer classification lists
"""

from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Severity Levels
# ---------------------------------------------------------------------------

SEVERITY_LOW: str = "low"
SEVERITY_MEDIUM: str = "medium"
SEVERITY_HIGH: str = "high"
SEVERITY_CRITICAL: str = "critical"

VALID_SEVERITIES: Tuple[str, ...] = (
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_HIGH,
    SEVERITY_CRITICAL,
)

# ---------------------------------------------------------------------------
# Validation Issue Type Identifiers
# ---------------------------------------------------------------------------

# Each constant maps to a short, machine-readable issue code.
ISSUE_CORRUPTED_METADATA: str = "CORRUPTED_METADATA"
ISSUE_MISSING_EXIF: str = "MISSING_EXIF"
ISSUE_INVALID_TIMESTAMP: str = "INVALID_TIMESTAMP"
ISSUE_FUTURE_TIMESTAMP: str = "FUTURE_TIMESTAMP"
ISSUE_IMPOSSIBLE_DATE: str = "IMPOSSIBLE_DATE"
ISSUE_INVALID_GPS: str = "INVALID_GPS"
ISSUE_EMPTY_METADATA: str = "EMPTY_METADATA"
ISSUE_DUPLICATE_FIELD: str = "DUPLICATE_FIELD"
ISSUE_UNSUPPORTED_METADATA: str = "UNSUPPORTED_METADATA"
ISSUE_BROKEN_EXIF: str = "BROKEN_EXIF"

# ---------------------------------------------------------------------------
# Observation Type Identifiers
# ---------------------------------------------------------------------------

OBS_EDITED_PHOTOSHOP: str = "edited_photoshop"
OBS_EXPORTED_GIMP: str = "exported_gimp"
OBS_EXPORTED_CANVA: str = "exported_canva"
OBS_SAVED_STABLE_DIFFUSION: str = "saved_stable_diffusion"
OBS_SAVED_MIDJOURNEY: str = "saved_midjourney"
OBS_METADATA_REMOVED: str = "metadata_removed"
OBS_CAMERA_MISSING: str = "camera_missing"
OBS_GPS_REMOVED: str = "gps_removed"
OBS_TIMESTAMP_MISMATCH: str = "timestamp_mismatch"
OBS_SCREENSHOT_DETECTED: str = "screenshot_detected"
OBS_MOBILE_CAMERA: str = "mobile_camera"
OBS_DSLR_IMAGE: str = "dslr_image"
OBS_PNG_WITHOUT_EXIF: str = "png_without_exif"
OBS_METADATA_INCONSISTENT: str = "metadata_inconsistent"

# ---------------------------------------------------------------------------
# Software / AI-Generator Signature Strings
# ---------------------------------------------------------------------------
# Maps an observation type to a list of case-insensitive substrings that, when
# found in the EXIF Software tag, trigger the corresponding observation.

SOFTWARE_SIGNATURES: Dict[str, List[str]] = {
    OBS_EDITED_PHOTOSHOP: [
        "photoshop",
        "adobe photoshop",
        "adobe imageready",
        "adobe photoshop elements",
        "lightroom",
    ],
    OBS_EXPORTED_GIMP: [
        "gimp",
    ],
    OBS_EXPORTED_CANVA: [
        "canva",
    ],
    OBS_SAVED_STABLE_DIFFUSION: [
        "stable diffusion",
        "sd-scripts",
        "automatic1111",
        "automatic1111-webui",
        "comfyui",
        "invokeai",
        "diffusers",
        "kohya",
        "novelai",
    ],
    OBS_SAVED_MIDJOURNEY: [
        "midjourney",
    ],
}

# Substrings that suggest the image is a screenshot.
SCREENSHOT_SIGNATURES: List[str] = [
    "screenshot",
    "snipping tool",
    "snippingtool",
    "sharex",
    "greenshot",
    "lightshot",
    "greenshot",
    "windows screenshot",
    "macos screenshot",
    "ios screenshot",
    "android screenshot",
]

# ---------------------------------------------------------------------------
# Camera Manufacturer Classification
# ---------------------------------------------------------------------------

MOBILE_CAMERA_MAKES: List[str] = [
    "apple",
    "samsung",
    "google",
    "google inc",
    "huawei",
    "xiaomi",
    "oppo",
    "vivo",
    "oneplus",
    "realme",
    "motorola",
    "lenovo",
    "nokia",
    "sony",  # Sony phones (distinct from Sony Alpha DSLRs)
    "lg",
    "htc",
    "zte",
    "meizu",
    "blackberry",
]

PROFESSIONAL_CAMERA_MAKES: List[str] = [
    "canon",
    "nikon",
    "sony",
    "sony corporation",
    "fujifilm",
    "olympus",
    "panasonic",
    "pentax",
    "leica",
    "hasselblad",
    "phase one",
    "medium format",
]

# ---------------------------------------------------------------------------
# MIME Type Mappings
# ---------------------------------------------------------------------------

EXTENSION_TO_MIME: Dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".bmp": "image/bmp",
    ".gif": "image/gif",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".avif": "image/avif",
}

# ---------------------------------------------------------------------------
# EXIF Tag Name Mappings (piexif section → {tag_id: human_name})
# ---------------------------------------------------------------------------
# These are the EXIF tags we explicitly extract and map to our ExifData model.
# Tag IDs follow the EXIF specification (https://exiv2.org/tags.html).

EXIF_0TH_TAG_MAP: Dict[int, str] = {
    271: "Make",
    272: "Model",
    274: "Orientation",
    305: "Software",
    315: "Artist",
    318: "Copyright",
    306: "DateTime",
}

EXIF_EXIF_TAG_MAP: Dict[int, str] = {
    36867: "DateTimeOriginal",
    36868: "DateTimeDigitized",
    33432: "Copyright",
    33434: "ExposureTime",
    33437: "FNumber",
    34850: "ExposureProgram",
    34855: "ISOSpeedRatings",
    34856: "SensitivityType",
    36864: "ExifVersion",
    37377: "ShutterSpeedValue",
    37378: "ApertureValue",
    37379: "BrightnessValue",
    37380: "ExposureBiasValue",
    37381: "MaxApertureValue",
    37383: "SubjectDistance",
    37384: "MeteringMode",
    37385: "LightSource",
    37386: "FocalLength",
    37396: "SubjectArea",
    40960: "FlashEnergy",
    40961: "Flash",
    40962: "FocalLengthIn35mmFilm",
    41986: "WhiteBalance",
    41987: "DigitalZoomRatio",
    41988: "FocalLengthIn35mmFilm",
    41990: "SubjectDistanceRange",
    41991: "OwnerName",
    41993: "ImageDescription",
    41994: "ImageNumber",
    41995: "ImageHistory",
    42016: "RelatedImageFile",
    42032: "CameraOwnerName",
    42033: "LensSpecification",
    42034: "LensModel",
    42036: "LensMake",
    42037: "UserComment",
    42240: "SubSecTime",
}

EXIF_GPS_TAG_MAP: Dict[int, str] = {
    1: "GPSLatitudeRef",
    2: "GPSLatitude",
    3: "GPSLongitudeRef",
    4: "GPSLongitude",
    5: "GPSAltitudeRef",
    6: "GPSAltitude",
    7: "GPSTimeStamp",
    8: "GPSSatellites",
    9: "GPSStatus",
    10: "GPSMeasureMode",
    11: "GPSDOP",
    12: "GPSSpeedRef",
    13: "GPSSpeed",
    14: "GPSCourse",
    15: "GPSCourseRef",
    16: "GPSDay",
    17: "GPSDate",
    18: "GPSDifferential",
    23: "GPSImgDirection",
    24: "GPSImgDirectionRef",
    25: "GPSMapDatum",
    27: "GPSDateStamp",
    28: "GPSDifferential",
    29: "GPSProcessingMethod",
    30: "GPSAreaInformation",
    31: "GPSDate",
}

# ---------------------------------------------------------------------------
# EXIF Orientation Values
# ---------------------------------------------------------------------------

ORIENTATION_VALUES: Dict[int, str] = {
    1: "Horizontal (normal)",
    2: "Mirror horizontal",
    3: "Rotate 180",
    4: "Mirror vertical",
    5: "Mirror horizontal and rotate 270 CW",
    6: "Rotate 90 CW",
    7: "Mirror horizontal and rotate 90 CW",
    8: "Rotate 270 CW",
}

# ---------------------------------------------------------------------------
# Flash Values (EXIF spec)
# ---------------------------------------------------------------------------

FLASH_VALUES: Dict[int, str] = {
    0: "Flash did not fire",
    1: "Flash fired",
    5: "Strobe return light not detected",
    7: "Strobe return light detected",
    9: "Flash fired, compulsory mode",
    13: "Flash fired, compulsory mode, return light not detected",
    15: "Flash fired, compulsory mode, return light detected",
    16: "Flash did not fire, compulsory mode",
    24: "Flash did not fire, auto mode",
    32: "Flash fired, auto mode",
    33: "Flash fired, auto mode, return light not detected",
    35: "Flash fired, auto mode, return light detected",
    36: "No flash function",
    48: "Flash fired, red-eye reduction mode",
    49: "Flash fired, red-eye reduction mode, return light not detected",
    51: "Flash fired, red-eye reduction mode, return light detected",
    56: "Flash fired, auto mode, red-eye reduction mode",
    57: "Flash fired, auto mode, red-eye reduction mode, return light not detected",
    59: "Flash fired, auto mode, red-eye reduction mode, return light detected",
    64: "Flash did not fire, auto mode, return light not detected",
    65: "Flash did not fire, auto mode, return light detected",
    80: "Flash fired, auto mode, red-eye reduction mode, return light not detected",
    81: "Flash fired, auto mode, red-eye reduction mode, return light detected",
}

# ---------------------------------------------------------------------------
# White Balance Values
# ---------------------------------------------------------------------------

WHITE_BALANCE_VALUES: Dict[int, str] = {
    0: "Auto white balance",
    1: "Manual white balance",
    2: "Auto white balance (BP800)",
    3: "Manual white balance (BP800)",
}

# ---------------------------------------------------------------------------
# Module Constants
# ---------------------------------------------------------------------------

MODULE_NAME: str = "Metadata Analysis"
MODULE_DESCRIPTION: str = (
    "Extracts, validates, and analyzes image metadata (EXIF, XMP, ICC profiles, "
    "and AI generator signatures) to assess media provenance and detect forensic anomalies."
)

# Maximum image dimension for "large image" detection in tests
LARGE_IMAGE_THRESHOLD: int = 4000

# Minimum image dimension for "small image" detection in tests
SMALL_IMAGE_THRESHOLD: int = 200
