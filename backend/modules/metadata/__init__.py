"""
Metadata Analysis Module for VeritasX

This package provides a production-ready metadata analysis engine that extracts,
validates, and analyses image metadata (EXIF, XMP, ICC profiles, and AI
generator signatures) to assess media provenance and detect forensic anomalies.

Public Interface
----------------
    from backend.modules.metadata import MetadataAnalysisModule

    module = MetadataAnalysisModule()
    result = await module.analyze(image_bytes, request_id)

Architecture
------------
The module follows Clean Architecture with four independent layers:

1. **Extractor** (``MetadataExtractor``) — Extracts file info, image info, and EXIF data.
2. **Validator** (``MetadataValidator``) — Validates metadata and generates issues.
3. **Analyzer** (``MetadataAnalyzer``) — Rule-based forensic observation generation.
4. **Scorer** (``MetadataScorer``) — Calculates metadata_score and confidence_score.

Each layer is injectable, allowing for easy testing and customisation.
"""

from backend.modules.metadata.analyzer import MetadataAnalyzer
from backend.modules.metadata.extractor import MetadataExtractor
from backend.modules.metadata.module import MetadataAnalysisModule
from backend.modules.metadata.scorer import MetadataScorer
from backend.modules.metadata.validator import MetadataValidator

__all__ = [
    "MetadataAnalysisModule",
    "MetadataExtractor",
    "MetadataValidator",
    "MetadataAnalyzer",
    "MetadataScorer",
]
