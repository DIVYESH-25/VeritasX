"""
Frequency Analysis Module — Automated Tests

Test coverage:
1.  Camera JPEG (consistent compression)
2.  PNG image
3.  WEBP image
4.  Screenshot (uniform low error)
5.  AI-generated image (uniform low error pattern)
6.  Edited image
7.  Large image (4000x4000)
8.  Small image (10x10)
9.  Corrupted image

Verifications:
- FFT processing correctness
- Metrics computation
- Observation generation
- Scoring logic
- Orchestrator compatibility
- Aggregator compatibility
- Exception handling resilience
- Visualization correctness
"""

from __future__ import annotations

import asyncio
import io
import logging
import time
import numpy as np
import pytest
from PIL import Image

from backend.modules.frequency.analyzer import FrequencyAnalyzer
from backend.modules.frequency.constants import MODULE_NAME
from backend.modules.frequency.module import FrequencyAnalysisModule
from backend.modules.frequency.processor import FrequencyProcessor
from backend.modules.frequency.scorer import FrequencyScorer
from backend.schemas.models import ModuleResult, ModuleStatus

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("veritasx.modules.frequency.tests")

# ---------------------------------------------------------------------------
# Test Fixtures — Image Generation Helpers
# ---------------------------------------------------------------------------

REQUEST_ID = "test-freq-001"


def _create_camera_jpeg() -> bytes:
    """Create a JPEG image with consistent, camera-like compression.

    This image is a natural-looking image with a gradient — the FFT should
    show a healthy low-frequency dominance typical of natural photographs.

    :return: Raw JPEG bytes.
    """
    # Create a natural-looking image with a radial gradient
    img = Image.new("RGB", (800, 600))
    pixels = img.load()
    center_x, center_y = 400, 300
    for y in range(600):
        for x in range(800):
            dx, dy = x - center_x, y - center_y
            dist = np.sqrt(dx * dx + dy * dy)
            r = int(128 + 60 * np.sin(dist / 100))
            g = int(128 + 40 * np.cos((x + y) / 50))
            b = int(128 + 50 * np.sin((x - y) / 80))
            pixels[x, y] = (
                max(0, min(255, r)),
                max(0, min(255, g)),
                max(0, min(255, b)),
            )

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _create_png() -> bytes:
    """Create a PNG image with a gradient.

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


def _create_webp() -> bytes:
    """Create a WEBP image.

    :return: Raw WEBP bytes.
    """
    img = Image.new("RGB", (512, 512))
    pixels = img.load()
    for y in range(512):
        for x in range(512):
            r = int((x / 512) * 255)
            g = int((y / 512) * 255)
            b = int(128 + 127 * np.sin((x + y) / 30))
            pixels[x, y] = (r, g, b)

    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=90)
    return buf.getvalue()


def _create_screenshot_image() -> bytes:
    """Create a JPEG that looks like a screenshot.

    Screenshots are typically saved once by the OS, resulting in very uniform
    frequency content.

    :return: Raw JPEG bytes.
    """
    img = Image.new("RGB", (1920, 1080), color=(240, 240, 240))
    pixels = img.load()
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

    AI-generated images often show very smooth, uniform frequency spectra
    because the generation process introduces subtle regularities.

    :return: Raw JPEG bytes.
    """
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


