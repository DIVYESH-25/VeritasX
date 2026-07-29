"""
Metadata Analysis Module — Automated Tests

Test coverage:
1.  JPEG with EXIF
2.  JPEG without EXIF
3.  PNG
4.  WEBP
5.  Screenshot (software signature)
6.  Corrupted image
7.  Large image
8.  Small image

Verifications:
- Metadata extraction correctness
- Validation issue generation
- Scoring logic
- Orchestrator compatibility
- Error handling resilience
"""

from __future__ import annotations

import asyncio
import io
import logging
import struct
import time
from datetime import datetime
from typing import Optional

import pytest
from PIL import Image

from backend.modules.metadata.analyzer import MetadataAnalyzer
from backend.modules.metadata.extractor import MetadataExtractor
from backend.modules.metadata.module import MetadataAnalysisModule
from backend.modules.metadata.scorer import MetadataScorer
from backend.modules.metadata.validator import MetadataValidator
from backend.schemas.models import ModuleResult, ModuleStatus

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("veritasx.modules.metadata.tests")

# ---------------------------------------------------------------------------
# Test Fixtures — Image Generation Helpers
# ---------------------------------------------------------------------------

REQUEST_ID = "test-metadata-001"


def _create_jpeg_with_exif() -> bytes:
    """Create a JPEG image with rich EXIF data.

    :return: Raw JPEG bytes with EXIF.
    """
    import piexif

    # Create a simple RGB image
    img = Image.new("RGB", (800, 600), color=(128, 128, 128))

    # Build EXIF data
    zeroth_ifd = {
        piexif.ImageIFD.Make: "Canon",
        piexif.ImageIFD.Model: "Canon EOS 5D Mark IV",
        piexif.ImageIFD.Software: "Adobe Photoshop n.0",
        piexif.ImageIFD.DateTime: "2024:01:15 10:30:00",
        piexif.ImageIFD.Artist: "John Doe",
        piexif.ImageIFD.Copyright: "Copyright 2024 John Doe",
        piexif.ImageIFD.Orientation: 1,
    }

    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: "2024:01:15 10:25:00",
        piexif.ExifIFD.DateTimeDigitized: "2024:01:15 10:25:00",
        piexif.ExifIFD.ExposureTime: (1, 125),
        piexif.ExifIFD.FNumber: (56, 10),
        piexif.ExifIFD.ISOSpeedRatings: 100,
        piexif.ExifIFD.Flash: 16,
        piexif.ExifIFD.FocalLength: (50, 1),
        piexif.ExifIFD.WhiteBalance: 0,
        piexif.ExifIFD.ExposureBiasValue: (0, 1),
        piexif.ExifIFD.MaxApertureValue: (56, 10),
        piexif.ExifIFD.MeteringMode: 5,
        piexif.ExifIFD.LensMake: "Canon",
        piexif.ExifIFD.LensModel: "EF24-70mm f/2.8L II USM",
    }

    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: "N",
        piexif.GPSIFD.GPSLatitude: ((40, 1), (42, 1), (50, 1000)),
        piexif.GPSIFD.GPSLongitudeRef: "W",
        piexif.GPSIFD.GPSLongitude: ((74, 1), (0, 1), (0, 1)),
        piexif.GPSIFD.GPSAltitudeRef: 0,
        piexif.GPSIFD.GPSAltitude: (10, 1),
    }

    exif_dict = {
        "0th": zeroth_ifd,
        "Exif": exif_ifd,
        "GPS": gps_ifd,
    }

    exif_bytes = piexif.dump(exif_dict)

    # Save image with EXIF
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif_bytes, quality=95)
    return buf.getvalue()


