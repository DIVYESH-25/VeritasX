"""
Metadata Analysis Module — Validation Layer

The ``MetadataValidator`` inspects extracted metadata and produces a list of
``ValidationIssue`` objects describing any anomalies, inconsistencies, or
forensic red flags.

Validation checks performed:
1.  Corrupted metadata
2.  Missing EXIF
3.  Invalid timestamps
4.  Future timestamps
5.  Impossible dates
6.  Invalid GPS
7.  Empty metadata
8.  Duplicate fields
9.  Unsupported metadata
10. Broken EXIF
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import List, Optional

from backend.modules.metadata.constants import (
    ISSUE_BROKEN_EXIF,
    ISSUE_CORRUPTED_METADATA,
    ISSUE_DUPLICATE_FIELD,
    ISSUE_EMPTY_METADATA,
    ISSUE_FUTURE_TIMESTAMP,
    ISSUE_IMPOSSIBLE_DATE,
    ISSUE_INVALID_GPS,
    ISSUE_INVALID_TIMESTAMP,
    ISSUE_MISSING_EXIF,
    ISSUE_UNSUPPORTED_METADATA,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)
from backend.modules.metadata.models import (
    ExifData,
    ExtractionResult,
    FileInfo,
    GpsInfo,
    ImageInfo,
    ValidationIssue,
    ValidationResult,
)
from backend.modules.metadata.utils import (
    is_future_timestamp,
    is_impossible_date,
    parse_exif_timestamp,
    validate_gps_coordinates,
)

logger = logging.getLogger("veritasx.modules.metadata.validator")


class MetadataValidator:
    """Validates extracted metadata and generates validation issues.

    This class is stateless and safe to reuse across requests.
    """

    def __init__(self) -> None:
        """Initialise the validator."""
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, extraction_result: ExtractionResult, request_id: str) -> ValidationResult:
        """Run all validation checks on the extracted metadata.

        :param extraction_result: The result of metadata extraction.
        :param request_id: Request ID for tracing.
        :return: ``ValidationResult`` containing all issues found.
        """
        start = time.perf_counter()
        logger.info(f"[{request_id}] Starting metadata validation...")

        result = ValidationResult()

        # Run each validation check
        self._check_missing_exif(extraction_result, result)
        self._check_empty_metadata(extraction_result, result)
        self._check_broken_exif(extraction_result, result)
        self._check_corrupted_metadata(extraction_result, result)
        self._check_timestamps(extraction_result, result)
        self._check_gps(extraction_result, result)
        self._check_duplicate_fields(extraction_result, result)
        self._check_unsupported_metadata(extraction_result, result)

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            f"[{request_id}] Validation complete in {elapsed_ms}ms | "
            f"Issues found: {result.total_issues} | "
            f"By severity: {result.issues_by_severity}"
        )

        return result

    # ------------------------------------------------------------------
    # Validation Checks
    # ------------------------------------------------------------------

    def _check_missing_exif(
        self,
        extraction: ExtractionResult,
        result: ValidationResult,
    ) -> None:
        """Check if EXIF data is missing.

        :param extraction: Extraction result to validate.
        :param result: Validation result to append issues to.
        """
        exif = extraction.exif_data

        if not exif.has_exif:
            result.add_issue(ValidationIssue(
                type=ISSUE_MISSING_EXIF,
                severity=SEVERITY_HIGH,
                description="No EXIF metadata found in the image. The image may have had metadata stripped.",
                field="exif",
            ))
        elif exif.exif_field_count == 0:
            result.add_issue(ValidationIssue(
                type=ISSUE_MISSING_EXIF,
                severity=SEVERITY_MEDIUM,
                description="EXIF data container exists but contains no readable fields.",
                field="exif",
            ))

    def _check_empty_metadata(
        self,
        extraction: ExtractionResult,
        result: ValidationResult,
    ) -> None:
        """Check if the metadata is completely empty (all fields are None).

        :param extraction: Extraction result to validate.
        :param result: Validation result to append issues to.
        """
        exif = extraction.exif_data

        # Check if all key EXIF fields are None/empty
        key_fields = [
            exif.camera_make,
            exif.camera_model,
            exif.software,
            exif.datetime_original,
            exif.datetime_digitized,
            exif.datetime_modified,
            exif.iso,
            exif.focal_length,
            exif.aperture,
            exif.exposure_time,
        ]

        non_empty_count = sum(1 for f in key_fields if f is not None and f != "")

        if exif.has_exif and non_empty_count == 0:
            result.add_issue(ValidationIssue(
                type=ISSUE_EMPTY_METADATA,
                severity=SEVERITY_CRITICAL,
                description="EXIF data exists but all key metadata fields are empty. Metadata may have been intentionally cleared.",
                field="exif",
            ))
        elif not exif.has_exif:
            # Already flagged by _check_missing_exif; add a lower-severity note
            result.add_issue(ValidationIssue(
                type=ISSUE_EMPTY_METADATA,
                severity=SEVERITY_LOW,
                description="No EXIF metadata present — all metadata fields are empty.",
                field="exif",
            ))

    def _check_broken_exif(
        self,
        extraction: ExtractionResult,
        result: ValidationResult,
    ) -> None:
        """Check for broken or malformed EXIF data.

        :param extraction: Extraction result to validate.
        :param result: Validation result to append issues to.
        """
        exif = extraction.exif_data

        # Check if raw_exif_data exists but has_exif is False (extraction failed)
        if extraction.raw_exif_data and not exif.has_exif:
            result.add_issue(ValidationIssue(
                type=ISSUE_BROKEN_EXIF,
                severity=SEVERITY_HIGH,
                description="Raw EXIF data was detected but could not be parsed into structured fields. EXIF may be corrupted.",
                field="exif",
            ))

        # Check for raw tags that couldn't be mapped to known fields
        if exif.raw_tags:
            unmapped_count = sum(
                1 for k in exif.raw_tags
                if k.startswith("Tag_") or k.startswith("Exif_") or k.startswith("GPS_")
            )
            if unmapped_count > 0:
                result.add_issue(ValidationIssue(
                    type=ISSUE_BROKEN_EXIF,
                    severity=SEVERITY_LOW,
                    description=f"{unmapped_count} EXIF tag(s) could not be mapped to known field names. EXIF structure may be non-standard.",
                    field="exif",
                ))

    def _check_corrupted_metadata(
        self,
        extraction: ExtractionResult,
        result: ValidationResult,
    ) -> None:
        """Check for signs of corrupted metadata.

        :param extraction: Extraction result to validate.
        :param result: Validation result to append issues to.
        """
        image_info = extraction.image_info
        file_info = extraction.file_info

        # Check for zero dimensions (corrupted image)
        if image_info.width == 0 or image_info.height == 0:
            result.add_issue(ValidationIssue(
                type=ISSUE_CORRUPTED_METADATA,
                severity=SEVERITY_CRITICAL,
                description="Image dimensions are zero. The image file may be corrupted or truncated.",
                field="image.width,height",
            ))

        # Check for unknown format
        if image_info.format == "UNKNOWN":
            result.add_issue(ValidationIssue(
                type=ISSUE_CORRUPTED_METADATA,
                severity=SEVERITY_HIGH,
                description="Image format could not be determined. The file may be corrupted or in an unsupported format.",
                field="image.format",
            ))

        # Check for unknown MIME type
        if file_info.mime_type == "application/octet-stream":
            result.add_issue(ValidationIssue(
                type=ISSUE_CORRUPTED_METADATA,
                severity=SEVERITY_MEDIUM,
                description="MIME type could not be determined. The file may not be a valid image.",
                field="file.mime_type",
            ))

    def _check_timestamps(
        self,
        extraction: ExtractionResult,
        result: ValidationResult,
    ) -> None:
        """Validate all timestamp fields.

        Checks for:
        - Invalid timestamps (unparseable)
        - Future timestamps
        - Impossible dates
        - Timestamp mismatches

        :param extraction: Extraction result to validate.
        :param result: Validation result to append issues to.
        """
        exif = extraction.exif_data
        now = datetime.now()

        # Check DateTimeOriginal
        if exif.datetime_original:
            dt = parse_exif_timestamp(exif.datetime_original)
            if dt is None:
                result.add_issue(ValidationIssue(
                    type=ISSUE_INVALID_TIMESTAMP,
                    severity=SEVERITY_MEDIUM,
                    description=f"DateTimeOriginal value '{exif.datetime_original}' could not be parsed as a valid timestamp.",
                    field="exif.datetime_original",
                ))
            else:
                if is_impossible_date(dt):
                    result.add_issue(ValidationIssue(
                        type=ISSUE_IMPOSSIBLE_DATE,
                        severity=SEVERITY_HIGH,
                        description=f"DateTimeOriginal '{exif.datetime_original}' represents an impossible date (year {dt.year}).",
                        field="exif.datetime_original",
                    ))
                if is_future_timestamp(dt, now):
                    result.add_issue(ValidationIssue(
                        type=ISSUE_FUTURE_TIMESTAMP,
                        severity=SEVERITY_HIGH,
                        description=f"DateTimeOriginal '{exif.datetime_original}' is in the future (current time: {now}).",
                        field="exif.datetime_original",
                    ))

        # Check DateTimeDigitized
        if exif.datetime_digitized:
            dt = parse_exif_timestamp(exif.datetime_digitized)
            if dt is None:
                result.add_issue(ValidationIssue(
                    type=ISSUE_INVALID_TIMESTAMP,
                    severity=SEVERITY_MEDIUM,
                    description=f"DateTimeDigitized value '{exif.datetime_digitized}' could not be parsed as a valid timestamp.",
                    field="exif.datetime_digitized",
                ))
            else:
                if is_impossible_date(dt):
                    result.add_issue(ValidationIssue(
                        type=ISSUE_IMPOSSIBLE_DATE,
                        severity=SEVERITY_HIGH,
                        description=f"DateTimeDigitized '{exif.datetime_digitized}' represents an impossible date (year {dt.year}).",
                        field="exif.datetime_digitized",
                    ))
                if is_future_timestamp(dt, now):
                    result.add_issue(ValidationIssue(
                        type=ISSUE_FUTURE_TIMESTAMP,
                        severity=SEVERITY_HIGH,
                        description=f"DateTimeDigitized '{exif.datetime_digitized}' is in the future (current time: {now}).",
                        field="exif.datetime_digitized",
                    ))

        # Check DateTime (modified)
        if exif.datetime_modified:
            dt = parse_exif_timestamp(exif.datetime_modified)
            if dt is None:
                result.add_issue(ValidationIssue(
                    type=ISSUE_INVALID_TIMESTAMP,
                    severity=SEVERITY_MEDIUM,
                    description=f"DateTimeModified value '{exif.datetime_modified}' could not be parsed as a valid timestamp.",
                    field="exif.datetime_modified",
                ))
            else:
                if is_impossible_date(dt):
                    result.add_issue(ValidationIssue(
                        type=ISSUE_IMPOSSIBLE_DATE,
                        severity=SEVERITY_HIGH,
                        description=f"DateTimeModified '{exif.datetime_modified}' represents an impossible date (year {dt.year}).",
                        field="exif.datetime_modified",
                    ))
                if is_future_timestamp(dt, now):
                    result.add_issue(ValidationIssue(
                        type=ISSUE_FUTURE_TIMESTAMP,
                        severity=SEVERITY_HIGH,
                        description=f"DateTimeModified '{exif.datetime_modified}' is in the future (current time: {now}).",
                        field="exif.datetime_modified",
                    ))

        # Check for timestamp mismatch (original vs digitized)
        if exif.datetime_original and exif.datetime_digitized:
            dt_orig = parse_exif_timestamp(exif.datetime_original)
            dt_dig = parse_exif_timestamp(exif.datetime_digitized)
            if dt_orig and dt_dig:
                # If they differ by more than 1 day, flag as mismatch
                delta = abs((dt_orig - dt_dig).total_seconds())
                if delta > 86400:  # 1 day in seconds
                    result.add_issue(ValidationIssue(
                        type=ISSUE_INVALID_TIMESTAMP,
                        severity=SEVERITY_MEDIUM,
                        description=(
                            f"DateTimeOriginal ('{exif.datetime_original}') and "
                            f"DateTimeDigitized ('{exif.datetime_digitized}') differ by "
                            f"{round(delta / 3600, 1)} hours, which may indicate timestamp manipulation."
                        ),
                        field="exif.datetime_original,exif.datetime_digitized",
                    ))

    def _check_gps(
        self,
        extraction: ExtractionResult,
        result: ValidationResult,
    ) -> None:
        """Validate GPS coordinates.

        :param extraction: Extraction result to validate.
        :param result: Validation result to append issues to.
        """
        gps = extraction.exif_data.gps

        if gps is None:
            # GPS is optional — only flag if we expected it (e.g., mobile camera)
            # We'll add a low-severity note that GPS is absent
            result.add_issue(ValidationIssue(
                type=ISSUE_INVALID_GPS,
                severity=SEVERITY_LOW,
                description="No GPS data found in the image.",
                field="exif.gps",
            ))
            return

        # Validate coordinates
        if gps.latitude is not None or gps.longitude is not None:
            if not validate_gps_coordinates(gps.latitude, gps.longitude):
                result.add_issue(ValidationIssue(
                    type=ISSUE_INVALID_GPS,
                    severity=SEVERITY_HIGH,
                    description=(
                        f"GPS coordinates are invalid: "
                        f"latitude={gps.latitude}, longitude={gps.longitude}. "
                        f"Values are outside valid ranges."
                    ),
                    field="exif.gps",
                ))

        # Check for partial GPS (latitude but no longitude, or vice versa)
        if gps.latitude is not None and gps.longitude is None:
            result.add_issue(ValidationIssue(
                type=ISSUE_INVALID_GPS,
                severity=SEVERITY_MEDIUM,
                description="GPS latitude is present but longitude is missing. GPS data may be incomplete.",
                field="exif.gps",
            ))
        elif gps.longitude is not None and gps.latitude is None:
            result.add_issue(ValidationIssue(
                type=ISSUE_INVALID_GPS,
                severity=SEVERITY_MEDIUM,
                description="GPS longitude is present but latitude is missing. GPS data may be incomplete.",
                field="exif.gps",
            ))

    def _check_duplicate_fields(
        self,
        extraction: ExtractionResult,
        result: ValidationResult,
    ) -> None:
        """Check for duplicate EXIF fields.

        :param extraction: Extraction result to validate.
        :param result: Validation result to append issues to.
        """
        raw_tags = extraction.exif_data.raw_tags

        if not raw_tags:
            return

        # Check for duplicate keys (case-insensitive)
        seen: dict[str, str] = {}
        duplicates: list[str] = []

        for key in raw_tags:
            lower_key = key.lower()
            if lower_key in seen:
                duplicates.append(key)
            else:
                seen[lower_key] = key

        if duplicates:
            result.add_issue(ValidationIssue(
                type=ISSUE_DUPLICATE_FIELD,
                severity=SEVERITY_MEDIUM,
                description=f"Duplicate EXIF fields detected (case-insensitive): {', '.join(duplicates)}.",
                field="exif",
            ))

    def _check_unsupported_metadata(
        self,
        extraction: ExtractionResult,
        result: ValidationResult,
    ) -> None:
        """Check for unsupported or unknown metadata fields.

        :param extraction: Extraction result to validate.
        :param result: Validation result to append issues to.
        """
        raw_tags = extraction.exif_data.raw_tags

        if not raw_tags:
            return

        # Check for tags that start with "Tag_" (unmapped)
        unmapped = [k for k in raw_tags if k.startswith("Tag_") or k.startswith("Exif_") or k.startswith("GPS_")]

        if unmapped:
            result.add_issue(ValidationIssue(
                type=ISSUE_UNSUPPORTED_METADATA,
                severity=SEVERITY_LOW,
                description=f"{len(unmapped)} EXIF tag(s) could not be mapped to known field names: {', '.join(unmapped[:10])}.",
                field="exif",
            ))
