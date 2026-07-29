"""
Base Forensic Module Implementation with Exception Safety & Timing
"""

import time
import logging
import traceback
from typing import Dict, Any, Optional
from backend.orchestrator.interfaces import IForensicModule
from backend.schemas.models import ModuleResult, ModuleStatus

logger = logging.getLogger("veritasx.modules")


class BaseForensicModule(IForensicModule):
    """
    Base class for all forensic detection modules.
    Provides automatic execution timing, exception handling, and logging.
    """

    def __init__(self, name: str, description: str = "", enabled: bool = True):
        self._name = name
        self._description = description
        self._enabled = enabled

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    async def execute(self, image_data: bytes, request_id: str) -> ModuleResult:
        """
        Executes the forensic module with exception safety and microsecond-level timing.
        """
        if not self.is_enabled:
            logger.info(f"[{request_id}] Module '{self.name}' is disabled. Skipping.")
            return ModuleResult(
                module=self.name,
                status=ModuleStatus.SKIPPED,
                score=0.0,
                confidence=0.0,
                execution_time_ms=0.0,
                message="Module is disabled",
            )

        start_time = time.perf_counter()
        logger.info(f"[{request_id}] Starting module '{self.name}'...")

        try:
            result = await self.analyze(image_data, request_id)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            result.execution_time_ms = elapsed_ms
            logger.info(
                f"[{request_id}] Module '{self.name}' finished successfully in {elapsed_ms}ms "
                f"(score={result.score}, confidence={result.confidence})"
            )
            return result

        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            error_msg = str(exc)
            stack_trace = traceback.format_exc()
            logger.error(
                f"[{request_id}] Module '{self.name}' FAILED in {elapsed_ms}ms with error: {error_msg}\n{stack_trace}"
            )
            return ModuleResult(
                module=self.name,
                status=ModuleStatus.ERROR,
                score=0.0,
                confidence=0.0,
                execution_time_ms=elapsed_ms,
                message=f"Module execution failed: {error_msg}",
                error_details=stack_trace,
            )