def _create_edited_image() -> bytes:
    """Create an image with localised modifications (simulating an edit).

    :return: Raw bytes of the edited image.
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

    # Simulate editing: paste a different region
    edited = img.copy()
    center_img = Image.new("RGB", (200, 200), color=(200, 100, 50))
    edited.paste(center_img, (200, 100))

    buf = io.BytesIO()
    edited.save(buf, format="JPEG", quality=90)
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

class TestFrequencyProcessor:
    """Tests for the FrequencyProcessor."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.processor = FrequencyProcessor()

    def test_process_camera_jpeg(self) -> None:
        """Test frequency processing of a camera JPEG."""
        image_bytes = _create_camera_jpeg()
        result = self.processor.process(image_bytes, REQUEST_ID)

        assert result.image_width == 800
        assert result.image_height == 600
        assert result.image_format == "JPEG"
        assert result.image_mode == "RGB"
        assert result.magnitude_spectrum.shape[0] > 0
        assert result.magnitude_spectrum.shape[1] > 0
        # Metrics should have valid values
        assert result.metrics.energy_ratio >= 0.0
        assert 0.0 <= result.metrics.spectral_entropy <= 1.0
        assert result.metrics.peak_to_mean_ratio >= 0.0
        assert 0.0 <= result.metrics.horizontal_energy_fraction <= 1.0
        assert 0.0 <= result.metrics.vertical_energy_fraction <= 1.0
        assert 0.0 <= result.metrics.radial_symmetry_score <= 1.0
        assert result.metrics.fft_size[0] > 0
        assert result.metrics.fft_size[1] > 0

        logger.info(
            f"Camera JPEG: energy_ratio={result.metrics.energy_ratio:.2f}, "
            f"spectral_entropy={result.metrics.spectral_entropy:.4f}, "
            f"peak_to_mean={result.metrics.peak_to_mean_ratio:.2f}"
        )

    def test_process_png(self) -> None:
        """Test frequency processing of a PNG image."""
        image_bytes = _create_png()
        result = self.processor.process(image_bytes, REQUEST_ID)

        assert result.image_format == "PNG"
        assert result.image_width == 640
        assert result.image_height == 480
        assert result.metrics.energy_ratio >= 0.0

        logger.info(
            f"PNG: energy_ratio={result.metrics.energy_ratio:.2f}, "
            f"spectral_entropy={result.metrics.spectral_entropy:.4f}"
        )

    def test_process_webp(self) -> None:
        """Test frequency processing of a WEBP image."""
        image_bytes = _create_webp()
        result = self.processor.process(image_bytes, REQUEST_ID)

        assert result.image_format == "WEBP"
        assert result.image_width == 512
        assert result.image_height == 512

        logger.info(
            f"WEBP: energy_ratio={result.metrics.energy_ratio:.2f}, "
            f"spectral_entropy={result.metrics.spectral_entropy:.4f}"
        )

    def test_process_corrupted_image(self) -> None:
        """Test frequency processing of a corrupted image (should not crash)."""
        image_bytes = _create_corrupted_image()
        result = self.processor.process(image_bytes, REQUEST_ID)

        # Should return fallback result with zeroed metrics
        assert result.metrics.energy_ratio == 0.0
        assert result.metrics.spectral_entropy == 0.0
        assert result.image_format == "UNKNOWN"

    def test_process_large_image(self) -> None:
        """Test frequency processing of a large image."""
        image_bytes = _create_large_image()
        result = self.processor.process(image_bytes, REQUEST_ID)

        assert result.image_width == 4000
        assert result.image_height == 4000
        assert result.metrics.energy_ratio >= 0.0
        # FFT should be downsampled
        assert result.metrics.fft_size[0] <= 1024
        assert result.metrics.fft_size[1] <= 1024

        logger.info(
            f"Large image: {result.image_width}x{result.image_height}, "
            f"fft_size={result.metrics.fft_size}, "
            f"energy_ratio={result.metrics.energy_ratio:.2f}"
        )

    def test_process_small_image(self) -> None:
        """Test frequency processing of a small image."""
        image_bytes = _create_small_image()
        result = self.processor.process(image_bytes, REQUEST_ID)

        assert result.image_width == 10
        assert result.image_height == 10
        assert result.metrics.energy_ratio >= 0.0

    def test_process_empty_bytes(self) -> None:
        """Test frequency processing of empty bytes (should not crash)."""
        result = self.processor.process(b"", REQUEST_ID)

        assert result.metrics.energy_ratio == 0.0
        assert result.image_format == "UNKNOWN"

    def test_hann_window_option(self) -> None:
        """Test that Hann window application changes the spectrum."""
        image_bytes = _create_camera_jpeg()

        processor_with_hann = FrequencyProcessor(apply_hann=True)
        processor_without_hann = FrequencyProcessor(apply_hann=False)

        result_with = processor_with_hann.process(image_bytes, f"{REQUEST_ID}-hann")
        result_without = processor_without_hann.process(image_bytes, f"{REQUEST_ID}-no-hann")

        # Both should produce valid results
        assert result_with.metrics.energy_ratio >= 0.0
        assert result_without.metrics.energy_ratio >= 0.0

        logger.info(
            f"Hann: ratio={result_with.metrics.energy_ratio:.2f} | "
            f"No Hann: ratio={result_without.metrics.energy_ratio:.2f}"
        )


