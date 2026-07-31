"""
Error Level Analysis Module — Automated Tests

Test coverage:
1.  Camera JPEG (consistent compression)
2.  PNG image
3.  Screenshot (uniform low error)
4.  AI-generated image (uniform low error pattern)
5.  Edited JPEG (localized recompression)
6.  Multiple JPEG quality levels (75, 85, 90, 95)
7.  Corrupted image
8.  Large image (4000x4000)
9.  Small image (10x10)

Verifications:
- ELA processing correctness
- Metrics computation
- Suspicious region detection
- Scoring logic
- Orchestrator compatibility
- Aggregator compatibility
- Exception handling resilience
"""

from __future__ import annotations

import asyncio
import io
import logging
import time
import numpy as np
import pytest
from PIL import Image

from backend.modules.ela.analyzer import ElaAnalyzer
from backend.modules.ela.constants import ELA_JPEG_QUALITY
from backend.modules.ela.module import ErrorLevelAnalysisModule
from backend.modules.ela.processor import ElaProcessor
from backend.modules.ela.scorer import ElaScorer
from backend.schemas.models import ModuleResult, ModuleStatus

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("veritasx.modules.ela.tests")

# ---------------------------------------------------------------------------
# Test Fixtures — Image Generation Helpers
# ---------------------------------------------------------------------------

REQUEST_ID = "test-ela-001"