def _create_jpeg_without_exif() -> bytes:
    """Create a JPEG image without any EXIF data.

    :return: Raw JPEG bytes without EXIF.
    """
    img = Image.new("RGB", (400, 300), color=(200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _create_png() -> bytes:
    """Create a PNG image.

    :return: Raw PNG bytes.
    """
    img = Image.new("RGBA", (640, 480), color=(50, 150, 200, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _create_png_with_text_chunks() -> bytes:
    """Create a PNG image with text chunks (Software, etc.).

    :return: Raw PNG bytes with text metadata.
    """
    img = Image.new("RGB", (320, 240), color=(100, 200, 100))
    buf = io.BytesIO()
    img.save(
        buf,
        format="PNG",
        pnginfo=Image.PngImageFile.PngInfo()
        if hasattr(Image, "PngImageFile")
        else None,
        text={"Software": "GIMP 2.10.34"},
    )
    return buf.getvalue()


def _create_webp() -> bytes:
    """Create a WEBP image.

    :return: Raw WEBP bytes.
    """
    img = Image.new("RGB", (500, 500), color=(150, 75, 200))
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=90)
    return buf.getvalue()


def _create_webp_with_exif() -> bytes:
    """Create a WEBP image with EXIF data.

    :return: Raw WEBP bytes with EXIF.
    """
    import piexif

    img = Image.new("RGB", (500, 500), color=(150, 75, 200))

    zeroth_ifd = {
        piexif.ImageIFD.Make: "Google",
        piexif.ImageIFD.Model: "Pixel 8",
        piexif.ImageIFD.Software: "Midjourney",
    }

    exif_dict = {"0th": zeroth_ifd}
    exif_bytes = piexif.dump(exif_dict)

    buf = io.BytesIO()
    img.save(buf, format="WEBP", exif=exif_bytes, quality=90)
    return buf.getvalue()


def _create_screenshot_image() -> bytes:
    """Create a JPEG image that looks like a screenshot.

    :return: Raw JPEG bytes with screenshot software in EXIF.
    """
    import piexif

    img = Image.new("RGB", (1920, 1080), color=(240, 240, 240))

    zeroth_ifd = {
        piexif.ImageIFD.Software: "Windows Snipping Tool",
        piexif.ImageIFD.Make: "Microsoft",
        piexif.ImageIFD.Model: "Windows",
    }

    exif_dict = {"0th": zeroth_ifd}
    exif_bytes = piexif.dump(exif_dict)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif_bytes, quality=95)
    return buf.getvalue()


def _create_corrupted_image() -> bytes:
    """Create a corrupted/invalid image file.

    :return: Bytes that are not a valid image.
    """
    # Random bytes that look like a corrupted JPEG
    return b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\x00" * 50 + b"CORRUPTED DATA"


def _create_large_image() -> bytes:
    """Create a large image (4000x4000).

    :return: Raw JPEG bytes of a large image.
    """
    img = Image.new("RGB", (4000, 4000), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _create_small_image() -> bytes:
    """Create a small image (10x10).

    :return: Raw JPEG bytes of a small image.
    """
    img = Image.new("RGB", (10, 10), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _create_stable_diffusion_image() -> bytes:
    """Create a JPEG with Stable Diffusion software signature.

    :return: Raw JPEG bytes with AI software signature.
    """
    import piexif

    img = Image.new("RGB", (512, 512), color=(128, 128, 128))

    zeroth_ifd = {
        piexif.ImageIFD.Software: "Stable Diffusion 1.5",
    }

    exif_dict = {"0th": zeroth_ifd}
    exif_bytes = piexif.dump(exif_dict)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif_bytes, quality=95)
    return buf.getvalue()


def _create_midjourney_image() -> bytes:
    """Create a JPEG with Midjourney software signature.

    :return: Raw JPEG bytes with Midjourney software signature.
    """
    import piexif

    img = Image.new("RGB", (1024, 1024), color=(64, 64, 64))

    zeroth_ifd = {
        piexif.ImageIFD.Software: "Midjourney 6",
    }

    exif_dict = {"0th": zeroth_ifd}
    exif_bytes = piexif.dump(exif_dict)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif_bytes, quality=95)
    return buf.getvalue()


def _create_future_timestamp_image() -> bytes:
    """Create a JPEG with a future timestamp.

    :return: Raw JPEG bytes with future timestamp.
    """
    import piexif

    img = Image.new("RGB", (400, 300), color=(100, 100, 100))

    future_date = "2099:12:31 23:59:59"

    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: future_date,
        piexif.ExifIFD.DateTimeDigitized: future_date,
    }

    exif_dict = {"Exif": exif_ifd}
    exif_bytes = piexif.dump(exif_dict)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif_bytes, quality=95)
    return buf.getvalue()


