# Frequency Analysis Module

## Overview

The Frequency Analysis module performs FFT-based (Fast Fourier Transform)
frequency-domain analysis of images to detect forensic anomalies that may
indicate AI synthesis or digital manipulation.

Frequency-domain analysis is a cornerstone of digital image forensics. Natural
photographs exhibit characteristic frequency signatures: low frequencies
dominate (due to smooth surfaces and gradual lighting), energy rolls off
smoothly at higher frequencies, and the horizontal/vertical energy distribution
is generally balanced. AI-generated images, screenshots, and heavily processed
images can deviate from these natural patterns in measurable ways.

## Theory of FFT-Based Frequency Analysis

### The 2D Fourier Transform

The 2D Discrete Fourier Transform (DFT) converts an image from the spatial
domain to the frequency domain:

```
F(u, v) = Σ Σ f(x, y) · e^(-j·2π·(ux/M + vy/N))
```

Where:
- `f(x, y)` is the pixel intensity at position (x, y)
- `F(u, v)` is the complex-valued frequency component at frequency (u, v)
- `M`, `N` are the image dimensions

### Pipeline

1. **Decode** the image using Pillow
2. **Convert to grayscale** — frequency analysis is performed on luminance
3. **Apply Hann window** (optional) — reduces spectral leakage at image borders
4. **Compute 2D FFT** via `np.fft.fft2` (O(N log N) via Cooley-Tukey algorithm)
5. **Shift zero-frequency** to center via `np.fft.fftshift`
6. **Compute magnitude spectrum**: `|F(u, v)| = √(Re² + Im²)`
7. **Logarithmic scaling**: `log(1 + |F|)` — compresses dynamic range
8. **Normalize** to [0, 1] for analysis and visualization
9. **Calculate frequency-domain statistics**

### Key Concepts

- **Low-frequency dominance**: Natural images have most energy in low
  frequencies (smooth areas, gradual tonal changes). A flat or high-frequency-
  dominant spectrum can indicate synthetic generation.

- **Spectral entropy**: Measures how concentrated or spread out the energy is.
  High entropy = uniform distribution; low entropy = concentrated peaks.

- **Radial energy distribution**: Energy fraction at different radii from the
  center. Natural images concentrate energy near the center.

- **H/V balance**: The ratio of horizontal to vertical frequency energy.
  Natural images are typically balanced; strong asymmetry can indicate
  directional artifacts.

- **Peak-to-mean ratio**: The ratio of the strongest frequency component to
  the average. High values indicate periodic structures or grid artifacts.

- **Radial symmetry**: How similar the spectrum is to its 180° rotation.
  Excessive symmetry can indicate synthetic generation.

## Architecture

The module follows Clean Architecture principles, mirroring the structure of
the existing ELA and Metadata Analysis modules:

```
backend/modules/frequency/
├── __init__.py          # Package exports
├── module.py            # Entry point (FrequencyAnalysisModule)
├── processor.py         # FFT pipeline & metrics computation
├── analyzer.py          # Rule-based observation engine
├── scorer.py            # frequency_score & confidence_score calculation
├── visualization.py     # Base64 spectrum image generation
├── constants.py         # Static thresholds, weights, identifiers
├── models.py            # Pydantic DTOs
├── utils.py             # Image loading & encoding helpers
├── tests.py             # Automated test suite
└── README.md            # This file
```

### Layers

1. **Processor** (`FrequencyProcessor`): Implements the core FFT pipeline.
   Decodes the image, converts to grayscale, applies optional windowing,
   computes the 2D FFT, and calculates frequency-domain metrics.

2. **Visualizer** (`FrequencyVisualizer`): Converts the magnitude spectrum
   numpy array into a base64-encoded PNG for API/frontend consumption.

3. **Analyzer** (`FrequencyAnalyzer`): Rule-based forensic observation engine.
   Inspects the computed metrics and generates structured observations with
   severity and confidence levels.

4. **Scorer** (`FrequencyScorer`): Calculates `frequency_score` (0.0 =
   suspicious, 1.0 = consistent natural spectrum) and `confidence_score`
   (0.0 = low, 1.0 = high).

5. **Module** (`FrequencyAnalysisModule`): The main entry point that
   orchestrates the four layers and returns a standardised `ModuleResult`.

### Dependency Injection

Each layer is injected via the constructor with sensible defaults, allowing
for easy testing and customisation:

```python
from backend.modules.frequency import FrequencyAnalysisModule

module = FrequencyAnalysisModule()
# Custom processor with no Hann window
module = FrequencyAnalysisModule(apply_hann=False)
# Inject custom analyzer
module = FrequencyAnalysisModule(analyzer=CustomAnalyzer())
```

## Metrics

The following metrics are computed from the FFT magnitude spectrum:

