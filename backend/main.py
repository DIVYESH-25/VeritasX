"""
VeritasX Backend API Entrypoint & FastAPI Server
"""

import logging
import uuid
from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.schemas.models import (
    OrchestratorResponse,
    HealthCheckResponse,
)
from backend.services.analysis_service import AnalysisService, get_analysis_service

# Configure Structured Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("veritasx.api")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-ready Backend Orchestrator for VeritasX AI Media Forensic System.",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/api/v1/health",
    response_model=HealthCheckResponse,
    tags=["System Health"],
    summary="Backend Health Check",
)
async def health_check(
    service: AnalysisService = Depends(get_analysis_service)
) -> HealthCheckResponse:
    """
    Returns system operational status and list of active forensic detection modules.
    """
    active_mods = [m.name for m in service.orchestrator.dispatcher.get_active_modules()]
    return HealthCheckResponse(
        status="healthy",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        active_modules=active_mods,
    )


@app.post(
    "/api/v1/analyze",
    response_model=OrchestratorResponse,
    status_code=status.HTTP_200_OK,
    tags=["Forensic Orchestrator"],
    summary="Submit Image for Multi-Module Forensic Analysis",
)
async def analyze_image(
    file: UploadFile = File(..., description="Image file to analyze (JPEG, PNG, WEBP)"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
    service: AnalysisService = Depends(get_analysis_service),
) -> OrchestratorResponse:
    """
    Primary API endpoint for media analysis.
    Accepts an uploaded image, generates a Request ID, dispatches all active forensic modules
    concurrently using asyncio, and returns an aggregated forensic verdict.
    """
    req_id = x_request_id or str(uuid.uuid4())
    logger.info(f"[{req_id}] Received upload request: filename='{file.filename}', content_type='{file.content_type}'")

    if not file.content_type or not file.content_type.startswith("image/"):
        logger.warning(f"[{req_id}] Invalid media type: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file.content_type}'. Expected an image format (JPEG, PNG, WEBP)."
        )

    try:
        image_bytes = await file.read()
        if len(image_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes)."
            )

        if len(image_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
            max_mb = settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed limit of {max_mb}MB."
            )

        # Process through Orchestrator Pipeline
        response = await service.analyze_image(
            image_bytes=image_bytes,
            request_id=req_id
        )

        return response

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[{req_id}] Server error processing image: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Orchestrator Error: {str(exc)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