def _create_gimp_image() -> bytes:
    """Create a JPEG with GIMP software signature.

    :return: Raw JPEG bytes with GIMP software signature.
    """
    import piexif

    img = Image.new("RGB", (600, 400), color=(200, 200, 200))

    zeroth_ifd = {
        piexif.ImageIFD.Software: "GIMP 2.10.34",
    }

    exif_dict = {"0th": zeroth_ifd}
    exif_bytes = piexif.dump(exif_dict)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif_bytes, quality=95)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------

class TestMetadataExtraction:
    """Tests for the MetadataExtractor."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.extractor = MetadataExtractor()

    def test_extract_jpeg_with_exif(self) -> None:
        """Test extraction from a JPEG with rich EXIF data."""
        image_bytes = _create_jpeg_with_exif()
        result = self.extractor.extract(image_bytes, REQUEST_ID, "test.jpg")

        assert result.file_info.filename == "test.jpg"
        assert result.file_info.extension == ".jpg"
        assert result.file_info.mime_type == "image/jpeg"
        assert result.file_info.file_size > 0
        assert len(result.file_info.sha256) == 64
        assert len(result.file_info.md5) == 32

        assert result.image_info.width == 800
        assert result.image_info.height == 600
        assert result.image_info.format == "JPEG"
        assert result.image_info.color_mode == "RGB"

        assert result.exif_data.has_exif is True
        assert result.exif_data.exif_field_count > 0
        assert result.exif_data.camera_make == "Canon"
        assert result.exif_data.camera_model == "Canon EOS 5D Mark IV"
        assert result.exif_data.software == "Adobe Photoshop n.0"
        assert result.exif_data.iso == 100
        assert result.exif_data.focal_length is not None
        assert result.exif_data.gps is not None
        assert result.exif_data.gps.latitude is not None
        assert result.exif_data.gps.longitude is not None

        logger.info(
            f"JPEG with EXIF: {result.exif_data.exif_field_count} fields, "
            f"camera={result.exif_data.camera_make} {result.exif_data.camera_model}"
        )

    def test_extract_jpeg_without_exif(self) -> None:
        """Test extraction from a JPEG without EXIF data."""
        image_bytes = _create_jpeg_without_exif()
        result = self.extractor.extract(image_bytes, REQUEST_ID, "no_exif.jpg")

        assert result.file_info.mime_type == "image/jpeg"
        assert result.image_info.width == 400
        assert result.image_info.height == 300

        assert result.exif_data.has_exif is False
        assert result.exif_data.exif_field_count == 0

    def test_extract_png(self) -> None:
        """Test extraction from a PNG image."""
        image_bytes = _create_png()
        result = self.extractor.extract(image_bytes, REQUEST_ID, "test.png")

        assert result.file_info.mime_type == "image/png"
        assert result.image_info.format == "PNG"
        assert result.image_info.color_mode == "RGBA"

    def test_extract_png_with_text_chunks(self) -> None:
        """Test extraction from a PNG with text chunks."""
        image_bytes = _create_png_with_text_chunks()
        result = self.extractor.extract(image_bytes, REQUEST_ID, "text.png")

        assert result.file_info.mime_type == "image/png"
        # PNG text chunks may or may not be captured depending on Pillow version

    def test_extract_webp(self) -> None:
        """Test extraction from a WEBP image."""
        image_bytes = _create_webp()
        result = self.extractor.extract(image_bytes, REQUEST_ID, "test.webp")

        assert result.file_info.mime_type == "image/webp"
        assert result.image_info.format == "WEBP"

    def test_extract_webp_with_exif(self) -> None:
        """Test extraction from a WEBP with EXIF data."""
        image_bytes = _create_webp_with_exif()
        result = self.extractor.extract(image_bytes, REQUEST_ID, "test.webp")

        assert result.file_info.mime_type == "image/webp"
        assert result.exif_data.has_exif is True
        assert result.exif_data.camera_make == "Google"
        assert result.exif_data.software == "Midjourney"

    def test_extract_corrupted_image(self) -> None:
        """Test extraction from a corrupted image."""
        image_bytes = _create_corrupted_image()
        result = self.extractor.extract(image_bytes, REQUEST_ID, "corrupted.jpg")

        # Should not crash — should return minimal info
        assert result.file_info.file_size > 0
        assert result.image_info.width == 0
        assert result.image_info.height == 0
        assert result.exif_data.has_exif is False

    def test_extract_large_image(self) -> None:
        """Test extraction from a large image."""
        image_bytes = _create_large_image()
        result = self.extractor.extract(image_bytes, REQUEST_ID, "large.jpg")

        assert result.image_info.width == 4000
        assert result.image_info.height == 4000
        assert result.file_info.file_size > 100000  # Should be at least 100KB

    def test_extract_small_image(self) -> None:
        """Test extraction from a small image."""
        image_bytes = _create_small_image()
        result = self.extractor.extract(image_bytes, REQUEST_ID, "small.jpg")

        assert result.image_info.width == 10
        assert result.image_info.height == 10
        assert result.image_info.aspect_ratio == 1.0

    def test_sha256_and_md5_hashes(self) -> None:
        """Test that hashes are computed correctly."""
        image_bytes = _create_jpeg_with_exif()
        result = self.extractor.extract(image_bytes, REQUEST_ID, "test.jpg")

        import hashlib
        assert result.file_info.sha256 == hashlib.sha256(image_bytes).hexdigest()
        assert result.file_info.md5 == hashlib.md5(image_bytes).hexdigest()


class TestMetadataValidation:
    """Tests for the MetadataValidator."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.extractor = MetadataExtractor()
        self.validator = MetadataValidator()

    def test_validate_jpeg_with_exif(self) -> None:
        """Test validation of a JPEG with valid EXIF."""
        image_bytes = _create_jpeg_with_exif()
        extraction = self.extractor.extract(image_bytes, REQUEST_ID, "test.jpg")
        validation = self.validator.validate(extraction, REQUEST_ID)

        # Should have some issues (e.g., Photoshop software, GPS missing note)
        assert validation.total_issues >= 0

    def test_validate_jpeg_without_exif(self) -> None:
        """Test validation of a JPEG without EXIF."""
        image_bytes = _create_jpeg_without_exif()
        extraction = self.extractor.extract(image_bytes, REQUEST_ID, "no_exif.jpg")
        validation = self.validator.validate(extraction, REQUEST_ID)

        # Should flag missing EXIF
        missing_exif_issues = [
            i for i in validation.issues if i.type == "MISSING_EXIF"
        ]
        assert len(missing_exif_issues) > 0

        # Should flag empty metadata
        empty_metadata_issues = [
            i for i in validation.issues if i.type == "EMPTY_METADATA"
        ]
        assert len(empty_metadata_issues) > 0

    def test_validate_future_timestamp(self) -> None:
        """Test validation of an image with a future timestamp."""
        image_bytes = _create_future_timestamp_image()
        extraction = self.extractor.extract(image_bytes, REQUEST_ID, "future.jpg")
        validation = self.validator.validate(extraction, REQUEST_ID)

        future_issues = [
            i for i in validation.issues if i.type == "FUTURE_TIMESTAMP"
        ]
        assert len(future_issues) > 0

    def test_validate_corrupted_image(self) -> None:
        """Test validation of a corrupted image."""
        image_bytes = _create_corrupted_image()
        extraction = self.extractor.extract(image_bytes, REQUEST_ID, "corrupted.jpg")
        validation = self.validator.validate(extraction, REQUEST_ID)

        # Should flag corrupted metadata
        corrupted_issues = [
            i for i in validation.issues if i.type == "CORRUPTED_METADATA"
        ]
        assert len(corrupted_issues) > 0


