"""
Metadata Analysis Module — Pydantic Data Models

Defines all data transfer objects (DTOs) used throughout the Metadata Analysis
module.  Models follow Pydantic v2 conventions and are serialisable to JSON
for inclusion in the standardised ``ModuleResult.data`` payload.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# File Information
# ---------------------------------------------------------------------------

class FileInfo(BaseModel):
    """Static file-system-level information about the analysed image."""

    filename: str = Field(..., description="Original filename of the uploaded image")
    extension: str = Field(..., description="File extension including the dot, e.g. '.jpg'")
    mime_type: str = Field(..., description="Detected MIME type, e.g. 'image/jpeg'")
    file_size: int = Field(..., description="File size in bytes")
    sha256: str = Field(..., description="SHA-256 hash of the raw image bytes")
    md5: str = Field(..., description="MD5 hash of the raw image bytes")


# ---------------------------------------------------------------------------
# Image Information
# ---------------------------------------------------------------------------

class ImageInfo(BaseModel):
    """Decoded image-level information obtained via Pillow."""

    width: int = Field(..., ge=0, description="Image width in pixels")
    height: int = Field(..., ge=0, description="Image height in pixels")
    aspect_ratio: float = Field(..., ge=0.0, description="Width / height ratio")
    color_mode: str = Field(..., description="Pillow color mode, e.g. 'RGB', 'RGBA', 'CMYK'")
    color_profile: Optional[str] = Field(default=None, description="ICC profile description if present")
    bit_depth: Optional[int] = Field(default=None, ge=1, description="Bits per channel")
    compression_type: Optional[str] = Field(default=None, description="Compression algorithm, e.g. 'raw', 'jpeg', 'deflate'")
    dpi: Optional[Tuple[float, float]] = Field(default=None, description="(x_dpi, y_dpi) tuple")
    format: str = Field(..., description="Pillow-detected format, e.g. 'JPEG', 'PNG', 'WEBP'")


# ---------------------------------------------------------------------------
# EXIF Data
# ---------------------------------------------------------------------------

class GpsInfo(BaseModel):
    """Parsed GPS information converted to decimal degrees."""

    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    latitude_ref: Optional[str] = Field(default=None, description="'N' or 'S'")
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    longitude_ref: Optional[str] = Field(default=None, description="'E' or 'W'")
    altitude: Optional[float] = Field(default=None)
    altitude_ref: Optional[str] = Field(default=None, description="'Above sea level' or 'Below sea level'")
    timestamp: Optional[str] = Field(default=None, description="GPS timestamp string")
    raw: Dict[str, Any] = Field(default_factory=dict, description="Raw GPS tag values")


class ExifData(BaseModel):
    """Structured EXIF metadata extracted from the image."""

    # Camera / device information
    camera_make: Optional[str] = Field(default=None)
    camera_model: Optional[str] = Field(default=None)
    lens: Optional[str] = Field(default=None)
    lens_make: Optional[str] = Field(default=None)

    # Software / editing information
    software: Optional[str] = Field(default=None)
    artist: Optional[str] = Field(default=None)
    copyright: Optional[str] = Field(default=None)

    # Timestamps
    datetime_original: Optional[str] = Field(default=None, description="When the image was originally captured")
    datetime_digitized: Optional[str] = Field(default=None, description="When the image was digitized")
    datetime_modified: Optional[str] = Field(default=None, description="When the image was last modified")

    # Exposure / camera settings
    exposure_time: Optional[str] = Field(default=None)
    aperture: Optional[str] = Field(default=None)
    iso: Optional[int] = Field(default=None, ge=0)
    flash: Optional[str] = Field(default=None)
    focal_length: Optional[str] = Field(default=None)
    white_balance: Optional[str] = Field(default=None)
    exposure_program: Optional[str] = Field(default=None)
    metering_mode: Optional[str] = Field(default=None)
    light_source: Optional[str] = Field(default=None)
    exposure_bias: Optional[str] = Field(default=None)
    max_aperture: Optional[str] = Field(default=None)
    subject_distance: Optional[str] = Field(default=None)
    image_description: Optional[str] = Field(default=None)
    orientation: Optional[str] = Field(default=None)

    # GPS
    gps: Optional[GpsInfo] = Field(default=None)

    # Metadata availability summary
    has_exif: bool = Field(default=False, description="Whether any EXIF data was found")
    exif_field_count: int = Field(default=0, ge=0, description="Number of EXIF fields extracted")

    # Raw tags (preserved for forensic inspection)
    raw_tags: Dict[str, Any] = Field(default_factory=dict, description="All raw EXIF tag name → value pairs")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ValidationIssue(BaseModel):
    """A single validation issue discovered during metadata validation."""

    type: str = Field(..., description="Machine-readable issue code, e.g. 'MISSING_EXIF'")
    severity: str = Field(..., description="Severity: 'low', 'medium', 'high', or 'critical'")
    description: str = Field(..., description="Human-readable description of the issue")
    field: Optional[str] = Field(default=None, description="The metadata field the issue pertains to, if applicable")


class ValidationResult(BaseModel):
    """Aggregated validation result containing all issues found."""

    total_issues: int = Field(default=0, ge=0)
    issues_by_severity: Dict[str, int] = Field(default_factory=dict)
    issues: List[ValidationIssue] = Field(default_factory=list)

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue and update summary counters."""
        self.issues.append(issue)
        self.total_issues += 1
        self.issues_by_severity[issue.severity] = (
            self.issues_by_severity.get(issue.severity, 0) + 1
        )


# ---------------------------------------------------------------------------
# Observations
# ---------------------------------------------------------------------------

class Observation(BaseModel):
    """A single forensic observation generated by the rule-based analyzer."""

    title: str = Field(..., description="Short, human-readable title of the observation")
    description: str = Field(..., description="Detailed explanation of what was detected")
    severity: str = Field(..., description="Severity level: 'low', 'medium', 'high', or 'critical'")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in this observation (0.0–1.0)")
    observation_type: Optional[str] = Field(default=None, description="Machine-readable observation type code")


# ---------------------------------------------------------------------------
# Extraction Result (internal DTO)
# ---------------------------------------------------------------------------

class ExtractionResult(BaseModel):
    """Internal DTO carrying the output of the extraction layer to downstream layers."""

    file_info: FileInfo
    image_info: ImageInfo
    exif_data: ExifData
    raw_exif_data: Dict[str, Any] = Field(default_factory=dict, description="Raw EXIF dict from piexif/exifread")

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# Metadata Result (final structured output)
# ---------------------------------------------------------------------------

class MetadataResult(BaseModel):
    """Final structured metadata analysis result included in ModuleResult.data."""

    file: FileInfo
    image: ImageInfo
    exif: ExifData
    validation: Dict[str, Any]
    observations: List[Observation]
    metadata_score: float = Field(..., ge=0.0, le=1.0, description="0.0 = suspicious, 1.0 = trustworthy")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in the analysis")


# ---------------------------------------------------------------------------
# Score Result (internal DTO)
# ---------------------------------------------------------------------------

class ScoreResult(BaseModel):
    """Internal DTO carrying scores from the scoring engine."""

    metadata_score: float = Field(..., ge=0.0, le=1.0)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
