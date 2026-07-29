"""
Metadata Analysis Module — Extraction Layer

The ``MetadataExtractor`` is responsible for extracting all available metadata
from raw image bytes using Pillow, piexif, and exifread.  It produces a
structured ``ExtractionResult`` that downstream layers (validator, analyzer,
scorer) consume.

Design notes
------------
* The image is opened **once** via Pillow to minimise memory usage and
  decoding overhead.
* EXIF data is extracted from raw bytes via piexif (fast, structured) with
  exifread as a fallback for edge cases.
* PNG text chunks and WEBP EXIF are also captured.
* All extraction failures are caught and reported gracefully — the module
  never crashes.
"""

from __future__ import annotations

import io
import logging
import time
from typing import Any, Dict, Optional

from PIL import Image, UnidentifiedImageError

from backend.modules.metadata.constants import (
    EXIF_0TH_TAG_MAP,
    EXIF_EXIF_TAG_MAP,
    EXIF_GPS_TAG_MAP,
    EXTENSION_TO_MIME,
    FLASH_VALUES,
    ORIENTATION_VALUES,
    WHITE_BALANCE_VALUES,
)
from backend.modules.metadata.models import (
    ExifData,
    ExtractionResult,
    FileInfo,
    GpsInfo,
    ImageInfo,
)
from backend.modules.metadata.utils import (
    bytes_to_stream,
    calculate_aspect_ratio,
    compute_md5,
    compute_sha256,
    detect_mime_type,
    safe_float,
    safe_int,
    safe_serialize_value,
    safe_str,
)

logger = logging.getLogger("veritasx.modules.metadata.extractor")


