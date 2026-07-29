# Metadata Analysis Module — VeritasX Forensic Backend

Production-ready metadata analysis engine for media provenance assessment and image forgery detection in the VeritasX forensic platform.

---

## 📌 Architecture Overview

The Metadata Analysis module follows Clean Architecture and Single Responsibility principles. It is structured into four independent, testable, and composable layers orchestrated by `MetadataAnalysisModule`:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MetadataAnalysisModule                              │
└──────┬──────────────────────┬──────────────────────┬─────────────────┬──────┘
       │                      │                      │                 │
       ▼                      ▼                      ▼                 ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐    ┌──────────────┐
│  Extractor   │ ────►│  Validator   │ ────►│   Analyzer   │───►│    Scorer    │
│              │      │              │      │              │    │              │
│ (Pillow,     │      │ (EXIF & Tag  │      │ (Rule-based  │    │ (Dual-score  │
│  piexif,     │      │  Integrity   │      │  Observation │    │  Calculation │
│  exifread)   │      │  Checks)     │      │  Engine)     │    │  Engine)     │
└──────────────┘      └──────────────┘      └──────────────┘    └──────────────┘
```

### Clean Architecture Layers

1. **Extractor Layer (`MetadataExtractor`)**:
   - Opens the raw image payload **once** using Pillow to minimize CPU & memory overhead.
   - Extracts EXIF data via `piexif` (fast binary tag parsing) with `exifread` as a fallback.
   - Captures PNG text chunks (`tEXt`, `iTXt`, `zTXt`) and WEBP EXIF blocks.
   - Calculates cryptographic digests (SHA-256, MD5) and detects MIME type via magic bytes.

2. **Validator Layer (`MetadataValidator`)**:
   - Inspects extracted metadata for structural corruption, missing tags, unparseable dates, future timestamps, and impossible years (< 1826 or > 2100).
   - Validates GPS coordinates against range constraints `[-90, 90]` and `[-180, 180]`.
   - Identifies duplicate EXIF tags and unmapped non-standard tags.

3. **Analyzer Layer (`MetadataAnalyzer`)**:
   - Rule-based observation engine evaluating 10+ forensic detection heuristics.
   - Detects AI generator signatures (`Software` tag matches for Stable Diffusion, Automatic1111, ComfyUI, Midjourney, InvokeAI).
   - Detects editing software signatures (Adobe Photoshop, Lightroom, GIMP, Canva, Snipping Tool).
   - Categorizes device origin (mobile camera makes vs. DSLR / professional camera makes).

4. **Scoring Engine (`MetadataScorer`)**:
   - Calculates dual scores:
     - `metadata_score` (0.0 = suspicious/synthetic → 1.0 = organic/trustworthy).
     - `confidence_score` (0.0 = low confidence → 1.0 = high confidence).
   - Applies weighted scoring across EXIF richness (25%), camera info (20%), timestamps (15%), GPS (10%), validation penalties (15%), and AI generator penalties (15% + 0.50 direct deduction).

---

## 🚀 Public Interface & Usage

### Basic Execution

```python
from backend.modules.metadata import MetadataAnalysisModule

# Instantiate module (offline execution, no external API keys required)
module = MetadataAnalysisModule()

# Analyze image bytes
result = await module.analyze(image_bytes=raw_data, request_id="req-12345")

print(f"Status: {result.status}")
print(f"Module Score (Synthetic Likelihood): {result.score:.4f}")
print(f"Confidence: {result.confidence:.4f}")
print(f"Metadata Score (Trustworthiness): {result.data['metadata_score']:.4f}")
```

### Orchestrator Integration

The module implements `BaseForensicModule` / `IForensicModule` and registers automatically with the VeritasX `ModuleDispatcher`:

```python
from backend.orchestrator.orchestrator import ForensicOrchestrator

orchestrator = ForensicOrchestrator()
response = await orchestrator.process_analysis(image_bytes=image_bytes)
```

---

## 📊 Score Calculation Logic

| Metric | Range | Description |
|---|---|---|
| **Module Result Score** | `0.0 – 1.0` | `1.0 - metadata_score`. Inverted for platform consistency (0 = Authentic, 1 = Synthetic/Manipulated). |
| **Metadata Score** | `0.0 – 1.0` | Direct trustworthiness score of metadata integrity. |
| **Confidence Score** | `0.0 – 1.0` | Confidence level based on tag richness and signal clarity. |

---

## 🧪 Testing & Verification

Run unit and integration tests using `pytest`:

```bash
pytest backend/modules/metadata/tests.py -v
```

Run backend orchestrator integration tests:

```bash
python -m backend.test_orchestrator
```

### Covered Test Scenarios
- ✅ JPEG with rich EXIF tags
- ✅ JPEG without EXIF metadata (stripped metadata detection)
- ✅ PNG images with/without text chunks
- ✅ WEBP images with EXIF data
- ✅ AI Generator signatures (Stable Diffusion, Automatic1111, Midjourney)
- ✅ Editing software signatures (Adobe Photoshop, GIMP, Canva)
- ✅ Screenshot signatures (Windows Snipping Tool, ShareX, Lightshot)
- ✅ Corrupted image byte streams
- ✅ Large images (4000x4000) and small thumbnail images (10x10)
- ✅ Future timestamps and impossible dates
- ✅ Concurrent execution with `ForensicOrchestrator`
