"""
Analysis Application Service & Dependency Injection Factory
"""

import logging
from typing import Optional
from backend.orchestrator.orchestrator import ForensicOrchestrator
from backend.schemas.models import OrchestratorResponse

logger = logging.getLogger("veritasx.service")


class AnalysisService:
    """
    Application Service layer providing orchestration management for API endpoints.
    """

    def __init__(self, orchestrator: Optional[ForensicOrchestrator] = None):
        self.orchestrator = orchestrator or ForensicOrchestrator()

    async def analyze_image(
        self,
        image_bytes: bytes,
        request_id: Optional[str] = None
    ) -> OrchestratorResponse:
        """
        Executes complete forensic analysis pipeline for an uploaded image payload.
        """
        if not image_bytes:
            raise ValueError("Image payload cannot be empty.")

        return await self.orchestrator.process_analysis(
            image_bytes=image_bytes,
            request_id=request_id
        )


# Singleton factory for FastAPI dependency injection
_analysis_service_instance: Optional[AnalysisService] = None


def get_analysis_service() -> AnalysisService:
    """FastAPI Dependency Provider for AnalysisService."""
    global _analysis_service_instance
    if _analysis_service_instance is None:
        _analysis_service_instance = AnalysisService()
    return _analysis_service_instance