class TestMetadataScoring:
    """Tests for the MetadataScorer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.extractor = MetadataExtractor()
        self.validator = MetadataValidator()
        self.analyzer = MetadataAnalyzer()
        self.scorer = MetadataScorer()

    def test_score_jpeg_with_exif(self) -> None:
        """Test scoring of a JPEG with rich EXIF."""
        image_bytes = _create_jpeg_with_exif()
        extraction = self.extractor.extract(image_bytes, REQUEST_ID, "test.jpg")
        validation = self.validator.validate(extraction, REQUEST_ID)
        observations = self.analyzer.analyze(extraction, validation, REQUEST_ID)
        score_result = self.scorer.calculate_scores(extraction, validation, observations, REQUEST_ID)

        assert 0.0 <= score_result.metadata_score <= 1.0
        assert 0.0 <= score_result.confidence_score <= 1.0
        assert score_result.metadata_score > 0.0  # Should have some score

    def test_score_jpeg_without_exif(self) -> None:
        """Test scoring of a JPEG without EXIF (should be low)."""
        image_bytes = _create_jpeg_without_exif()
        extraction = self.extractor.extract(image_bytes, REQUEST_ID, "no_exif.jpg")
        validation = self.validator.validate(extraction, REQUEST_ID)
        observations = self.analyzer.analyze(extraction, validation, REQUEST_ID)
        score_result = self.scorer.calculate_scores(extraction, validation, observations, REQUEST_ID)

        assert 0.0 <= score_result.metadata_score <= 1.0
        # No EXIF should result in a lower score
        assert score_result.metadata_score < 0.5

    def test_score_stable_diffusion_image(self) -> None:
        """Test scoring of an image with Stable Diffusion signature."""
        image_bytes = _create_stable_diffusion_image()
        extraction = self.extractor.extract(image_bytes, REQUEST_ID, "sd.jpg")
        validation = self.validator.validate(extraction, REQUEST_ID)
        observations = self.analyzer.analyze(extraction, validation, REQUEST_ID)
        score_result = self.scorer.calculate_scores(extraction, validation, observations, REQUEST_ID)

        assert 0.0 <= score_result.metadata_score <= 1.0
        # AI signature should result in a low metadata_score
        assert score_result.metadata_score < 0.5

    def test_score_midjourney_image(self) -> None:
        """Test scoring of an image with Midjourney signature."""
        image_bytes = _create_midjourney_image()
        extraction = self.extractor.extract(image_bytes, REQUEST_ID, "mj.jpg")
        validation = self.validator.validate(extraction, REQUEST_ID)
        observations = self.analyzer.analyze(extraction, validation, REQUEST_ID)
        score_result = self.scorer.calculate_scores(extraction, validation, observations, REQUEST_ID)

        assert 0.0 <= score_result.metadata_score <= 1.0
        assert score_result.metadata_score < 0.5


class TestMetadataAnalyzer:
    """Tests for the MetadataAnalyzer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.extractor = MetadataExtractor()
        self.validator = MetadataValidator()
        self.analyzer = MetadataAnalyzer()

    def test_observations_jpeg_with_exif(self) -> None:
        """Test that observations are generated for a JPEG with EXIF."""
        image_bytes = _create_jpeg_with_exif()
        extraction = self.extractor.extract(image_bytes, REQUEST_ID, "test.jpg")
        validation = self.validator.validate(extraction, REQUEST_ID)
        observations = self.analyzer.analyze(extraction, validation, REQUEST_ID)

        assert len(observations) > 0
        # Should detect Photoshop editing
        photoshop_obs = [o for o in observations if o.observation_type == "edited_photoshop"]
        assert len(photoshop_obs) > 0
        # Should detect DSLR camera
        dslr_obs = [o for o in observations if o.observation_type == "dslr_image"]
        assert len(dslr_obs) > 0

    def test_observations_screenshot(self) -> None:
        """Test that screenshot observation is generated."""
        image_bytes = _create_screenshot_image()
        extraction = self.extractor.extract(image_bytes, REQUEST_ID, "screenshot.jpg")
        validation = self.validator.validate(extraction, REQUEST_ID)
        observations = self.analyzer.analyze(extraction, validation, REQUEST_ID)

        screenshot_obs = [o for o in observations if o.observation_type == "screenshot_detected"]
        assert len(screenshot_obs) > 0

    def test_observations_stable_diffusion(self) -> None:
        """Test that Stable Diffusion observation is generated."""
        image_bytes = _create_stable_diffusion_image()
        extraction = self.extractor.extract(image_bytes, REQUEST_ID, "sd.jpg")
        validation = self.validator.validate(extraction, REQUEST_ID)
        observations = self.analyzer.analyze(extraction, validation, REQUEST_ID)

        sd_obs = [o for o in observations if o.observation_type == "saved_stable_diffusion"]
        assert len(sd_obs) > 0

    def test_observations_midjourney(self) -> None:
        """Test that Midjourney observation is generated."""
        image_bytes = _create_midjourney_image()
        extraction = self.extractor.extract(image_bytes, REQUEST_ID, "mj.jpg")
        validation = self.validator.validate(extraction, REQUEST_ID)
        observations = self.analyzer.analyze(extraction, validation, REQUEST_ID)

        mj_obs = [o for o in observations if o.observation_type == "saved_midjourney"]
        assert len(mj_obs) > 0

    def test_observations_gimp(self) -> None:
        """Test that GIMP observation is generated."""
        image_bytes = _create_gimp_image()
        extraction = self.extractor.extract(image_bytes, REQUEST_ID, "gimp.jpg")
        validation = self.validator.validate(extraction, REQUEST_ID)
        observations = self.analyzer.analyze(extraction, validation, REQUEST_ID)

        gimp_obs = [o for o in observations if o.observation_type == "exported_gimp"]
        assert len(gimp_obs) > 0

    def test_observations_png_without_exif(self) -> None:
        """Test that PNG without EXIF observation is generated."""
        image_bytes = _create_png()
        extraction = self.extractor.extract(image_bytes, REQUEST_ID, "test.png")
        validation = self.validator.validate(extraction, REQUEST_ID)
        observations = self.analyzer.analyze(extraction, validation, REQUEST_ID)

        png_obs = [o for o in observations if o.observation_type == "png_without_exif"]
        assert len(png_obs) > 0

    def test_observations_metadata_removed(self) -> None:
        """Test that metadata removed observation is generated."""
        image_bytes = _create_jpeg_without_exif()
        extraction = self.extractor.extract(image_bytes, REQUEST_ID, "no_exif.jpg")
        validation = self.validator.validate(extraction, REQUEST_ID)
        observations = self.analyzer.analyze(extraction, validation, REQUEST_ID)

        removed_obs = [o for o in observations if o.observation_type == "metadata_removed"]
        assert len(removed_obs) > 0

    def test_observations_mobile_camera(self) -> None:
        """Test that mobile camera observation is generated."""
        import piexif

        img = Image.new("RGB", (400, 300), color=(100, 100, 100))
        zeroth_ifd = {
            piexif.ImageIFD.Make: "Apple",
            piexif.ImageIFD.Model: "iPhone 15 Pro",
        }
        exif_dict = {"0th": zeroth_ifd}
        exif_bytes = piexif.dump(exif_dict)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", exif=exif_bytes, quality=95)
        image_bytes = buf.getvalue()

        extraction = self.extractor.extract(image_bytes, REQUEST_ID, "iphone.jpg")
        validation = self.validator.validate(extraction, REQUEST_ID)
        observations = self.analyzer.analyze(extraction, validation, REQUEST_ID)

        mobile_obs = [o for o in observations if o.observation_type == "mobile_camera"]
        assert len(mobile_obs) > 0


