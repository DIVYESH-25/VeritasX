"""
VeritasX Backend Schemas & Pydantic Data Models
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ModuleStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


class ModuleResult(BaseModel):
    """
    Standardized result structure returned by every forensic module.
    """
    module: str = Field(..., description="Name of the forensic module")
    status: ModuleStatus = Field(default=ModuleStatus.SUCCESS, description="Execution status")
    score: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score of AI manipulation (0 = Real, 1 = Fake)")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Module's self-reported confidence in its analysis")
    execution_time_ms: float = Field(default=0.0, description="Execution duration in milliseconds")
    message: str = Field(default="Module analysis complete", description="Human readable summary or status message")
    error_details: Optional[str] = Field(default=None, description="Exception trace or error message if status is error")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Detailed module-specific raw payload or metrics")


class AggregatedResult(BaseModel):
    """
    Aggregated forensic analysis verdict combining scores from all executed modules.
    """
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Weighted composite score (0 = Real, 1 = AI Generated)")
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Combined confidence score across modules")
    verdict: str = Field(..., description="Categorical verdict: REAL | AI_GENERATED | UNCERTAIN")
    risk_level: str = Field(..., description="Risk assessment: LOW | MEDIUM | HIGH | CRITICAL")
    summary: str = Field(..., description="Executive summary explaining the forensic verdict")
    active_module_count: int = Field(default=0, description="Number of modules evaluated")
    successful_module_count: int = Field(default=0, description="Number of modules that executed successfully")


class OrchestratorResponse(BaseModel):
    """
    Final structured API response returned by the VeritasX Backend Orchestrator.
    """
    request_id: str = Field(..., description="Unique UUID identifier for this analysis request")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Analysis timestamp in UTC")
    total_execution_time_ms: float = Field(..., description="Total wall-clock duration of orchestration pipeline in milliseconds")
    status: str = Field(default="completed", description="Overall pipeline status: completed | partial_failure | failed")
    aggregated_result: AggregatedResult = Field(..., description="Aggregated summary and verdict")
    modules: List[ModuleResult] = Field(default_factory=list, description="Detailed list of results from all forensic modules")


class HealthCheckResponse(BaseModel):
    """
    Health check status endpoint response.
    """
    status: str = "healthy"
    service: str = "VeritasX Backend Orchestrator"
    version: str = "1.0.0"
    active_modules: List[str] = Field(default_factory=list)