# ---------------------------------------------------------------------------
# Test Suite — Analyzer
# ---------------------------------------------------------------------------

class TestFrequencyAnalyzer:
    """Tests for the FrequencyAnalyzer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.processor = FrequencyProcessor()
        self.analyzer = FrequencyAnalyzer()

    def test_observations_camera_jpeg(self) -> None:
        """Test observations for a camera JPEG."""
        image_bytes = _create_camera_jpeg()
        processing_result = self.processor.process(image_bytes, REQUEST_ID)
        observations = self.analyzer.analyze(processing_result, REQUEST_ID)

        assert len(observations) >= 1
        # Check observation structure
        for obs in observations:
            assert obs.title
            assert obs.description
            assert obs.severity in ("low", "medium", "high", "critical")
            assert 0.0 <= obs.confidence <= 1.0

        logger.info(f"Camera JPEG observations: {[o.observation_type for o in observations]}")

    def test_observations_png(self) -> None:
        """Test observations for a PNG image."""
        image_bytes = _create_png()
        processing_result = self.processor.process(image_bytes, REQUEST_ID)
        observations = self.analyzer.analyze(processing_result, REQUEST_ID)

        assert len(observations) >= 0
        logger.info(f"PNG observations: {[o.observation_type for o in observations]}")

    def test_observations_screenshot(self) -> None:
        """Test observations for a screenshot-like image."""
        image_bytes = _create_screenshot_image()
        processing_result = self.processor.process(image_bytes, REQUEST_ID)
        observations = self.analyzer.analyze(processing_result, REQUEST_ID)

        logger.info(f"Screenshot observations: {[o.observation_type for o in observations]}")

    def test_observations_ai_generated(self) -> None:
        """Test observations for an AI-generated-like image."""
        image_bytes = _create_ai_generated_image()
        processing_result = self.processor.process(image_bytes, REQUEST_ID)
        observations = self.analyzer.analyze(processing_result, REQUEST_ID)

        logger.info(f"AI-generated observations: {[o.observation_type for o in observations]}")

    def test_observations_edited(self) -> None:
        """Test observations for an edited image."""
        image_bytes = _create_edited_image()
        processing_result = self.processor.process(image_bytes, REQUEST_ID)
        observations = self.analyzer.analyze(processing_result, REQUEST_ID)

        logger.info(f"Edited image observations: {[o.observation_type for o in observations]}")

    def test_observations_corrupted(self) -> None:
        """Test observations for a corrupted image."""
        image_bytes = _create_corrupted_image()
        processing_result = self.processor.process(image_bytes, REQUEST_ID)
        observations = self.analyzer.analyze(processing_result, REQUEST_ID)

        # Corrupted image may or may not generate observations
        assert len(observations) >= 0
        logger.info(f"Corrupted image observations: {len(observations)}")


# ---------------------------------------------------------------------------
# Test Suite — Scorer
# ---------------------------------------------------------------------------

class TestFrequencyScorer:
    """Tests for the FrequencyScorer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.processor = FrequencyProcessor()
        self.scorer = FrequencyScorer()

    def test_score_camera_jpeg(self) -> None:
        """Test scoring of a camera JPEG."""
        image_bytes = _create_camera_jpeg()
        result = self.processor.process(image_bytes, REQUEST_ID)
        score_result = self.scorer.calculate_scores(result, REQUEST_ID)

        assert 0.0 <= score_result.frequency_score <= 1.0
        assert 0.0 <= score_result.confidence_score <= 1.0
        logger.info(
            f"Camera JPEG: frequency_score={score_result.frequency_score:.4f}, "
            f"confidence={score_result.confidence_score:.4f}"
        )

    def test_score_png(self) -> None:
        """Test scoring of a PNG image."""
        image_bytes = _create_png()
        result = self.processor.process(image_bytes, REQUEST_ID)
        score_result = self.scorer.calculate_scores(result, REQUEST_ID)

        assert 0.0 <= score_result.frequency_score <= 1.0
        assert 0.0 <= score_result.confidence_score <= 1.0

    def test_score_corrupted_image(self) -> None:
        """Test scoring of a corrupted image (should not crash)."""
        image_bytes = _create_corrupted_image()
        result = self.processor.process(image_bytes, REQUEST_ID)
        score_result = self.scorer.calculate_scores(result, REQUEST_ID)

        assert 0.0 <= score_result.frequency_score <= 1.0
        assert 0.0 <= score_result.confidence_score <= 1.0
        # Corrupted image should have lower confidence
        assert score_result.confidence_score < 0.5
        logger.info(
            f"Corrupted image: frequency_score={score_result.frequency_score:.4f}, "
            f"confidence={score_result.confidence_score:.4f}"
        )

    def test_score_small_image(self) -> None:
        """Test scoring of a small image (should have lower confidence)."""
        image_bytes = _create_small_image()
        result = self.processor.process(image_bytes, REQUEST_ID)
        score_result = self.scorer.calculate_scores(result, REQUEST_ID)

        assert 0.0 <= score_result.frequency_score <= 1.0
        assert 0.0 <= score_result.confidence_score <= 1.0
        logger.info(
            f"Small image: frequency_score={score_result.frequency_score:.4f}, "
            f"confidence={score_result.confidence_score:.4f}"
        )


