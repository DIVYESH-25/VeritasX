"""
Error Level Analysis Module — Static Constants & Lookup Tables

Contains all static data used by the ELA module:
- Severity levels
- Module identity constants
- ELA algorithm configuration
- Scoring thresholds and weights
- Observation type identifiers
- Suspicious region detection parameters
"""

from typing import List, Tuple

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
# Module Identity
# ---------------------------------------------------------------------------

MODULE_NAME: str = "Error Level Analysis"
MODULE_DESCRIPTION: str = (
    "Analyzes JPEG compression error levels across image regions to detect "
    "localized resaving, recompression anomalies, and potential manipulation "
    "or synthetic generation indicators."
)

# ---------------------------------------------------------------------------
# ELA Algorithm Configuration
# ---------------------------------------------------------------------------

# Default JPEG quality for re-compression during ELA
ELA_JPEG_QUALITY: int = 90

# Supported JPEG quality levels for future configuration
SUPPORTED_JPEG_QUALITIES: List[int] = [75, 85, 90, 95]

# ---------------------------------------------------------------------------
# Suspicious Region Detection Parameters
# ---------------------------------------------------------------------------

# Pixels with absolute difference above this threshold are considered "high error"
HIGH_ERROR_PIXEL_THRESHOLD: float = 15.0

# Minimum pixel area for a detected region to be reported as suspicious
SUSPICIOUS_REGION_MIN_AREA: int = 100

# Minimum mean difference intensity for a region to be considered suspicious
SUSPICIOUS_REGION_MIN_INTENSITY: float = 10.0

# Number of standard deviations above the mean for region threshold
REGION_THRESHOLD_SIGMA: float = 2.0

# ---------------------------------------------------------------------------
# Scoring Thresholds
# ---------------------------------------------------------------------------

# Average error above which the image is considered suspicious
AVG_ERROR_THRESHOLD: float = 8.0

# Standard deviation above which the image is considered suspicious
STD_DEV_THRESHOLD: float = 5.0

# Percentage of high-error pixels above which the image is suspicious
HIGH_ERROR_PIXEL_PERCENTAGE_THRESHOLD: float = 5.0

# Dynamic range above which the image is considered suspicious
DYNAMIC_RANGE_THRESHOLD: float = 50.0

# Maximum number of suspicious regions before heavy penalty
MAX_SUSPICIOUS_REGIONS: int = 10

# ---------------------------------------------------------------------------
# Scoring Weights (must sum to 1.0 for ela_score components)
# ---------------------------------------------------------------------------

WEIGHT_AVERAGE_ERROR: float = 0.25
WEIGHT_STD_DEV: float = 0.20
WEIGHT_HIGH_ERROR_PIXELS: float = 0.25
WEIGHT_DYNAMIC_RANGE: float = 0.15
WEIGHT_SUSPICIOUS_REGIONS: float = 0.15

# ---------------------------------------------------------------------------
# Observation Type Identifiers
# ---------------------------------------------------------------------------

OBS_UNIFORM_COMPRESSION: str = "uniform_compression"
OBS_LOCALIZED_RECOMPRESSION: str = "localized_recompression"
OBS_EDITED_REGION_SUSPECTED: str = "edited_region_suspected"
OBS_HEAVY_JPEG_ARTIFACTS: str = "heavy_jpeg_artifacts"
OBS_MULTIPLE_COMPRESSION_SIGNATURES: str = "multiple_compression_signatures"
OBS_CONSISTENT_CAMERA_COMPRESSION: str = "consistent_camera_compression"
OBS_SCREENSHOT_CHARACTERISTICS: str = "screenshot_characteristics"
OBS_POSSIBLE_SYNTHETIC_GENERATION: str = "possible_synthetic_generation"

# ---------------------------------------------------------------------------
# Image Size Thresholds for Confidence Scoring
# ---------------------------------------------------------------------------

# Minimum pixel count for reliable ELA analysis
MIN_PIXELS_FOR_CONFIDENCE: int = 10000  # 10K pixels

# Pixel count thresholds for confidence tiers
CONFIDENCE_PIXEL_TIER_1: int = 10000      # 10K
CONFIDENCE_PIXEL_TIER_2: int = 100000     # 100K
CONFIDENCE_PIXEL_TIER_3: int = 1000000    # 1MP

# Maximum dimension for ELA image visualization (to limit base64 size)
ELA_IMAGE_MAX_DIMENSION: int = 1024

# ---------------------------------------------------------------------------
# Image Format Constants
# ---------------------------------------------------------------------------

JPEG_FORMATS: Tuple[str, ...] = ("JPEG", "JPG")
PNG_FORMATS: Tuple[str, ...] = ("PNG",)
WEBP_FORMATS: Tuple[str, ...] = ("WEBP",)
