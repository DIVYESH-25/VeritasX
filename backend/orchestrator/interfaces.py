"""
VeritasX Forensic Module Interfaces & Protocols
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from backend.schemas.models import ModuleResult


class IForensicModule(ABC):
    """
    Abstract interface that all forensic detection modules must implement.
    Adheres to SOLID Principles (Interface Segregation & Dependency Inversion).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier name for the module."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Brief description of what the module detects."""
        pass

    @property
    @abstractmethod
    def is_enabled(self) -> bool:
        """Flag indicating whether the module is currently active."""
        pass

    @abstractmethod
    async def analyze(self, image_data: bytes, request_id: str) -> ModuleResult:
        """
        Asynchronously perform forensic analysis on preprocessed image bytes.

        :param image_data: Preprocessed image payload as raw bytes.
        :param request_id: Unique request identifier for request tracing.
        :return: Standardized ModuleResult instance.
        """
        pass

    @abstractmethod
    async def execute(self, image_data: bytes, request_id: str) -> ModuleResult:
        """
        Safe execution wrapper that handles exception catching and execution timing.
        """
        pass