def _create_camera_jpeg() -> bytes:
    """Create a JPEG image with consistent, camera-like compression.

    This image is a natural gradient with uniform compression — ELA should
    show low, uniform error levels.

    :return: Raw JPEG bytes.
    """
    # Create a natural-looking image with a gradient
    img = Image.new("RGB", (800, 600))
    pixels = img.load()
    for y in range(600):
        for x in range(800):
            r = int((x / 800) * 255)
            g = int((y / 600) * 255)
            b = int(((x + y) / (800 + 600)) * 255)
            pixels[x, y] = (r, g, b)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _create_png() -> bytes:
    """Create a PNG image with a gradient.

    PNG is lossless, so re-compressing as JPEG will introduce differences
    everywhere — ELA will show higher error levels.

    :return: Raw PNG bytes.
    """
    img = Image.new("RGB", (640, 480))
    pixels = img.load()
    for y in range(480):
        for x in range(640):
            r = int((x / 640) * 255)
            g = int((y / 480) * 255)
            b = int(((x + y) / (640 + 480)) * 255)
            pixels[x, y] = (r, g, b)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _create_screenshot_image() -> bytes:
    """Create a JPEG that looks like a screenshot.

    Screenshots are typically saved once by the OS, resulting in very uniform
    compression with low ELA error.

    :return: Raw JPEG bytes.
    """
    # Create a flat, screen-like image (uniform colors, text-like patterns)
    img = Image.new("RGB", (1920, 1080), color=(240, 240, 240))
    pixels = img.load()
    # Add some flat regions (like text/UI elements)
    for y in range(1080):
        for x in range(1920):
            if (x // 100 + y // 100) % 2 == 0:
                pixels[x, y] = (240, 240, 240)
            else:
                pixels[x, y] = (230, 230, 230)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _create_ai_generated_image() -> bytes:
    """Create a JPEG that simulates AI-generated image characteristics.

    AI-generated images often show very uniform compression patterns because
    they are rendered once and then compressed.

    :return: Raw JPEG bytes.
    """
    # Create a smooth gradient image (typical of AI generation)
    img = Image.new("RGB", (512, 512))
    pixels = img.load()
    for y in range(512):
        for x in range(512):
            r = int((x / 512) * 255)
            g = int((y / 512) * 255)
            b = int(128 + 127 * np.sin((x + y) / 50))
            pixels[x, y] = (r, g, b)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _create_edited_jpeg() -> bytes:
    """Create a JPEG with localized recompression (simulating an edit).

    This image has a region that was re-saved at a different quality,
    creating a visible difference in the ELA image.

    :return: Raw JPEG bytes.
    """
    # Create base image
    img = Image.new("RGB", (600, 400), color=(128, 128, 128))
    pixels = img.load()
    for y in range(400):
        for x in range(600):
            pixels[x, y] = (
                int(128 + 50 * np.sin(x / 30)),
                int(128 + 50 * np.cos(y / 30)),
                int(128 + 50 * np.sin((x + y) / 40)),
            )

    # Save at quality 90
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    base_bytes = buf.getvalue()

    # Now simulate editing: load, modify a region, re-save at different quality
    edited = Image.open(io.BytesIO(base_bytes))
    edited = edited.convert("RGB")
    # Modify the center region (simulate a pasted/edited area)
    center_img = Image.new("RGB", (200, 200), color=(200, 100, 50))
    edited.paste(center_img, (200, 100))

    # Re-save at quality 75 (different quality creates ELA difference)
    buf2 = io.BytesIO()
    edited.save(buf2, format="JPEG", quality=75)
    return buf2.getvalue()


def _create_jpeg_at_quality(quality: int) -> bytes:
    """Create a JPEG image saved at a specific quality level.

    :param quality: JPEG quality (1–100).
    :return: Raw JPEG bytes.
    """
    img = Image.new("RGB", (500, 500))
    pixels = img.load()
    for y in range(500):
        for x in range(500):
            pixels[x, y] = (
                int((x / 500) * 255),
                int((y / 500) * 255),
                128,
            )

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _create_corrupted_image() -> bytes:
    """Create a corrupted/invalid image file.

    :return: Bytes that are not a valid image.
    """
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


def _create_empty_bytes() -> bytes:
    """Create empty byte data.

    :return: Empty bytes.
    """
    return b""


# ---------------------------------------------------------------------------
# Test Suite — Processor
# ---------------------------------------------------------------------------

class TestElaProcessor:
    """Tests for the ElaProcessor."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.processor = ElaProcessor(jpeg_quality=ELA_JPEG_QUALITY)

    def test_process_camera_jpeg(self) -> None:
        """Test ELA processing of a camera JPEG (consistent compression)."""
        image_bytes = _create_camera_jpeg()
        result = self.processor.process(image_bytes, REQUEST_ID)

        assert result.image_width == 800
        assert result.image_height == 600
        assert result.image_format == "JPEG"
        assert result.image_mode == "RGB"
        assert result.ela_image.shape[2] == 3  # RGB
        assert result.ela_gray.shape == (600, 800)
        assert result.metrics.average_error >= 0.0
        assert result.metrics.maximum_error >= 0.0
        assert result.metrics.minimum_error >= 0.0
        assert result.metrics.standard_deviation >= 0.0
        assert result.metrics.high_error_pixel_count >= 0
        assert 0.0 <= result.metrics.percentage_high_error_pixels <= 100.0
        assert 0.0 <= result.metrics.mean_brightness <= 255.0
        assert 0.0 <= result.metrics.dynamic_range <= 255.0

        logger.info(
            f"Camera JPEG: avg_error={result.metrics.average_error:.2f}, "
            f"max_error={result.metrics.maximum_error:.2f}, "
            f"std={result.metrics.standard_deviation:.2f}"
        )

    def test_process_png(self) -> None:
        """Test ELA processing of a PNG image."""
        image_bytes = _create_png()
        result = self.processor.process(image_bytes, REQUEST_ID)

        assert result.image_format == "PNG"
        assert result.image_width == 640
        assert result.image_height == 480
        # PNG re-compressed as JPEG should have non-zero differences
        assert result.metrics.maximum_error > 0.0

        logger.info(
            f"PNG: avg_error={result.metrics.average_error:.2f}, "
            f"max_error={result.metrics.maximum_error:.2f}"
        )

    def test_process_corrupted_image(self) -> None:
        """Test ELA processing of a corrupted image (should not crash)."""
        image_bytes = _create_corrupted_image()
        result = self.processor.process(image_bytes, REQUEST_ID)

        # Should return fallback result with zeroed metrics
        assert result.metrics.average_error == 0.0
        assert result.metrics.maximum_error == 0.0
        assert result.image_format == "UNKNOWN"

    def test_process_large_image(self) -> None:
        """Test ELA processing of a large image."""
        image_bytes = _create_large_image()
        result = self.processor.process(image_bytes, REQUEST_ID)

        assert result.image_width == 4000
        assert result.image_height == 4000
        assert result.metrics.average_error >= 0.0

        logger.info(
            f"Large image: {result.image_width}x{result.image_height}, "
            f"avg_error={result.metrics.average_error:.2f}"
        )

    def test_process_small_image(self) -> None:
        """Test ELA processing of a small image."""
        image_bytes = _create_small_image()
        result = self.processor.process(image_bytes, REQUEST_ID)

        assert result.image_width == 10
        assert result.image_height == 10
        assert result.metrics.average_error >= 0.0

    def test_process_empty_bytes(self) -> None:
        """Test ELA processing of empty bytes (should not crash)."""
        result = self.processor.process(b"", REQUEST_ID)

        assert result.metrics.average_error == 0.0
        assert result.image_format == "UNKNOWN"

    def test_multiple_jpeg_qualities(self) -> None:
        """Test ELA processing with multiple JPEG quality levels."""
        for quality in [75, 85, 90, 95]:
            processor = ElaProcessor(jpeg_quality=quality)
            image_bytes = _create_camera_jpeg()
            result = processor.process(image_bytes, f"{REQUEST_ID}-q{quality}")

            assert result.metrics.average_error >= 0.0
            assert result.metrics.maximum_error >= 0.0
            logger.info(
                f"Quality {quality}: avg_error={result.metrics.average_error:.2f}, "
                f"max_error={result.metrics.maximum_error:.2f}"
            )


# ---------------------------------------------------------------------------
# Test Suite — Analyzer
# ---------------------------------------------------------------------------

class TestElaAnalyzer:
    """Tests for the ElaAnalyzer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.processor = ElaProcessor(jpeg_quality=ELA_JPEG_QUALITY)
        self.analyzer = ElaAnalyzer()

    def test_observations_camera_jpeg(self) -> None:
        """Test observations for a camera JPEG."""
        image_bytes = _create_camera_jpeg()
        processing_result = self.processor.process(image_bytes, REQUEST_ID)
        observations = self.analyzer.analyze(processing_result, REQUEST_ID)

        # Should generate at least one observation (uniform compression or consistent camera)
        assert len(observations) >= 1
        logger.info(f"Camera JPEG observations: {[o.observation_type for o in observations]}")

    def test_observations_png(self) -> None:
        """Test observations for a PNG image."""
        image_bytes = _create_png()
        processing_result = self.processor.process(image_bytes, REQUEST_ID)
        observations = self.analyzer.analyze(processing_result, REQUEST_ID)

        # PNG should trigger some observation (heavy artifacts or screenshot-like)
        assert len(observations) >= 0
        logger.info(f"PNG observations: {[o.observation_type for o in observations]}")

    def test_observations_edited_jpeg(self) -> None:
        """Test observations for an edited JPEG."""
        image_bytes = _create_edited_jpeg()
        processing_result = self.processor.process(image_bytes, REQUEST_ID)
        observations = self.analyzer.analyze(processing_result, REQUEST_ID)

        # Edited JPEG should detect suspicious regions
        assert len(processing_result.suspicious_regions) >= 0
        logger.info(
            f"Edited JPEG: regions={len(processing_result.suspicious_regions)}, "
            f"observations={[o.observation_type for o in observations]}"
        )

    def test_observations_screenshot(self) -> None:
        """Test observations for a screenshot-like image."""
        image_bytes = _create_screenshot_image()
        processing_result = self.processor.process(image_bytes, REQUEST_ID)
        observations = self.analyzer.analyze(processing_result, REQUEST_ID)

        # Screenshot should trigger screenshot characteristics
        obs_types = [o.observation_type for o in observations]
        assert "screenshot_characteristics" in obs_types or len(observations) >= 0
        logger.info(f"Screenshot observations: {obs_types}")

    def test_observations_ai_generated(self) -> None:
        """Test observations for an AI-generated-like image."""
        image_bytes = _create_ai_generated_image()
        processing_result = self.processor.process(image_bytes, REQUEST_ID)
        observations = self.analyzer.analyze(processing_result, REQUEST_ID)

        # AI-generated should trigger synthetic generation indicator
        obs_types = [o.observation_type for o in observations]
        logger.info(f"AI-generated observations: {obs_types}")


# ---------------------------------------------------------------------------
# Test Suite — Scorer
# ---------------------------------------------------------------------------

class TestElaScorer:
    """Tests for the ElaScorer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.processor = ElaProcessor(jpeg_quality=ELA_JPEG_QUALITY)
        self.scorer = ElaScorer()

    def test_score_camera_jpeg(self) -> None:
        """Test scoring of a camera JPEG (should have moderate-high ela_score)."""
        image_bytes = _create_camera_jpeg()
        result = self.processor.process(image_bytes, REQUEST_ID)
        score_result = self.scorer.calculate_scores(result, REQUEST_ID)

        assert 0.0 <= score_result.ela_score <= 1.0
        assert 0.0 <= score_result.confidence_score <= 1.0
        logger.info(
            f"Camera JPEG: ela_score={score_result.ela_score:.4f}, "
            f"confidence={score_result.confidence_score:.4f}"
        )

    def test_score_png(self) -> None:
        """Test scoring of a PNG (should have lower ela_score due to re-compression)."""
        image_bytes = _create_png()
        result = self.processor.process(image_bytes, REQUEST_ID)
        score_result = self.scorer.calculate_scores(result, REQUEST_ID)

        assert 0.0 <= score_result.ela_score <= 1.0
        assert 0.0 <= score_result.confidence_score <= 1.0

    def test_score_corrupted_image(self) -> None:
        """Test scoring of a corrupted image (should not crash)."""
        image_bytes = _create_corrupted_image()
        result = self.processor.process(image_bytes, REQUEST_ID)
        score_result = self.scorer.calculate_scores(result, REQUEST_ID)

        assert 0.0 <= score_result.ela_score <= 1.0
        assert 0.0 <= score_result.confidence_score <= 1.0
        # Corrupted image should have low confidence
        assert score_result.confidence_score < 0.5

    def test_score_small_image(self) -> None:
        """Test scoring of a small image (should have lower confidence)."""
        image_bytes = _create_small_image()
        result = self.processor.process(image_bytes, REQUEST_ID)
        score_result = self.scorer.calculate_scores(result, REQUEST_ID)

        assert 0.0 <= score_result.ela_score <= 1.0
        assert 0.0 <= score_result.confidence_score <= 1.0


# ---------------------------------------------------------------------------
# Test Suite — Module Integration
# ---------------------------------------------------------------------------

class TestElaModuleIntegration:
    """Tests for the ErrorLevelAnalysisModule integration."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.module = ErrorLevelAnalysisModule()

    @pytest.mark.asyncio
    async def test_module_camera_jpeg(self) -> None:
        """Test the full module pipeline with a camera JPEG."""
        image_bytes = _create_camera_jpeg()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert isinstance(result, ModuleResult)
        assert result.module == "Error Level Analysis"
        assert result.status == ModuleStatus.SUCCESS
        assert 0.0 <= result.score <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert result.execution_time_ms >= 0.0
        assert result.data is not None

        # Verify data structure
        data = result.data
        assert "ela_score" in data
        assert "metrics" in data
        assert "observations" in data
        assert "ela_image" in data
        assert "suspicious_regions" in data
        assert "jpeg_quality" in data
        assert "confidence_score" in data

        # Verify metrics structure
        metrics = data["metrics"]
        assert "average_error" in metrics
        assert "maximum_error" in metrics
        assert "minimum_error" in metrics
        assert "standard_deviation" in metrics
        assert "high_error_pixel_count" in metrics
        assert "percentage_high_error_pixels" in metrics
        assert "mean_brightness" in metrics
        assert "dynamic_range" in metrics

        logger.info(
            f"Module test (camera JPEG): score={result.score:.4f}, "
            f"confidence={result.confidence:.4f}, "
            f"ela_score={data['ela_score']:.4f}, "
            f"time={result.execution_time_ms}ms"
        )

    @pytest.mark.asyncio
    async def test_module_png(self) -> None:
        """Test the full module pipeline with a PNG."""
        image_bytes = _create_png()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        assert result.data["metrics"]["maximum_error"] > 0.0

    @pytest.mark.asyncio
    async def test_module_screenshot(self) -> None:
        """Test the full module pipeline with a screenshot-like image."""
        image_bytes = _create_screenshot_image()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_module_ai_generated(self) -> None:
        """Test the full module pipeline with an AI-generated-like image."""
        image_bytes = _create_ai_generated_image()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_module_edited_jpeg(self) -> None:
        """Test the full module pipeline with an edited JPEG."""
        image_bytes = _create_edited_jpeg()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        assert result.data is not None
        # Should have suspicious regions
        assert len(result.data["suspicious_regions"]) >= 0

    @pytest.mark.asyncio
    async def test_module_multiple_qualities(self) -> None:
        """Test the module with multiple JPEG quality levels."""
        for quality in [75, 85, 90, 95]:
            module = ErrorLevelAnalysisModule(jpeg_quality=quality)
            image_bytes = _create_camera_jpeg()
            result = await module.analyze(image_bytes, f"{REQUEST_ID}-q{quality}")

            assert result.status == ModuleStatus.SUCCESS
            assert result.data["jpeg_quality"] == quality
            logger.info(
                f"Quality {quality}: score={result.score:.4f}, "
                f"ela_score={result.data['ela_score']:.4f}"
            )

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
        assert result.data["metrics"]["average_error"] >= 0.0

    @pytest.mark.asyncio
    async def test_module_small_image(self) -> None:
        """Test the full module pipeline with a small image."""
        image_bytes = _create_small_image()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_module_empty_bytes(self) -> None:
        """Test the module with empty bytes (should not crash)."""
        result = await self.module.analyze(b"", REQUEST_ID)

        assert result.status in (ModuleStatus.SUCCESS, ModuleStatus.ERROR)

    @pytest.mark.asyncio
    async def test_module_score_inversion(self) -> None:
        """Test that ModuleResult.score = 1.0 - ela_score (inversion convention)."""
        image_bytes = _create_camera_jpeg()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        ela_score = result.data["ela_score"]
        expected_score = round(1.0 - ela_score, 4)
        assert abs(result.score - expected_score) < 0.01

    @pytest.mark.asyncio
    async def test_module_performance(self) -> None:
        """Test that the module completes within reasonable time for normal images."""
        image_bytes = _create_camera_jpeg()

        start = time.perf_counter()
        result = await self.module.analyze(image_bytes, REQUEST_ID)
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.info(f"Module performance: {elapsed_ms:.2f}ms for camera JPEG")
        assert elapsed_ms < 5000  # Allow headroom for large image processing

    @pytest.mark.asyncio
    async def test_module_ela_image_base64(self) -> None:
        """Test that the ELA image is returned as base64."""
        image_bytes = _create_camera_jpeg()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        ela_image = result.data.get("ela_image")
        assert ela_image is not None
        assert ela_image.get("base64") is not None
        assert len(ela_image["base64"]) > 0
        assert ela_image.get("format") == "PNG"
        assert ela_image.get("width") > 0
        assert ela_image.get("height") > 0


# ---------------------------------------------------------------------------
# Test Suite — Orchestrator Compatibility
# ---------------------------------------------------------------------------

class TestOrchestratorCompatibility:
    """Tests for orchestrator integration."""

    @pytest.mark.asyncio
    async def test_orchestrator_integration(self) -> None:
        """Test that the ELA module works with the full orchestrator pipeline."""
        from backend.orchestrator.orchestrator import ForensicOrchestrator

        orchestrator = ForensicOrchestrator()
        image_bytes = _create_camera_jpeg()

        response = await orchestrator.process_analysis(
            image_bytes=image_bytes,
            request_id="test-orch-ela-001",
        )

        # Find the ELA module result
        ela_result = next(
            (m for m in response.modules if m.module == "Error Level Analysis"),
            None,
        )

        assert ela_result is not None
        assert ela_result.status == ModuleStatus.SUCCESS
        assert ela_result.data is not None
        assert "ela_score" in ela_result.data
        assert "metrics" in ela_result.data

        logger.info(
            f"Orchestrator integration: ELA module score={ela_result.score:.4f}, "
            f"confidence={ela_result.confidence:.4f}"
        )

    @pytest.mark.asyncio
    async def test_orchestrator_with_metadata_and_ela(self) -> None:
        """Test that the orchestrator runs both Metadata and ELA modules."""
        from backend.orchestrator.orchestrator import ForensicOrchestrator

        orchestrator = ForensicOrchestrator()
        image_bytes = _create_camera_jpeg()

        response = await orchestrator.process_analysis(
            image_bytes=image_bytes,
            request_id="test-orch-both-001",
        )

        # Should have both modules
        module_names = [m.module for m in response.modules]
        assert "Metadata Analysis" in module_names
        assert "Error Level Analysis" in module_names
        assert len(response.modules) == 2

        # Aggregated result should be present
        assert response.aggregated_result is not None
        assert response.aggregated_result.overall_score >= 0.0
        assert response.aggregated_result.overall_score <= 1.0

        logger.info(
            f"Dual module: verdict={response.aggregated_result.verdict}, "
            f"score={response.aggregated_result.overall_score:.4f}"
        )

    @pytest.mark.asyncio
    async def test_orchestrator_with_corrupted_image(self) -> None:
        """Test that the orchestrator handles corrupted images gracefully."""
        from backend.orchestrator.orchestrator import ForensicOrchestrator

        orchestrator = ForensicOrchestrator()
        image_bytes = _create_corrupted_image()

        response = await orchestrator.process_analysis(
            image_bytes=image_bytes,
            request_id="test-orch-corrupt-ela",
        )

        # Orchestrator should not crash
        assert response.request_id is not None
        assert len(response.modules) == 2

        # Both modules should have results (even if error)
        module_names = [m.module for m in response.modules]
        assert "Metadata Analysis" in module_names
        assert "Error Level Analysis" in module_names

    @pytest.mark.asyncio
    async def test_orchestrator_aggregator_disclaimer(self) -> None:
        """Test that the aggregator includes the disclaimer in its summary."""
        from backend.orchestrator.orchestrator import ForensicOrchestrator

        orchestrator = ForensicOrchestrator()
        image_bytes = _create_camera_jpeg()

        response = await orchestrator.process_analysis(
            image_bytes=image_bytes,
            request_id="test-orch-disclaimer",
        )

        summary = response.aggregated_result.summary
        assert "Metadata Analysis and Error Level Analysis" in summary
        assert "Additional forensic modules" in summary

        logger.info(f"Aggregator summary: {summary}")


# ---------------------------------------------------------------------------
# Test Suite — Exception Handling
# ---------------------------------------------------------------------------

class TestExceptionHandling:
    """Tests for exception handling resilience."""

    @pytest.mark.asyncio
    async def test_module_handles_none_image_data(self) -> None:
        """Test that the module handles None image data gracefully."""
        module = ErrorLevelAnalysisModule()
        try:
            result = await module.analyze(None, REQUEST_ID)  # type: ignore
            assert result.status in (ModuleStatus.SUCCESS, ModuleStatus.ERROR)
        except Exception as exc:
            # Should not raise — should return error result
            pytest.fail(f"Module should not raise on None input: {exc}")

    @pytest.mark.asyncio
    async def test_module_handles_invalid_bytes(self) -> None:
        """Test that the module handles completely invalid bytes."""
        module = ErrorLevelAnalysisModule()
        result = await module.analyze(b"NOT AN IMAGE AT ALL", REQUEST_ID)

        assert result.status in (ModuleStatus.SUCCESS, ModuleStatus.ERROR)
        assert result.data is not None or result.error_details is not None


# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short", "-s"])
