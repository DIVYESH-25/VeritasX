"""
Verification Test Script for VeritasX Backend Orchestrator
"""

import asyncio
import logging
from backend.orchestrator.orchestrator import ForensicOrchestrator
from backend.orchestrator.dispatcher import ModuleDispatcher
from backend.modules.base import BaseForensicModule
from backend.schemas.models import ModuleResult, ModuleStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger("test_orchestrator")


class SimulatedFailingModule(BaseForensicModule):
    """Failing test module to verify error handling resilience."""
    def __init__(self):
        super().__init__(name="Simulated Faulty Module", description="Test module that deliberately fails")

    async def analyze(self, image_data: bytes, request_id: str) -> ModuleResult:
        raise RuntimeError("Simulated internal GPU/C2PA memory error!")


def _generate_authentic_image() -> bytes:
    import io
    import piexif
    from PIL import Image

    img = Image.new("RGB", (800, 600), color=(120, 120, 120))
    zeroth = {
        piexif.ImageIFD.Make: "Canon",
        piexif.ImageIFD.Model: "Canon EOS R5",
        piexif.ImageIFD.DateTime: "2024:01:15 10:30:00",
    }
    exif = {
        piexif.ExifIFD.DateTimeOriginal: "2024:01:15 10:30:00",
        piexif.ExifIFD.ISOSpeedRatings: 100,
        piexif.ExifIFD.FocalLength: (50, 1),
        piexif.ExifIFD.FNumber: (28, 10),
    }
    exif_bytes = piexif.dump({"0th": zeroth, "Exif": exif})
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif_bytes, quality=95)
    return buf.getvalue()


async def run_tests():
    logger.info("==================================================")
    logger.info("   VeritasX Backend Orchestrator Test Suite       ")
    logger.info("==================================================")

    # Test 1: Standard Orchestration with Core Forensic Modules
    logger.info("\n--- TEST 1: Standard Multi-Module Orchestration ---")
    orchestrator = ForensicOrchestrator()
    dummy_image = _generate_authentic_image()

    response = await orchestrator.process_analysis(image_bytes=dummy_image)

    print("\n[Orchestrator Response JSON]")
    print(response.model_dump_json(indent=2))

    assert response.request_id is not None
    assert len(response.modules) == 2
    assert response.status == "completed"
    assert response.aggregated_result.verdict == "REAL"
    print("\n[OK] TEST 1 PASSED: Standard Orchestration Successful.")

    # Test 2: Concurrency & Error Isolation Test
    logger.info("\n--- TEST 2: Error Resilience & Fault Tolerance ---")
    custom_dispatcher = ModuleDispatcher(auto_register_default=True)
    custom_dispatcher.register_module(SimulatedFailingModule())

    resilient_orchestrator = ForensicOrchestrator(dispatcher=custom_dispatcher)
    fault_response = await resilient_orchestrator.process_analysis(image_bytes=dummy_image)

    print("\n[Faulty Pipeline Response JSON]")
    print(fault_response.model_dump_json(indent=2))

    assert len(fault_response.modules) == 3
    assert fault_response.status == "partial_failure"

    failing_result = next(m for m in fault_response.modules if m.module == "Simulated Faulty Module")
    assert failing_result.status == ModuleStatus.ERROR
    assert "Simulated internal GPU/C2PA memory error!" in failing_result.message

    print("\n[OK] TEST 2 PASSED: Error Resilience Verified. Orchestrator survived module failure.")
    logger.info("\n==================================================")
    logger.info("  ALL ORCHESTRATOR TESTS COMPLETED SUCCESSFULLY!  ")
    logger.info("==================================================")


if __name__ == "__main__":
    asyncio.run(run_tests())