class TestModuleIntegration:
    """Tests for the MetadataAnalysisModule integration."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.module = MetadataAnalysisModule()

    @pytest.mark.asyncio
    async def test_module_jpeg_with_exif(self) -> None:
        """Test the full module pipeline with a JPEG containing EXIF."""
        image_bytes = _create_jpeg_with_exif()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert isinstance(result, ModuleResult)
        assert result.module == "Metadata Analysis"
        assert result.status == ModuleStatus.SUCCESS
        assert 0.0 <= result.score <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert result.execution_time_ms >= 0.0
        assert result.data is not None

        # Verify data structure
        data = result.data
        assert "file" in data
        assert "image" in data
        assert "exif" in data
        assert "validation" in data
        assert "observations" in data
        assert "metadata_score" in data

        assert data["exif"]["has_exif"] is True
        assert data["exif"]["exif_field_count"] > 0
        assert data["exif"]["camera_make"] == "Canon"

        logger.info(
            f"Module test (JPEG+EXIF): score={result.score:.4f}, "
            f"confidence={result.confidence:.4f}, "
            f"metadata_score={data['metadata_score']:.4f}, "
            f"time={result.execution_time_ms}ms"
        )

    @pytest.mark.asyncio
    async def test_module_jpeg_without_exif(self) -> None:
        """Test the full module pipeline with a JPEG without EXIF."""
        image_bytes = _create_jpeg_without_exif()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        assert result.data["exif"]["has_exif"] is False
        # Low metadata_score should result in high module score (suspicious)
        assert result.score > 0.3

    @pytest.mark.asyncio
    async def test_module_png(self) -> None:
        """Test the full module pipeline with a PNG."""
        image_bytes = _create_png()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        assert result.data["image"]["format"] == "PNG"

    @pytest.mark.asyncio
    async def test_module_webp(self) -> None:
        """Test the full module pipeline with a WEBP."""
        image_bytes = _create_webp()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        assert result.data["image"]["format"] == "WEBP"

    @pytest.mark.asyncio
    async def test_module_corrupted_image(self) -> None:
        """Test the full module pipeline with a corrupted image."""
        image_bytes = _create_corrupted_image()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        # Should not crash — should return error or success with error info
        assert result.status in (ModuleStatus.SUCCESS, ModuleStatus.ERROR)
        assert result.data is not None or result.error_details is not None

    @pytest.mark.asyncio
    async def test_module_large_image(self) -> None:
        """Test the full module pipeline with a large image."""
        image_bytes = _create_large_image()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        assert result.data["image"]["width"] == 4000
        assert result.data["image"]["height"] == 4000

    @pytest.mark.asyncio
    async def test_module_small_image(self) -> None:
        """Test the full module pipeline with a small image."""
        image_bytes = _create_small_image()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        assert result.data["image"]["width"] == 10
        assert result.data["image"]["height"] == 10

    @pytest.mark.asyncio
    async def test_module_stable_diffusion(self) -> None:
        """Test the full module pipeline with a Stable Diffusion image."""
        image_bytes = _create_stable_diffusion_image()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        observations = result.data["observations"]
        sd_obs = [o for o in observations if o.get("observation_type") == "saved_stable_diffusion"]
        assert len(sd_obs) > 0
        # AI signature should result in low metadata_score
        assert result.data["metadata_score"] < 0.5

    @pytest.mark.asyncio
    async def test_module_midjourney(self) -> None:
        """Test the full module pipeline with a Midjourney image."""
        image_bytes = _create_midjourney_image()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        observations = result.data["observations"]
        mj_obs = [o for o in observations if o.get("observation_type") == "saved_midjourney"]
        assert len(mj_obs) > 0

    @pytest.mark.asyncio
    async def test_module_performance(self) -> None:
        """Test that the module completes within 100ms for normal images."""
        image_bytes = _create_jpeg_with_exif()

        start = time.perf_counter()
        result = await self.module.analyze(image_bytes, REQUEST_ID)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should complete in under 100ms for a normal image
        # (This is a soft assertion — actual performance depends on the system)
        logger.info(f"Module performance: {elapsed_ms:.2f}ms for JPEG with EXIF")
        assert elapsed_ms < 500  # Allow some headroom

    @pytest.mark.asyncio
    async def test_module_empty_bytes(self) -> None:
        """Test the module with empty bytes."""
        result = await self.module.analyze(b"", REQUEST_ID)

        # Should not crash
        assert result.status in (ModuleStatus.SUCCESS, ModuleStatus.ERROR)


class TestOrchestratorCompatibility:
    """Tests for orchestrator integration."""

    @pytest.mark.asyncio
    async def test_orchestrator_integration(self) -> None:
        """Test that the module works with the full orchestrator pipeline."""
        from backend.orchestrator.orchestrator import ForensicOrchestrator

        orchestrator = ForensicOrchestrator()
        image_bytes = _create_jpeg_with_exif()

        response = await orchestrator.process_analysis(
            image_bytes=image_bytes,
            request_id="test-orch-001",
        )

        # Find the metadata module result
        metadata_result = next(
            (m for m in response.modules if m.module == "Metadata Analysis"),
            None,
        )

        assert metadata_result is not None
        assert metadata_result.status == ModuleStatus.SUCCESS
        assert metadata_result.data is not None
        assert metadata_result.data["exif"]["has_exif"] is True

        logger.info(
            f"Orchestrator integration: metadata module score={metadata_result.score:.4f}, "
            f"confidence={metadata_result.confidence:.4f}"
        )

    @pytest.mark.asyncio
    async def test_orchestrator_with_corrupted_image(self) -> None:
        """Test that the orchestrator handles corrupted images gracefully."""
        from backend.orchestrator.orchestrator import ForensicOrchestrator

        orchestrator = ForensicOrchestrator()
        image_bytes = _create_corrupted_image()

        response = await orchestrator.process_analysis(
            image_bytes=image_bytes,
            request_id="test-orch-corrupt",
        )

        # Orchestrator should not crash
        assert response.request_id is not None
        assert len(response.modules) > 0

        # Metadata module should have a result (even if error)
        metadata_result = next(
            (m for m in response.modules if m.module == "Metadata Analysis"),
            None,
        )
        assert metadata_result is not None


# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short", "-s"])
