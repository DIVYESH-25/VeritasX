"""
VeritasX Backend Forensic Orchestrator
"""

import time
import uuid
import logging
from typing import Optional, List
from backend.orchestrator.dispatcher import ModuleDispatcher
from backend.orchestrator.executor import AsyncModuleExecutor
from backend.aggregation.aggregator import ForensicAggregator
from backend.schemas.models import (
    OrchestratorResponse,
    ModuleResult,
    ModuleStatus,
)

logger = logging.getLogger("veritasx.orchestrator")


class ForensicOrchestrator:
    """
    Central controller of the VeritasX backend pipeline.
    Coordinates forensic module dispatching, concurrent execution, aggregation, and response logging.
    """

    def __init__(
        self,
        dispatcher: Optional[ModuleDispatcher] = None,
        executor: Optional[AsyncModuleExecutor] = None,
        aggregator: Optional[ForensicAggregator] = None,
    ):
        self.dispatcher = dispatcher or ModuleDispatcher(auto_register_default=True)
        self.executor = executor or AsyncModuleExecutor()
        self.aggregator = aggregator or ForensicAggregator()

    async def process_analysis(
        self,
        image_bytes: bytes,
        request_id: Optional[str] = None
    ) -> OrchestratorResponse:
        """
        Main orchestration entrypoint for media forensic analysis.

        :param image_bytes: Raw binary image payload.
        :param request_id: Optional client-provided request ID. Automatically generated if omitted.
        :return: OrchestratorResponse object containing structured module outputs and aggregated verdict.
        """
        # Generate unique Request ID if not provided
        req_id = request_id or str(uuid.uuid4())
        pipeline_start = time.perf_counter()

        logger.info(f"[{req_id}] === Initializing VeritasX Forensic Analysis Request ===")

        # 1. Fetch active modules from dispatcher
        active_modules = self.dispatcher.get_active_modules()
        logger.info(f"[{req_id}] Active forensic modules loaded: {[m.name for m in active_modules]}")

        # 2. Execute modules concurrently
        module_results: List[ModuleResult] = await self.executor.execute_modules_concurrently(
            modules=active_modules,
            image_data=image_bytes,
            request_id=req_id,
        )

        # 3. Aggregate collected results
        aggregated = self.aggregator.aggregate(module_results)

        total_elapsed_ms = round((time.perf_counter() - pipeline_start) * 1000, 2)

        # Determine overall pipeline status
        has_errors = any(r.status == ModuleStatus.ERROR for r in module_results)
        pipeline_status = "partial_failure" if has_errors else "completed"
        if all(r.status == ModuleStatus.ERROR for r in module_results) and module_results:
            pipeline_status = "failed"

        logger.info(
            f"[{req_id}] === Pipeline {pipeline_status.upper()} in {total_elapsed_ms}ms "
            f"| Verdict: {aggregated.verdict} (Score: {aggregated.overall_score}) ==="
        )

        return OrchestratorResponse(
            request_id=req_id,
            total_execution_time_ms=total_elapsed_ms,
            status=pipeline_status,
            aggregated_result=aggregated,
            modules=module_results,
        )
