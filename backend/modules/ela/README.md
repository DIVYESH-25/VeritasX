# Error Level Analysis Module — VeritasX Forensic Backend

Production-ready Error Level Analysis (ELA) engine for media provenance
assessment and image forgery detection in the VeritasX forensic platform.

---

## 📌 Architecture Overview

The ELA module follows Clean Architecture and Single Responsibility
principles. It is structured into four independent, testable, and composable
layers orchestrated by `ErrorLevelAnalysisModule`:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      ErrorLevelAnalysisModule                           │
└──────┬──────────────────┬──────────────────┬─────────────────┬────────┘
       │                  │                  │                 │
       ▼                  ▼                  ▼                 ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Processor   │──►│ Visualizer   │──►│   Analyzer   │──►│    Scorer    │
│              │   │              │   │              │   │              │
│ (ELA algo:   │   │ (base64 ELA │   │ (Rule-based  │   │ (Dual-score  │
│  decode,     │   │  image gen)  │   │  observation │   │  calc)       │
│  recompress, │   │              │   │  engine)     │   │              │
│  diff, etc.) │   │              │   │              │   │              │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

### Clean Architecture Layers

1. **Processor Layer (`ElaProcessor`)**:
   - Decodes the raw image payload using Pillow (single decode).
   - Converts to RGB for consistent ELA computation.
   - Re-compresses the image as JPEG at a configurable quality level (default 90)
     using an in-memory `BytesIO` buffer (no disk temp files).
   - Computes the absolute pixel-wise difference between the original and
     recompressed image using NumPy.
   - Normalises differences to the 0–255 range and enhances visibility.
   - Converts to grayscale using OpenCV for metric and region analysis.
   - Calculates statistical metrics (average error, max/min error, std dev,
     high-error pixel count, dynamic range, mean brightness).
   - Detects suspicious regions via OpenCV connected-component analysis.

2. **Visualizer Layer (`ElaVisualizer`)**:
   - Converts the ELA numpy array into a base64-encoded PNG image.
   - Resizes large images (max 1024px) to keep API payloads reasonable.

3. **Analyzer Layer (`ElaAnalyzer`)**:
   - Rule-based observation engine evaluating 8+ forensic detection heuristics.
   - Detects:
     - Uniform compression (consistent single-pass encoding)
     - Localized recompression (regional editing)
     - Heavy JPEG artifacts
     - Multiple compression signatures (multi-stage re-saving)
     - Edited region suspected (bounding box reporting)
     - Screenshot characteristics
     - Possible synthetic generation indicators
     - Consistent camera compression

4. **Scoring Engine (`ElaScorer`)**:
   - Calculates dual scores:
     - `ela_score` (0.0 = highly suspicious → 1.0 = consistent compression)
     - `confidence_score` (0.0 = low confidence → 1.0 = high confidence)
   - Applies weighted scoring across average error (25%), standard deviation
     (20%), high-error pixel percentage (25%), dynamic range (15%), and
     suspicious region count (15%).

---

## 🚀 Public Interface & Usage

### Basic Execution

```python
from backend.modules.ela import ErrorLevelAnalysisModule

# Instantiate module (offline execution, no external API keys required)
module = ErrorLevelAnalysisModule()

# Analyze image bytes
result = await module.analyze(image_bytes=raw_data, request_id="req-12345")

print(f"Status: {result.status}")
print(f"Module Score (Synthetic Likelihood): {result.score:.4f}")
print(f"Confidence: {result.confidence:.4f}")
print(f"ELA Score (Trustworthiness): {result.data['ela_score']:.4f}")
```

### Configurable JPEG Quality

```python
# Use a different JPEG quality for re-compression
module = ErrorLevelAnalysisModule(jpeg_quality=75)
```

### Orchestrator Integration

The module implements `BaseForensicModule` / `IForensicModule` and registers
automatically with the VeritasX `ModuleDispatcher`:

```python
from backend.orchestrator.orchestrator import ForensicOrchestrator

orchestrator = ForensicOrchestrator()
response = await orchestrator.process_analysis(image_bytes=image_bytes)
```

---

## 📊 Score Calculation Logic

| Metric | Range | Description |
|---|---|---|
| **Module Result Score** | `0.0 – 1.0` | `1.0 - ela_score`. Inverted for platform consistency (0 = Authentic, 1 = Synthetic/Manipulated). |
| **ELA Score** | `0.0 – 1.0` | Direct trustworthiness score of compression consistency. |
| **Confidence Score** | `0.0 – 1.0` | Confidence level based on image size, format, and signal clarity. |

### ELA Algorithm

1. **Decode** the image using Pillow
2. **Convert** to RGB
3. **Save** a temporary JPEG at the configured quality (in-memory `BytesIO`)
4. **Reload** the compressed JPEG
5. **Compute** the absolute pixel-wise difference (NumPy)
6. **Normalize** differences to 0–255
7. **Enhance** visibility with a quality-dependent gain factor
8. **Produce** the ELA image (RGB uint8 array)
9. **Remove** temporary buffers (automatic garbage collection)
10. **Return** the result

### Scoring Factors

| Factor | Weight | Direction |
|---|---|---|
| Average Error | 25% | Lower = more consistent |
| Standard Deviation | 20% | Lower = more consistent |
| High-Error Pixel % | 25% | Lower = more consistent |
| Dynamic Range | 15% | Lower = more consistent |
| Suspicious Regions | 15% | Fewer = more consistent |

---

## 🧪 Testing & Verification

Run unit and integration tests using `pytest`:

```bash
pytest backend/modules/ela/tests.py -v
```

### Covered Test Scenarios
- ✅ Camera JPEG (consistent compression)
- ✅ PNG image (lossless → recompressed as JPEG)
- ✅ Screenshot (uniform low error)
- ✅ AI-generated image (uniform low error pattern)
- ✅ Edited JPEG (localized recompression)
- ✅ Multiple JPEG quality levels (75, 85, 90, 95)
- ✅ Corrupted image (graceful fallback)
- ✅ Large image (4000×4000)
- ✅ Small image (10×10)
- ✅ Orchestrator compatibility
- ✅ Aggregator compatibility
- ✅ Exception handling resilience