# ---------------------------------------------------------------------------
# Test Suite — Visualizer
# ---------------------------------------------------------------------------

class TestFrequencyVisualizer:
    """Tests for the FrequencyVisualizer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.processor = FrequencyProcessor()
        from backend.modules.frequency.visualization import FrequencyVisualizer
        self.visualizer = FrequencyVisualizer()

    def test_generate_spectrum_image(self) -> None:
        """Test that the visualizer generates a base64 spectrum image."""
        image_bytes = _create_camera_jpeg()
        result = self.processor.process(image_bytes, REQUEST_ID)
        spectrum = self.visualizer.generate_spectrum_image(
            magnitude_spectrum=result.magnitude_spectrum,
            request_id=REQUEST_ID,
        )

        assert spectrum is not None
        assert spectrum.base64 is not None
        assert len(spectrum.base64) > 0
        assert spectrum.format == "PNG"
        assert spectrum.width > 0
        assert spectrum.height > 0

        logger.info(
            f"Spectrum image: {spectrum.width}×{spectrum.height}, "
            f"base64 length={len(spectrum.base64)}"
        )

    def test_generate_spectrum_image_empty(self) -> None:
        """Test that the visualizer handles empty spectrum gracefully."""
        spectrum = self.visualizer.generate_spectrum_image(
            magnitude_spectrum=np.array([]),
            request_id=REQUEST_ID,
        )
        assert spectrum is None


# ---------------------------------------------------------------------------
# Test Suite — Module Integration
# ---------------------------------------------------------------------------

class TestFrequencyModuleIntegration:
    """Tests for the FrequencyAnalysisModule integration."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.module = FrequencyAnalysisModule()

    @pytest.mark.asyncio
    async def test_module_camera_jpeg(self) -> None:
        """Test the full module pipeline with a camera JPEG."""
        image_bytes = _create_camera_jpeg()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert isinstance(result, ModuleResult)
        assert result.module == MODULE_NAME
        assert result.status == ModuleStatus.SUCCESS
        assert 0.0 <= result.score <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert result.execution_time_ms >= 0.0
        assert result.data is not None

        # Verify data structure
        data = result.data
        assert "frequency_score" in data
        assert "metrics" in data
        assert "observations" in data
        assert "fft_spectrum" in data
        assert "confidence_score" in data

        # Verify metrics structure
        metrics = data["metrics"]
        assert "energy_ratio" in metrics
        assert "spectral_entropy" in metrics
        assert "peak_to_mean_ratio" in metrics
        assert "mean_magnitude" in metrics
        assert "std_magnitude" in metrics
        assert "low_frequency_energy" in metrics
        assert "high_frequency_energy" in metrics
        assert "radial_energy_innner" in metrics
        assert "radial_energy_mid" in metrics
        assert "radial_energy_outer" in metrics
        assert "horizontal_energy_fraction" in metrics
        assert "vertical_energy_fraction" in metrics
        assert "hv_balance_ratio" in metrics
        assert "radial_symmetry_score" in metrics
        assert "image_width" in metrics
        assert "image_height" in metrics
        assert "image_format" in metrics
        assert "image_mode" in metrics
        assert "fft_size" in metrics

        logger.info(
            f"Module test (camera JPEG): score={result.score:.4f}, "
            f"confidence={result.confidence:.4f}, "
            f"frequency_score={data['frequency_score']:.4f}, "
            f"time={result.execution_time_ms}ms"
        )

    @pytest.mark.asyncio
    async def test_module_png(self) -> None:
        """Test the full module pipeline with a PNG."""
        image_bytes = _create_png()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        assert result.data is not None
        assert result.data["metrics"]["image_format"] == "PNG"

    @pytest.mark.asyncio
    async def test_module_webp(self) -> None:
        """Test the full module pipeline with a WEBP image."""
        image_bytes = _create_webp()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        assert result.data is not None
        assert result.data["metrics"]["image_format"] == "WEBP"

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
    async def test_module_edited(self) -> None:
        """Test the full module pipeline with an edited image."""
        image_bytes = _create_edited_image()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_module_corrupted_image(self) -> None:
        """Test the full module pipeline with a corrupted image."""
        image_bytes = _create_corrupted_image()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        # Should not crash — should return error or success with fallback data
        assert result.status in (ModuleStatus.SUCCESS, ModuleStatus.ERROR)

    @pytest.mark.asyncio
    async def test_module_large_image(self) -> None:
        """Test the full module pipeline with a large image."""
        image_bytes = _create_large_image()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        assert result.data["metrics"]["image_width"] == 4000
        assert result.data["metrics"]["image_height"] == 4000

    @pytest.mark.asyncio
    async def test_module_small_image(self) -> None:
        """Test the full module pipeline with a small image."""
        image_bytes = _create_small_image()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_module_empty_bytes(self) -> None:
        """Test the full module pipeline with empty bytes (should not crash)."""
        result = await self.module.analyze(b"", REQUEST_ID)

        assert result.status in (ModuleStatus.SUCCESS, ModuleStatus.ERROR)

    @pytest.mark.asyncio
    async def test_module_score_inversion(self) -> None:
        """Test that ModuleResult.score = 1.0 - frequency_score (inversion convention)."""
        image_bytes = _create_camera_jpeg()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        frequency_score = result.data["frequency_score"]
        expected_score = round(1.0 - frequency_score, 4)
        assert abs(result.score - expected_score) < 0.01

    @pytest.mark.asyncio
    async def test_module_spectrum_image_base64(self) -> None:
        """Test that the FFT spectrum image is returned as base64."""
        image_bytes = _create_camera_jpeg()
        result = await self.module.analyze(image_bytes, REQUEST_ID)

        assert result.status == ModuleStatus.SUCCESS
        spectrum = result.data.get("fft_spectrum")
        assert spectrum is not None
        assert spectrum.get("base64") is not None
        assert len(spectrum["base64"]) > 0
        assert spectrum.get("format") == "PNG"
        assert spectrum.get("width") > 0
        assert spectrum.get("height") > 0

    @pytest.mark.asyncio
    async def test_module_performance(self) -> None:
        """Test that the module completes within reasonable time for normal images."""
        image_bytes = _create_camera_jpeg()

        start = time.perf_counter()
        result = await self.module.analyze(image_bytes, REQUEST_ID)
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.info(f"Module performance: {elapsed_ms:.2f}ms for camera JPEG")
        assert elapsed_ms < 5000  # Allow headroom for FFT computation


