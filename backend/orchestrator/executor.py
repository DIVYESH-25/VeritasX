"""
Concurrent Async Module Executor for VeritasX
"""

import asyncio
import logging
import time
from typing import List
from backend.orchestrator.interfaces import IForensicModule
from backend.schemas.models import ModuleResult, ModuleStatus

logger = logging.getLogger("veritasx.executor")


class AsyncModuleExecutor:
    """
    Executes multiple forensic modules concurrently using Python asyncio.gather().
    Provides complete error isolation: failure of one module will not crash or stall others.
    """

    async def execute_modules_concurrently(
        self,
        modules: List[IForensicModule],
        image_data: bytes,
        request_id: str
    ) -> List[ModuleResult]:
        """
        Executes a list of forensic modules in parallel.

        :param modules: List of IForensicModule instances to execute.
        :param image_data: Preprocessed image payload as bytes.
        :param request_id: Unique request identifier.
        :return: List of ModuleResult objects corresponding to each module.
        """
        if not modules:
            logger.warning(f"[{request_id}] No active forensic modules provided to executor.")
            return []

        logger.info(f"[{request_id}] Dispatching {len(modules)} forensic modules concurrently...")
        start_time = time.perf_counter()

        # Create coroutine tasks for each active module
        tasks = [mod.execute(image_data, request_id) for mod in modules]

        # Execute concurrently with return_exceptions=True for total error isolation
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: List[ModuleResult] = []

        for mod, res in zip(modules, raw_results):
            if isinstance(res, Exception):
                # Critical safety net: Exception escaped module's internal error handler
                logger.error(
                    f"[{request_id}] Unhandled exception escaped from module '{mod.name}': {res}",
                    exc_info=res,
                )
                results.append(
                    ModuleResult(
                        module=mod.name,
                        status=ModuleStatus.ERROR,
                        score=0.0,
                        confidence=0.0,
                        execution_time_ms=0.0,
                        message=f"Unhandled executor exception: {str(res)}",
                        error_details=str(res),
                    )
                )
            elif isinstance(res, ModuleResult):
                results.append(res)
            else:
                logger.error(f"[{request_id}] Module '{mod.name}' returned invalid type: {type(res)}")
                results.append(
                    ModuleResult(
                        module=mod.name,
                        status=ModuleStatus.ERROR,
                        score=0.0,
                        confidence=0.0,
                        execution_time_ms=0.0,
                        message="Invalid return type from module",
                    )
                )

        total_elapsed = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            f"[{request_id}] Concurrent execution of {len(modules)} modules completed in {total_elapsed}ms."
        )

        return results
