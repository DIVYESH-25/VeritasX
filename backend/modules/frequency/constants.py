"""
Frequency Analysis Module — Static Constants & Lookup Tables

Contains all static data used by the Frequency Analysis module:
- Severity levels
- Module identity constants
- FFT algorithm configuration
- Scoring thresholds and weights
- Observation type identifiers
- Frequency band definitions
- Image size thresholds for confidence scoring
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

MODULE_NAME: str = "Frequency Analysis"
MODULE_DESCRIPTION: str = (
    "Analyzes spatial frequency-domain characteristics (FFT/DFT) of the image to "
    "detect periodic structures, checkerboard artifacts, aliasing, banding, "
    "ringing, and other frequency-domain anomalies that may indicate AI synthesis "
    "or digital manipulation."
)

# ---------------------------------------------------------------------------
# FFT Algorithm Configuration
# ---------------------------------------------------------------------------

# Maximum image dimension for FFT processing (to avoid memory explosion on large images)
FFT_MAX_DIMENSION: int = 1024

# Whether to apply a Hann window before FFT (reduces spectral leakage)
APPLY_HANN_WINDOW: bool = True

# ---------------------------------------------------------------------------
# Frequency Band Definitions
# ---------------------------------------------------------------------------

# Low-frequency radius as a fraction of the smaller image dimension
# Energy within this radius from the center is considered "low frequency"
LOW_FREQ_RADIUS_FRACTION: float = 0.05  # 5% from center

# High-frequency threshold: energy outside this fraction of max radius
# is considered "high frequency"
HIGH_FREQ_RADIUS_FRACTION: float = 0.50  # outer 50%

# ---------------------------------------------------------------------------
# Spectral Analysis Thresholds
# ---------------------------------------------------------------------------

# Spectral entropy threshold (normalized 0-1)
# Higher entropy = more uniform energy distribution = natural image tendency
SPECTRAL_ENTROPY_HIGH_THRESHOLD: float = 0.80  # Very uniform (suspicious for AI)
SPECTRAL_ENTROPY_LOW_THRESHOLD: float = 0.40   # Highly concentrated (camera/photo)

# Energy ratio threshold (low_freq / high_freq)
# High ratio = natural photo (dominant low frequencies)
# Low ratio = synthetic/unnaturally flat (GAN/diffusion artifacts)
ENERGY_RATIO_HIGH_THRESHOLD: float = 8.0   # Natural image typically has much more low-freq energy
ENERGY_RATIO_LOW_THRESHOLD: float = 1.0   # Suspiciously flat spectrum

# Standard deviation of magnitude spectrum thresholds
MAGNITUDE_STD_HIGH_THRESHOLD: float = 50.0   # High variance = natural variation
MAGNITUDE_STD_LOW_THRESHOLD: float = 15.0   # Low variance = unusually smooth

# Horizontal/vertical frequency balance threshold
# Ratio of horizontal to vertical energy; deviation from 1.0 indicates asymmetry
HV_BALANCE_ASYMMETRY_THRESHOLD: float = 2.0  # 2:1 ratio is notable

# Peak-to-mean ratio: indicates periodic/spiky frequency content
PEAK_TO_MEAN_HIGH_THRESHOLD: float = 15.0   # Strong periodic structure
PEAK_TO_MEAN_LOW_THRESHOLD: float = 5.0    # Smooth spectrum

# Radial symmetry: correlation between opposite quadrants of the spectrum
# Natural images tend to have some symmetry; perfectly symmetric can indicate artifacts
RADIAL_SYMMETRY_HIGH_THRESHOLD: float = 0.95  # Very symmetric
RADIAL_SYMMETRY_LOW_THRESHOLD: float = 0.30   # Very asymmetric

# ---------------------------------------------------------------------------
# Scoring Thresholds
# ---------------------------------------------------------------------------

# Image dimensions below which confidence in frequency analysis drops
FREQ_CONFIDENCE_MIN_WIDTH: int = 32
FREQ_CONFIDENCE_MIN_HEIGHT: int = 32

# Image size tiers for confidence scoring
FREQUENCY_PIXEL_TIER_1: int = 10000      # 10K pixels
FREQUENCY_PIXEL_TIER_2: int = 100000     # 100K pixels
FREQUENCY_PIXEL_TIER_3: int = 1000000    # 1MP

# Maximum dimension for FFT magnitude visualization (to limit base64 size)
FFT_IMAGE_MAX_DIMENSION: int = 512

# ---------------------------------------------------------------------------
# Scoring Weights (must sum to 1.0 for frequency_score components)
# ---------------------------------------------------------------------------

WEIGHT_ENERGY_RATIO: float = 0.25
WEIGHT_SPECTRAL_ENTROPY: float = 0.20
WEIGHT_MAGNITUDE_STD: float = 0.15
WEIGHT_HV_BALANCE: float = 0.15
WEIGHT_PEAK_TO_MEAN: float = 0.15
WEIGHT_RADIAL_SYMMETRY: float = 0.10

# ---------------------------------------------------------------------------
# Observation Type Identifiers
# ---------------------------------------------------------------------------

OBS_PERIODIC_STRUCTURES: str = "periodic_structures"
OBS_CHECKERBOARD_PATTERN: str = "checkerboard_pattern"
OBS_ALIASING_ARTIFACTS: str = "aliasing_artifacts"
OBS_HIGH_FREQ_ANOMALY: str = "high_freq_anomaly"
OBS_SPECTRAL_ASYMMETRY: str = "spectral_asymmetry"
OBS_BANDING: str = "banding"
OBS_RINGING_ARTIFACTS: str = "ringing_artifacts"
OBS_SPECTRUM_BALANCED: str = "spectrum_balanced"
OBS_LOW_FREQ_DOMINANT: str = "low_freq_dominant"
OBS_SMOOTH_SPECTRUM: str = "smooth_spectrum"
OBS_NATURAL_FOOTPRINT: str = "natural_frequency_footprint"

# ---------------------------------------------------------------------------
# Image Format Constants
# ---------------------------------------------------------------------------

JPEG_FORMATS: Tuple[str, ...] = ("JPEG", "JPG")
PNG_FORMATS: Tuple[str, ...] = ("PNG",)
WEBP_FORMATS: Tuple[str, ...] = ("WEBP",)
