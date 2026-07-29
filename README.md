# VeritasX — AI Media Forensic & Image Detection Platform

VeritasX is an enterprise-grade AI-generated image detection and media forensic platform. It combines a production-ready Python FastAPI backend orchestrator with a futuristic React frontend to perform multi-module deep learning and metadata forensic analysis.

---

## 📂 Project Structure

```
VeritasX/
├── backend/                        # Python FastAPI Backend Orchestrator
│   ├── aggregation/                # Forensic Result Aggregation Engine
│   │   └── aggregator.py           # Weighted scoring, confidence & verdict synthesis
│   ├── modules/                    # Modular Forensic Engines
│   │   ├── base.py                 # Exception-safe BaseForensicModule template
│   │   ├── metadata/               # 4-Layer Metadata Analysis Engine
│   │   │   ├── extractor.py        # Pillow, piexif & exifread binary parser
│   │   │   ├── validator.py        # Tag integrity & date/GPS validator
│   │   │   ├── analyzer.py         # Rule-based AI/editing signature detector
│   │   │   ├── scorer.py           # Dual-score (trustworthiness & confidence) math
│   │   │   ├── models.py           # Pydantic schemas & data structures
│   │   │   └── utils.py            # UTF-8 sanitization & hash calculation
│   │   ├── ela/                    # Error Level Analysis module
│   │   ├── frequency/              # Frequency Domain (FFT/DCT) analysis
│   │   ├── sensor_noise/           # PRNU & Sensor Noise Analysis
│   │   ├── artifacts/              # GAN/Diffusion Compression Artifacts
│   │   ├── adversarial/            # Adversarial Perturbation Detection
│   │   └── reverse_search/         # Web Reverse Search & Provenance Module
│   ├── orchestrator/               # Pipeline Execution & Module Management
│   │   ├── dispatcher.py           # Dynamic module registration & lifecycle
│   │   ├── executor.py             # Concurrent asyncio module executor
│   │   └── orchestrator.py         # Central orchestrator pipeline
│   ├── schemas/                    # System Pydantic Models & API Contracts
│   ├── services/                   # Application Service Layer & Dependency Injection
│   ├── config.py                   # System Configuration & Upload Limits
│   ├── main.py                     # FastAPI Entrypoint Server
│   └── test_orchestrator.py        # Orchestrator & Resiliency Verification Suite
│
├── frontend/                       # Frontend Web Application (React + Vite + TS)
│   ├── src/
│   │   ├── components/             # Cyber UI Components & Workspace Sections
│   │   │   └── sections/
│   │   │       ├── BatchDetectionWorkspace.tsx  # Multi-file drop zone & live proxy fallback
│   │   │       └── MetadataAnalysisPanel.tsx    # Forensic EXIF & observation inspector
│   │   ├── index.html              # App Entrypoint
│   │   └── tailwind.config.js      # Cyber Design System Theme Tokens
│   ├── vite.config.ts              # Vite Config & API Reverse Proxy
│   └── package.json                # Dependencies & Scripts
│
└── README.md                       # System Documentation
```

---

## 🚀 Key Features & Architectural Highlights

### 🛡️ Production-Ready Backend Orchestrator
- **Asynchronous Concurrent Execution**: Dispatches enabled forensic detection modules in parallel using Python `asyncio`.
- **Fault-Tolerant Module Isolation**: Individual module errors are isolated—pipeline completes smoothly even if a specific engine fails.
- **Dynamic Module Dispatcher**: Extensible Open/Closed architecture allowing seamless plug-and-play registration of new forensic engines.
- **Robust UTF-8 Sanitization**: Guaranteed safe serialization of non-standard binary EXIF tags (surrogate-free UTF-8 normalization).

### 🔍 4-Layer Metadata Analysis Engine
1. **Extraction Layer**: Single-pass image decode using Pillow, `piexif`, `exifread`, SHA-256/MD5 hashing, and magic byte MIME identification.
2. **Validation Layer**: Identifies corrupt EXIF headers, invalid GPS ranges, future timestamps, and unmapped tags.
3. **Observation Analyzer**: Rule-based detection of:
   - **AI Generators**: *Midjourney*, *Stable Diffusion*, *Automatic1111*, *ComfyUI*, *InvokeAI*.
   - **Editing Suites**: *Adobe Photoshop*, *Lightroom*, *GIMP*, *Canva*.
   - **Screenshot Utilities**: *Windows Snipping Tool*, *ShareX*, *Lightshot*.
   - **Capture Hardware**: Mobile Camera vs. DSLR / Mirrorless Professional Camera classification.
4. **Scoring Engine**: Dual-score calculation producing a **Trustworthiness Score** ($0.0 - 1.0$) and a **Confidence Score** ($0.0 - 1.0$).

### 🎨 Futuristic Cyber Interface
- **Cyberpunk Dark Theme**: Signature cyan glow (`#00E5FF`), 20% transparent glassmorphism panels, and smooth Lenis scrolling.
- **Batch Media Workspace**: Drag-and-drop analysis workspace supporting simultaneous media scans with real-time API fallback resiliency.
- **Detailed Forensic Inspector**: Interactive breakdown of metadata observations, EXIF field tables, and severity alerts.

---

## ⚡ API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/analyze` | Primary endpoint for multi-module media forensic analysis |
| `GET` | `/api/v1/health` | System health status & list of currently active forensic modules |
| `GET` | `/docs` | Interactive Swagger / OpenAPI documentation |

---

## 📦 Getting Started

### Prerequisites
- Python `3.10+`
- Node.js `18+` & `npm`

### 1. Backend Setup

```bash
# Navigate to workspace root
cd VeritasX

# Install Python dependencies
pip install -r backend/requirements.txt

# Run backend test suite
$env:PYTHONPATH="."; python backend/test_orchestrator.py
$env:PYTHONPATH="."; python backend/modules/metadata/tests.py

# Start FastAPI server (runs on http://127.0.0.1:8000)
$env:PYTHONPATH="."; python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server (runs on http://localhost:3000)
npm run dev
```

---

## 📜 License

MIT License &copy; VeritasX Media Forensics Inc.