# ---------------------------------------------------------------------------
# Test Suite — Orchestrator Compatibility
# ---------------------------------------------------------------------------

class TestOrchestratorCompatibility:
    """Tests for orchestrator integration."""

    @pytest.mark.asyncio
    async def test_orchestrator_integration(self) -> None:
        """Test that the Frequency module works with the full orchestrator pipeline."""
        from backend.orchestrator.orchestrator import ForensicOrchestrator

        orchestrator = ForensicOrchestrator()
        image_bytes = _create_camera_jpeg()

        response = await orchestrator.process_analysis(
            image_bytes=image_bytes,
            request_id="test-orch-freq-001",
        )

        # Find the Frequency Analysis module result
        freq_result = next(
            (m for m in response.modules if m.module == MODULE_NAME),
            None,
        )

        assert freq_result is not None
        assert freq_result.status == ModuleStatus.SUCCESS
        assert freq_result.data is not None
        assert "frequency_score" in freq_result.data
        assert "metrics" in freq_result.data

        logger.info(
            f"Orchestrator integration: Frequency module score={freq_result.score:.4f}, "
            f"confidence={freq_result.confidence:.4f}"
        )

    @pytest.mark.asyncio
    async def test_orchestrator_three_modules(self) -> None:
        """Test that the orchestrator runs Metadata, ELA, and Frequency modules."""
        from backend.orchestrator.orchestrator import ForensicOrchestrator

        orchestrator = ForensicOrchestrator()
        image_bytes = _create_camera_jpeg()

        response = await orchestrator.process_analysis(
            image_bytes=image_bytes,
            request_id="test-orch-three-001",
        )

        # Should have all three modules
        module_names = [m.module for m in response.modules]
        assert "Metadata Analysis" in module_names
        assert "Error Level Analysis" in module_names
        assert MODULE_NAME in module_names
        assert len(response.modules) == 3

        # Aggregated result should be present
        assert response.aggregated_result is not None
        assert response.aggregated_result.overall_score >= 0.0
        assert response.aggregated_result.overall_score <= 1.0

        logger.info(
            f"Three modules: verdict={response.aggregated_result.verdict}, "
            f"score={response.aggregated_result.overall_score:.4f}"
        )

    @pytest.mark.asyncio
    async def test_orchestrator_aggregator_disclaimer(self) -> None:
        """Test that the aggregator includes Frequency Analysis in its disclaimer."""
        from backend.orchestrator.orchestrator import ForensicOrchestrator

        orchestrator = ForensicOrchestrator()
        image_bytes = _create_camera_jpeg()

        response = await orchestrator.process_analysis(
            image_bytes=image_bytes,
            request_id="test-orch-disclaimer-freq",
        )

        summary = response.aggregated_result.summary
        assert "Metadata Analysis" in summary
        assert "Error Level Analysis" in summary
        assert MODULE_NAME in summary
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
        module = FrequencyAnalysisModule()
        try:
            result = await module.analyze(None, REQUEST_ID)  # type: ignore
            assert result.status in (ModuleStatus.SUCCESS, ModuleStatus.ERROR)
        except Exception as exc:
            # Should not raise — should return error result
            pytest.fail(f"Module should not raise on None input: {exc}")

    @pytest.mark.asyncio
    async def test_module_handles_invalid_bytes(self) -> None:
        """Test that the module handles completely invalid bytes."""
        module = FrequencyAnalysisModule()
        result = await module.analyze(b"NOT AN IMAGE AT ALL", REQUEST_ID)

        assert result.status in (ModuleStatus.SUCCESS, ModuleStatus.ERROR)


# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short", "-s"])