class MetadataExtractor:
    """Extracts file, image, and EXIF metadata from raw image bytes.

    This class is stateless and safe to reuse across requests.
    """

    def __init__(self) -> None:
        """Initialise the extractor."""
        # Track whether piexif is available
        self._piexif_available: bool = self._check_piexif()
        self._exifread_available: bool = self._check_exifread()

    # ------------------------------------------------------------------
    # Dependency checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_piexif() -> bool:
        """Check if piexif is importable."""
        try:
            import piexif  # noqa: F401
            return True
        except ImportError:
            logger.warning("piexif is not installed — EXIF extraction will be limited.")
            return False

    @staticmethod
    def _check_exifread() -> bool:
        """Check if exifread is importable."""
        try:
            import exifread  # noqa: F401
            return True
        except ImportError:
            logger.warning("exifread is not installed — EXIF fallback extraction will be unavailable.")
            return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(
        self,
        image_bytes: bytes,
        request_id: str,
        filename: str = "unknown",
    ) -> ExtractionResult:
        """Extract all metadata from *image_bytes*.

        :param image_bytes: Raw image bytes.
        :param request_id: Request ID for tracing.
        :param filename: Original filename (for extension/MIME detection).
        :return: ``ExtractionResult`` containing file info, image info, and EXIF data.
        """
        start = time.perf_counter()
        logger.info(f"[{request_id}] Starting metadata extraction for '{filename}' ({len(image_bytes)} bytes)")

        # 1. File information
        file_info = self._extract_file_info(image_bytes, filename)

        # 2. Image information (opens image once via Pillow)
        image_info, pil_image, raw_exif_bytes = self._extract_image_info(
            image_bytes, file_info.mime_type, request_id
        )

        # 3. EXIF data
        exif_data, raw_exif_data = self._extract_exif(
            image_bytes, raw_exif_bytes, pil_image, file_info.mime_type, request_id
        )

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            f"[{request_id}] Extraction complete in {elapsed_ms}ms | "
            f"EXIF fields: {exif_data.exif_field_count} | "
            f"Has EXIF: {exif_data.has_exif}"
        )

        return ExtractionResult(
            file_info=file_info,
            image_info=image_info,
            exif_data=exif_data,
            raw_exif_data=raw_exif_data,
        )

    # ------------------------------------------------------------------
    # File Information
    # ------------------------------------------------------------------

    def _extract_file_info(self, image_bytes: bytes, filename: str) -> FileInfo:
        """Build a ``FileInfo`` object from raw bytes.

        :param image_bytes: Raw image bytes.
        :param filename: Original filename.
        :return: Populated ``FileInfo``.
        """
        mime_type = detect_mime_type(image_bytes, filename)
        extension = self._get_extension(filename, mime_type)

        return FileInfo(
            filename=filename,
            extension=extension,
            mime_type=mime_type,
            file_size=len(image_bytes),
            sha256=compute_sha256(image_bytes),
            md5=compute_md5(image_bytes),
        )

    @staticmethod
    def _get_extension(filename: str, mime_type: str) -> str:
        """Determine the file extension from filename or MIME type.

        :param filename: Original filename.
        :param mime_type: Detected MIME type.
        :return: Extension including the dot (e.g. ``.jpg``).
        """
        import os

        _, ext = os.path.splitext(filename)
        if ext:
            return ext.lower()
        # Fallback: infer from MIME type
        for ext, mime in EXTENSION_TO_MIME.items():
            if mime == mime_type:
                return ext
        return ".bin"

    # ------------------------------------------------------------------
    # Image Information
    # ------------------------------------------------------------------

    def _extract_image_info(
        self,
        image_bytes: bytes,
        mime_type: str,
        request_id: str,
    ) -> tuple[ImageInfo, Optional[Image.Image], bytes]:
        """Extract image-level information using Pillow.

        Opens the image **once** and extracts all available properties.

        :param image_bytes: Raw image bytes.
        :param mime_type: Detected MIME type.
        :param request_id: Request ID for tracing.
        :return: Tuple of (ImageInfo, PIL Image, raw EXIF bytes).
        """
        stream = bytes_to_stream(image_bytes)
        pil_image: Optional[Image.Image] = None
        raw_exif_bytes: bytes = b""

        try:
            pil_image = Image.open(stream)
            pil_image.load()  # Force full decode to populate all properties
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            logger.warning(f"[{request_id}] Pillow could not open image: {exc}")
            # Return minimal info for corrupted/unrecognised images
            return self._minimal_image_info(mime_type), None, b""
        except Exception as exc:
            logger.error(f"[{request_id}] Unexpected error opening image with Pillow: {exc}", exc_info=True)
            return self._minimal_image_info(mime_type), None, b""

        # Extract properties
        width, height = pil_image.size
        aspect_ratio = calculate_aspect_ratio(width, height)
        color_mode = pil_image.mode
        img_format = pil_image.format or "UNKNOWN"

        # Bit depth
        bit_depth = self._get_bit_depth(pil_image)

        # Compression type
        compression = self._get_compression(pil_image)

        # DPI
        dpi = self._get_dpi(pil_image)

        # Color profile
        color_profile = self._get_color_profile(pil_image)

        # Raw EXIF bytes (for piexif extraction)
        if hasattr(pil_image, "_getexif") and pil_image._getexif():
            try:
                raw_exif_bytes = pil_image.info.get("exif", b"")
            except Exception:
                raw_exif_bytes = b""

        # Also check img.info for exif
        if not raw_exif_bytes:
            raw_exif_bytes = pil_image.info.get("exif", b"")

        image_info = ImageInfo(
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            color_mode=color_mode,
            color_profile=color_profile,
            bit_depth=bit_depth,
            compression_type=compression,
            dpi=dpi,
            format=img_format,
        )

        return image_info, pil_image, raw_exif_bytes

    @staticmethod
    def _minimal_image_info(mime_type: str) -> ImageInfo:
        """Create a minimal ``ImageInfo`` for images that cannot be opened.

        :param mime_type: Detected MIME type.
        :return: ``ImageInfo`` with zeroed/default values.
        """
        return ImageInfo(
            width=0,
            height=0,
            aspect_ratio=0.0,
            color_mode="unknown",
            color_profile=None,
            bit_depth=None,
            compression_type=None,
            dpi=None,
            format="UNKNOWN",
        )

    @staticmethod
    def _get_bit_depth(img: Image.Image) -> Optional[int]:
        """Determine the bit depth of the image.

        :param img: Pillow image object.
        :return: Bit depth per channel, or ``None`` if undeterminable.
        """
        # PNG has explicit bit depth
        if hasattr(img, "bits") and img.bits:
            return img.bits

        # Infer from mode
        mode_bit_depths = {
            "1": 1,
            "L": 8,
            "P": 8,
            "RGB": 8,
            "RGBA": 8,
            "CMYK": 8,
            "YCbCr": 8,
            "LAB": 8,
            "HSV": 8,
            "I": 16,
            "F": 32,
            "I;16": 16,
        }
        return mode_bit_depths.get(img.mode)

    @staticmethod
    def _get_compression(img: Image.Image) -> Optional[str]:
        """Get the compression type from a Pillow image.

        :param img: Pillow image object.
        :return: Compression type string or ``None``.
        """
        if hasattr(img, "compression") and img.compression:
            return img.compression
        # Check info dict
        return img.info.get("compression")

    @staticmethod
    def _get_dpi(img: Image.Image) -> Optional[tuple[float, float]]:
        """Get DPI from a Pillow image.

        :param img: Pillow image object.
        :return: (x_dpi, y_dpi) tuple or ``None``.
        """
        dpi = img.info.get("dpi")
        if dpi and isinstance(dpi, (tuple, list)) and len(dpi) == 2:
            try:
                return (float(dpi[0]), float(dpi[1]))
            except (ValueError, TypeError):
                return None
        return None

    @staticmethod
    def _get_color_profile(img: Image.Image) -> Optional[str]:
        """Get the ICC color profile description.

        :param img: Pillow image object.
        :return: Profile description or ``None``.
        """
        icc_profile = img.info.get("icc_profile")
        if icc_profile:
            # Try to get the profile description
            try:
                from PIL import ImageCms

                profile = ImageCms.ImageCmsProfile(icc_profile)
                if profile.profile.profile_description:
                    return profile.profile.profile_description
                return "ICC Profile (description unavailable)"
            except Exception:
                return "ICC Profile"
        return None

    # ------------------------------------------------------------------
    # EXIF Extraction
    # ------------------------------------------------------------------

    def _extract_exif(
        self,
        image_bytes: bytes,
        raw_exif_bytes: bytes,
        pil_image: Optional[Image.Image],
        mime_type: str,
        request_id: str,
    ) -> tuple[ExifData, Dict[str, Any]]:
        """Extract EXIF data using piexif (primary) and exifread (fallback).

        :param image_bytes: Raw image bytes.
        :param raw_exif_bytes: Raw EXIF bytes extracted from Pillow.
        :param pil_image: Pillow image object (for PNG text chunks).
        :param mime_type: Detected MIME type.
        :param request_id: Request ID for tracing.
        :return: Tuple of (ExifData, raw_exif_dict).
        """
        # Attempt 1: piexif on raw bytes (works for JPEG and WEBP)
        if self._piexif_available:
            try:
                import piexif

                exif_dict = piexif.load(image_bytes)
                if exif_dict:
                    exif_data, raw_exif = self._parse_piexif_dict(exif_dict, request_id)
                    if exif_data.has_exif and exif_data.exif_field_count > 0:
                        return exif_data, raw_exif
            except (piexif.InvalidImageDataError, ValueError, TypeError) as exc:
                logger.debug(f"[{request_id}] piexif extraction failed: {exc}")
            except Exception as exc:
                logger.debug(f"[{request_id}] piexif unexpected error: {exc}")

        # Attempt 2: exifread fallback
        if self._exifread_available:
            try:
                exif_data, raw_exif = self._extract_with_exifread(image_bytes, request_id)
                if exif_data.has_exif and exif_data.exif_field_count > 0:
                    return exif_data, raw_exif
            except Exception as exc:
                logger.debug(f"[{request_id}] exifread extraction failed: {exc}")

        # Attempt 3: Pillow's _getexif (JPEG fallback)
        if pil_image is not None:
            try:
                pillow_exif = pil_image._getexif()
                if pillow_exif:
                    exif_data, raw_exif = self._parse_pillow_exif(pillow_exif, request_id)
                    if exif_data.has_exif and exif_data.exif_field_count > 0:
                        return exif_data, raw_exif
            except Exception as exc:
                logger.debug(f"[{request_id}] Pillow _getexif failed: {exc}")

        # Attempt 4: PNG text chunks
        if pil_image is not None and pil_image.format == "PNG":
            try:
                exif_data, raw_exif = self._extract_png_text_chunks(pil_image, request_id)
                return exif_data, raw_exif
            except Exception as exc:
                logger.debug(f"[{request_id}] PNG text chunk extraction failed: {exc}")

        # No EXIF found
        logger.info(f"[{request_id}] No EXIF data found in image.")
        return ExifData(has_exif=False, exif_field_count=0), {}

    # ------------------------------------------------------------------
    # piexif Parsing
    # ------------------------------------------------------------------

    def _parse_piexif_dict(
        self,
        exif_dict: Dict[str, Any],
        request_id: str,
    ) -> tuple[ExifData, Dict[str, Any]]:
        """Parse a piexif EXIF dictionary into structured ``ExifData``.

        :param exif_dict: Dictionary returned by ``piexif.load()``.
        :param request_id: Request ID for tracing.
        :return: Tuple of (ExifData, raw_exif_dict).
        """
        raw_tags: Dict[str, Any] = {}
        field_count = 0

        # 0th IFD (image-level tags)
        zeroth = exif_dict.get("0th", {})
        for tag_id, value in zeroth.items():
            tag_name = EXIF_0TH_TAG_MAP.get(tag_id, f"Tag_{tag_id}")
            raw_tags[tag_name] = safe_serialize_value(value)
            field_count += 1

        # Exif IFD (camera settings)
        exif_ifd = exif_dict.get("Exif", {})
        for tag_id, value in exif_ifd.items():
            tag_name = EXIF_EXIF_TAG_MAP.get(tag_id, f"Exif_{tag_id}")
            raw_tags[tag_name] = safe_serialize_value(value)
            field_count += 1

        # GPS IFD
        gps_ifd = exif_dict.get("GPS", {})
        for tag_id, value in gps_ifd.items():
            tag_name = EXIF_GPS_TAG_MAP.get(tag_id, f"GPS_{tag_id}")
            raw_tags[tag_name] = safe_serialize_value(value)
            field_count += 1

        # Build ExifData from raw tags
        exif_data = self._build_exif_data(raw_tags, field_count, request_id)

        # Include raw piexif dict for forensic inspection
        raw_exif = {
            "0th": {str(k): safe_serialize_value(v) for k, v in zeroth.items()},
            "Exif": {str(k): safe_serialize_value(v) for k, v in exif_ifd.items()},
            "GPS": {str(k): safe_serialize_value(v) for k, v in gps_ifd.items()},
            "1st": {str(k): safe_serialize_value(v) for k, v in exif_dict.get("1st", {}).items()},
            "Interop": {str(k): safe_serialize_value(v) for k, v in exif_dict.get("Interop", {}).items()},
        }

        return exif_data, raw_exif

    def _build_exif_data(
        self,
        raw_tags: Dict[str, Any],
        field_count: int,
        request_id: str,
    ) -> ExifData:
        """Build a structured ``ExifData`` object from raw tag name/value pairs.

        :param raw_tags: Dictionary of tag_name → value.
        :param field_count: Total number of fields.
        :param request_id: Request ID for tracing.
        :return: Populated ``ExifData``.
        """
        # Camera information
        camera_make = safe_str(raw_tags.get("Make"))
        camera_model = safe_str(raw_tags.get("Model"))
        lens_model = safe_str(raw_tags.get("LensModel"))
        lens_make = safe_str(raw_tags.get("LensMake"))

        # Software
        software = safe_str(raw_tags.get("Software"))
        artist = safe_str(raw_tags.get("Artist"))
        copyright_info = safe_str(raw_tags.get("Copyright"))

        # Timestamps
        datetime_original = safe_str(raw_tags.get("DateTimeOriginal"))
        datetime_digitized = safe_str(raw_tags.get("DateTimeDigitized"))
        datetime_modified = safe_str(raw_tags.get("DateTime"))

        # Exposure / camera settings
        exposure_time = safe_str(raw_tags.get("ExposureTime"))
        aperture = safe_str(raw_tags.get("FNumber"))
        iso = safe_int(raw_tags.get("ISOSpeedRatings"))
        flash_value = safe_int(raw_tags.get("Flash"))
        flash = FLASH_VALUES.get(flash_value) if flash_value is not None else safe_str(raw_tags.get("Flash"))
        focal_length = safe_str(raw_tags.get("FocalLength"))
        white_balance_value = safe_int(raw_tags.get("WhiteBalance"))
        white_balance = (
            WHITE_BALANCE_VALUES.get(white_balance_value)
            if white_balance_value is not None
            else safe_str(raw_tags.get("WhiteBalance"))
        )
        orientation_value = safe_int(raw_tags.get("Orientation"))
        orientation = (
            ORIENTATION_VALUES.get(orientation_value)
            if orientation_value is not None
            else safe_str(raw_tags.get("Orientation"))
        )
        exposure_program = safe_str(raw_tags.get("ExposureProgram"))
        metering_mode = safe_str(raw_tags.get("MeteringMode"))
        light_source = safe_str(raw_tags.get("LightSource"))
        exposure_bias = safe_str(raw_tags.get("ExposureBiasValue"))
        max_aperture = safe_str(raw_tags.get("MaxApertureValue"))
        subject_distance = safe_str(raw_tags.get("SubjectDistance"))
        image_description = safe_str(raw_tags.get("ImageDescription"))

        # GPS
        gps_info = self._build_gps_info(raw_tags, request_id)

        return ExifData(
            camera_make=camera_make,
            camera_model=camera_model,
            lens=lens_model,
            lens_make=lens_make,
            software=software,
            artist=artist,
            copyright=copyright_info,
            datetime_original=datetime_original,
            datetime_digitized=datetime_digitized,
            datetime_modified=datetime_modified,
            exposure_time=exposure_time,
            aperture=aperture,
            iso=iso,
            flash=flash,
            focal_length=focal_length,
            white_balance=white_balance,
            orientation=orientation,
            exposure_program=exposure_program,
            metering_mode=metering_mode,
            light_source=light_source,
            exposure_bias=exposure_bias,
            max_aperture=max_aperture,
            subject_distance=subject_distance,
            image_description=image_description,
            gps=gps_info,
            has_exif=True,
            exif_field_count=field_count,
            raw_tags=raw_tags,
        )

    def _build_gps_info(
        self,
        raw_tags: Dict[str, Any],
        request_id: str,
    ) -> Optional[GpsInfo]:
        """Build a ``GpsInfo`` object from raw GPS tag values.

        :param raw_tags: Dictionary of tag_name → value.
        :param request_id: Request ID for tracing.
        :return: ``GpsInfo`` if any GPS data is present, else ``None``.
        """
        from backend.modules.metadata.utils import convert_dms_to_decimal

        lat_ref = safe_str(raw_tags.get("GPSLatitudeRef"))
        lon_ref = safe_str(raw_tags.get("GPSLongitudeRef"))
        lat_dms = raw_tags.get("GPSLatitude")
        lon_dms = raw_tags.get("GPSLongitude")
        altitude = safe_float(raw_tags.get("GPSAltitude"))
        altitude_ref = safe_str(raw_tags.get("GPSAltitudeRef"))
        gps_timestamp = safe_str(raw_tags.get("GPSTimeStamp"))
        gps_date = safe_str(raw_tags.get("GPSDate"))

        latitude = convert_dms_to_decimal(lat_dms, lat_ref) if lat_dms else None
        longitude = convert_dms_to_decimal(lon_dms, lon_ref) if lon_dms else None

        # Check if any GPS data exists
        has_gps = any([
            latitude is not None,
            longitude is not None,
            altitude is not None,
            gps_timestamp is not None,
        ])

        if not has_gps:
            return None

        # Altitude reference
        altitude_ref_str = None
        if altitude_ref is not None:
            altitude_ref_str = "Below sea level" if altitude_ref == 1 else "Above sea level"

        # GPS timestamp
        gps_ts_str = None
        if gps_timestamp:
            gps_ts_str = str(gps_timestamp)
        if gps_date:
            gps_ts_str = f"{gps_date} {gps_ts_str}" if gps_ts_str else gps_date

        # Raw GPS tags
        raw_gps = {
            k: str(v) for k, v in raw_tags.items() if k.startswith("GPS")
        }

        return GpsInfo(
            latitude=latitude,
            latitude_ref=lat_ref,
            longitude=longitude,
            longitude_ref=lon_ref,
            altitude=altitude,
            altitude_ref=altitude_ref_str,
            timestamp=gps_ts_str,
            raw=raw_gps,
        )

    # ------------------------------------------------------------------
    # exifread Fallback
    # ------------------------------------------------------------------

    def _extract_with_exifread(
        self,
        image_bytes: bytes,
        request_id: str,
    ) -> tuple[ExifData, Dict[str, Any]]:
        """Extract EXIF data using the exifread library as a fallback.

        :param image_bytes: Raw image bytes.
        :param request_id: Request ID for tracing.
        :return: Tuple of (ExifData, raw_exif_dict).
        """
        import exifread

        stream = bytes_to_stream(image_bytes)
        tags = exifread.process_file(stream, details=False, strict=True)

        if not tags:
            return ExifData(has_exif=False, exif_field_count=0), {}

        # Convert exifread tags to our raw_tags format
        raw_tags: Dict[str, Any] = {}
        for tag_name, value in tags.items():
            # exifread tag names look like "EXIF DateTimeOriginal", "GPS GPSLatitude", etc.
            clean_name = tag_name
            if tag_name.startswith("EXIF "):
                clean_name = tag_name[5:]
            elif tag_name.startswith("GPS "):
                clean_name = tag_name[4:]
            elif tag_name.startswith("Image "):
                clean_name = tag_name[6:]
            elif tag_name.startswith("TIFF "):
                clean_name = tag_name[5:]

            raw_tags[clean_name] = safe_serialize_value(value)

        field_count = len(raw_tags)
        exif_data = self._build_exif_data(raw_tags, field_count, request_id)

        raw_exif = {k: safe_serialize_value(v) for k, v in raw_tags.items()}

        return exif_data, raw_exif

    # ------------------------------------------------------------------
    # Pillow _getexif Fallback
    # ------------------------------------------------------------------

    def _parse_pillow_exif(
        self,
        pillow_exif: Dict[int, Any],
        request_id: str,
    ) -> tuple[ExifData, Dict[str, Any]]:
        """Parse EXIF data from Pillow's ``_getexif()`` output.

        :param pillow_exif: Dictionary of tag_id → value from Pillow.
        :param request_id: Request ID for tracing.
        :return: Tuple of (ExifData, raw_exif_dict).
        """
        from PIL.ExifTags import TAGS

        raw_tags: Dict[str, Any] = {}
        for tag_id, value in pillow_exif.items():
            tag_name = TAGS.get(tag_id, f"Tag_{tag_id}")
            raw_tags[tag_name] = safe_serialize_value(value)

        field_count = len(raw_tags)
        exif_data = self._build_exif_data(raw_tags, field_count, request_id)

        raw_exif = {k: safe_serialize_value(v) for k, v in raw_tags.items()}

        return exif_data, raw_exif

    # ------------------------------------------------------------------
    # PNG Text Chunks
    # ------------------------------------------------------------------

    def _extract_png_text_chunks(
        self,
        pil_image: Image.Image,
        request_id: str,
    ) -> tuple[ExifData, Dict[str, Any]]:
        """Extract text chunks from a PNG image.

        PNG images may contain text chunks (tEXt, iTXt, zTXt) with metadata
        like Software, Description, etc.

        :param pil_image: Pillow PNG image object.
        :param request_id: Request ID for tracing.
        :return: Tuple of (ExifData, raw_exif_dict).
        """
        raw_tags: Dict[str, Any] = {}

        # Pillow stores PNG text chunks in img.info
        for key, value in pil_image.info.items():
            if key.lower() in ("software", "description", "comment", "author", "copyright", "date:create", "date:modify"):
                clean_val = safe_serialize_value(value)
                raw_tags[key] = clean_val
                # Map to standard EXIF field names
                if key.lower() == "software":
                    raw_tags["Software"] = clean_val
                elif key.lower() == "author":
                    raw_tags["Artist"] = clean_val
                elif key.lower() == "copyright":
                    raw_tags["Copyright"] = clean_val
                elif key.lower() == "date:create":
                    raw_tags["DateTimeOriginal"] = clean_val
                elif key.lower() == "date:modify":
                    raw_tags["DateTime"] = clean_val

        # Also check for eXIf chunk (PNG 1.2)
        png_exif = pil_image.info.get("exif")
        if png_exif and isinstance(png_exif, bytes) and len(png_exif) > 0:
            try:
                import piexif

                exif_dict = piexif.load(png_exif)
                for section in ("0th", "Exif", "GPS"):
                    for tag_id, value in exif_dict.get(section, {}).items():
                        tag_name = EXIF_0TH_TAG_MAP.get(tag_id) or EXIF_EXIF_TAG_MAP.get(tag_id) or EXIF_GPS_TAG_MAP.get(tag_id) or f"Tag_{tag_id}"
                        raw_tags[tag_name] = safe_serialize_value(value)

            except Exception as exc:
                logger.debug(f"[{request_id}] PNG eXIf chunk parsing failed: {exc}")

        if not raw_tags:
            return ExifData(has_exif=False, exif_field_count=0), {}

        field_count = len(raw_tags)
        exif_data = self._build_exif_data(raw_tags, field_count, request_id)

        raw_exif = {k: str(v) for k, v in raw_tags.items()}

        return exif_data, raw_exif
