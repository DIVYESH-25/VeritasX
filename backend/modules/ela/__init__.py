"""
Error Level Analysis Module for VeritasX

This package provides a production-ready Error Level Analysis (ELA) engine
that detects compression-level anomalies across image regions to identify
potential manipulation, re-compression, and synthetic generation indicators.

Public Interface
----------------
    from backend.modules.ela import ErrorLevelAnalysisModule

    module = ErrorLevelAnalysisModule()
    result = await module.analyze(image_bytes, request_id)

Architecture
------------
The module follows Clean Architecture with four independent layers:

1. **Processor** (``ElaProcessor``) — Implements the standard ELA algorithm:
   decode, RGB-convert, JPEG re-compress at configurable quality, compute
   absolute pixel differences, normalise, enhance, and produce the ELA image.
   Also computes statistical metrics and detects suspicious regions.
2. **Visualizer** (``ElaVisualizer``) — Converts the ELA numpy array into a
   base64-encoded image for API/frontend consumption.
3. **Analyzer** (``ElaAnalyzer``) — Rule-based forensic observation engine.
4. **Scorer** (``ElaScorer``) — Calculates ela_score and confidence_score.

Each layer is injectable, allowing for easy testing and customisation.
"""

from backend.modules.ela.analyzer import ElaAnalyzer
from backend.modules.ela.module import ErrorLevelAnalysisModule
from backend.modules.ela.processor import ElaProcessor
from backend.modules.ela.scorer import ElaScorer
from backend.modules.ela.visualization import ElaVisualizer

__all__ = [
    "ErrorLevelAnalysisModule",
    "ElaProcessor",
    "ElaAnalyzer",
    "ElaScorer",
    "ElaVisualizer",
]