| Metric | Description |
|--------|-------------|
| `low_frequency_energy` | Total energy in the central low-frequency region |
| `high_frequency_energy` | Total energy in the outer high-frequency region |
| `energy_ratio` | Ratio of low-frequency to high-frequency energy |
| `mean_magnitude` | Mean spectral magnitude (log-scaled) |
| `std_magnitude` | Standard deviation of spectral magnitude |
| `spectral_entropy` | Normalised entropy of the magnitude distribution |
| `peak_to_mean_ratio` | Ratio of peak magnitude to mean magnitude |
| `radial_energy_innner` | Energy fraction in the inner radius (0–25%) |
| `radial_energy_mid` | Energy fraction in the mid radius (25–75%) |
| `radial_energy_outer` | Energy fraction in the outer radius (75–100%) |
| `horizontal_energy_fraction` | Fraction of energy in horizontal frequency bands |
| `vertical_energy_fraction` | Fraction of energy in vertical frequency bands |
| `hv_balance_ratio` | Ratio of horizontal to vertical energy concentration |
| `radial_symmetry_score` | Measure of radial symmetry in the spectrum |

## Observations

The analyzer generates structured observations based on measurable
characteristics of the spectrum:

- **Periodic Structures Detected**: Strong peaks in the spectrum indicating
  repetitive patterns
- **Checkerboard Pattern Detected**: Sharp peaks with low entropy, characteristic
  of checkerboard artifacts
- **High-Frequency Aliasing**: Elevated high-frequency energy near Nyquist
- **Unusually High-Frequency Content**: Flat spectrum with low energy ratio
- **Spectral Asymmetry**: Imbalanced H/V energy distribution
- **Banding Detected**: Structured variations in the spectrum
- **Ringing Artifacts**: Patterns consistent with Gibbs phenomenon
- **Spectrum Appears Balanced**: Healthy frequency distribution (natural)
- **Low-Frequency Dominant**: Typical of natural photographs
- **Unusually Smooth Spectrum**: Can occur in AI-generated images
- **Natural Frequency Footprint**: Overall natural characteristics

## Scoring

### frequency_score

- **0.0** = Suspicious/synthetic frequency characteristics
- **1.0** = Consistent natural frequency spectrum

Factors (weighted):
- Energy ratio (25%)
- Spectral entropy (20%)
- Magnitude standard deviation (15%)
- H/V balance (15%)
- Peak-to-mean ratio (15%)
- Radial symmetry (10%)

### confidence_score

- **0.0** = Low confidence in the analysis
- **1.0** = High confidence in the analysis

Factors:
- Image size (more pixels = higher confidence)
- Image format (JPEG native for frequency analysis)
- Signal clarity (non-zero metrics)

### ModuleResult Score Convention

The module follows the VeritasX convention: score = 1.0 - frequency_score,
so 0 = Real and 1 = Fake.

## API Usage

### Direct Module Usage

```python
import asyncio
from backend.modules.frequency import FrequencyAnalysisModule

module = FrequencyAnalysisModule()
result = await module.analyze(image_bytes, "request-123")

print(f"Score: {result.score}")           # 0 = Real, 1 = Fake
print(f"Confidence: {result.confidence}")
print(f"Frequency Score: {result.data['frequency_score']}")
print(f"Observations: {len(result.data['observations'])}")
print(f"FFT Spectrum: {result.data['fft_spectrum']['base64'][:50]}...")
```

### Via Orchestrator

The module is automatically registered in the dispatcher and participates
in the full orchestration pipeline:

```python
from backend.orchestrator.orchestrator import ForensicOrchestrator

orchestrator = ForensicOrchestrator()
response = await orchestrator.process_analysis(image_bytes, "request-123")

for module_result in response.modules:
    if module_result.module == "Frequency Analysis":
        print(f"Frequency score: {module_result.score}")
        print(f"FFT spectrum available: {module_result.data['fft_spectrum'] is not None}")
```

## Testing

Run the full test suite:

```bash
cd backend
python -m pytest modules/frequency/tests.py -v --tb=short -s
```

Test coverage includes:
- Camera JPEG (consistent compression)
- PNG image
- WEBP image
- Screenshot (uniform low error)
- AI-generated image (uniform low error pattern)
- Edited image
- Large image (4000×4000)
- Small image (10×10)
- Corrupted image
- Exception handling resilience
- Orchestrator & aggregator integration

## Limitations

1. **FFT is a global transform** — it does not localise frequency anomalies
   to specific image regions. Localised manipulation detection requires
   windowed or multi-scale approaches (e.g., Short-Time Fourier Transform or
   wavelets), which are not implemented in this module.

2. **Grayscale processing** — colour-channel-specific frequency anomalies
   are not detected. A synthetic blend in one colour channel may not be
   visible in the grayscale spectrum.

3. **Hann windowing** — applied by default to reduce spectral leakage, but
   this can attenuate genuine edge information at image borders.

4. **Downsampling for large images** — images larger than 1024×1024 are
   downsampled before FFT for performance, which can attenuate high-frequency
   detail.

5. **Not a definitive authenticity detector** — frequency analysis is one
   forensic signal. Natural images can exhibit unusual frequency
   characteristics, and some AI-generated images can exhibit natural-like
   spectra. Frequency Analysis should always be combined with other forensic
   modules (Metadata Analysis, Error Level Analysis) for a comprehensive
   assessment.

6. **Periodic textures** — natural images with strong periodic patterns
   (e.g., fences, window blinds) can produce frequency peaks that may be
   misidentified as suspicious.
