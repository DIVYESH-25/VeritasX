"""
Module Dispatcher for VeritasX Forensic Engines
"""

import logging
from typing import Dict, List, Optional
from backend.orchestrator.interfaces import IForensicModule

logger = logging.getLogger("veritasx.dispatcher")


class ModuleDispatcher:
    """
    Manages registration, lifecycle, and retrieval of active forensic detection modules.
    Enforces Open/Closed Principle: New modules can be added dynamically without modifying the Orchestrator.
    """

    def __init__(self, auto_register_default: bool = True):
        self._registry: Dict[str, IForensicModule] = {}
        if auto_register_default:
            self._register_default_modules()

    def _register_default_modules(self) -> None:
        """Register active forensic detection modules (Metadata Analysis)."""
        from backend.modules.metadata import MetadataAnalysisModule

        defaults = [
            MetadataAnalysisModule(),
        ]
        for mod in defaults:
            self.register_module(mod)

    def register_module(self, module: IForensicModule) -> None:
        """
        Register a new forensic module. Overwrites existing module if same name exists.
        """
        if not isinstance(module, IForensicModule):
            raise TypeError(f"Module must implement IForensicModule. Got {type(module)}")

        self._registry[module.name] = module
        logger.info(f"Registered forensic module: '{module.name}' (enabled={module.is_enabled})")

    def unregister_module(self, module_name: str) -> Optional[IForensicModule]:
        """
        Unregister a forensic module by name.
        """
        removed = self._registry.pop(module_name, None)
        if removed:
            logger.info(f"Unregistered forensic module: '{module_name}'")
        return removed

    def get_module(self, module_name: str) -> Optional[IForensicModule]:
        """
        Retrieve a single module by name.
        """
        return self._registry.get(module_name)

    def get_active_modules(self) -> List[IForensicModule]:
        """
        Return a list of all currently enabled modules.
        """
        return [mod for mod in self._registry.values() if mod.is_enabled]

    def get_all_modules(self) -> List[IForensicModule]:
        """
        Return a list of all registered modules regardless of enabled status.
        """
        return list(self._registry.values())
