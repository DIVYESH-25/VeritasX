"""
Frequency Analysis Module for VeritasX

This package provides a production-ready FFT-based frequency domain analysis
engine that detects periodic structures, checkerboard artifacts, aliasing,
banding, ringing, and other frequency-domain anomalies that may indicate
AI synthesis or digital manipulation.

Public Interface
----------------
    from backend.modules.frequency import FrequencyAnalysisModule

    module = FrequencyAnalysisModule()
    result = await module.analyze(image_bytes, request_id)

Architecture
------------
The module follows Clean Architecture with four independent layers:

1. **Processor** (``FrequencyProcessor``) — Implements the FFT pipeline:
   decode, grayscale convert, optional Hann windowing, 2D FFT, fftshift,
   log-scaled magnitude spectrum, and frequency-domain metric computation.
2. **Visualizer** (``FrequencyVisualizer``) — Converts the magnitude
   spectrum numpy array into a base64-encoded PNG for API/frontend
   consumption.
3. **Analyzer** (``FrequencyAnalyzer``) — Rule-based forensic observation
   engine operating on the computed metrics.
4. **Scorer** (``FrequencyScorer``) — Calculates frequency_score and
   confidence_score.

Each layer is injectable, allowing for easy testing and customisation.
"""

from backend.modules.frequency.analyzer import FrequencyAnalyzer
from backend.modules.frequency.module import FrequencyAnalysisModule
from backend.modules.frequency.processor import FrequencyProcessor
from backend.modules.frequency.scorer import FrequencyScorer
from backend.modules.frequency.visualization import FrequencyVisualizer

__all__ = [
    "FrequencyAnalysisModule",
    "FrequencyProcessor",
    "FrequencyAnalyzer",
    "FrequencyScorer",
    "FrequencyVisualizer",
]
