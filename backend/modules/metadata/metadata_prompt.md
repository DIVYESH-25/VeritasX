🚀 Prompt: Build Enterprise Metadata Analysis Module for VeritasX

You are a Senior AI Engineer, Digital Forensics Engineer, and Python Backend Architect.

I am building VeritasX, an enterprise-grade AI Image Forensics platform.

The frontend and backend orchestrator are already implemented.

Today I want to build only the Metadata Analysis module.

Do NOT implement any other forensic modules.

Objective

Build a production-ready, modular, scalable, and extensible Metadata Analysis module that integrates seamlessly with the existing Backend Orchestrator.

The module should extract metadata, validate it, analyze it, generate forensic observations, assign a metadata confidence score, and return a standardized ModuleResult.

The module must be completely offline and must not require external APIs.

Folder Structure

Create:

backend/
└── modules/
    └── metadata/
        ├── __init__.py
        ├── analyzer.py
        ├── extractor.py
        ├── validator.py
        ├── scorer.py
        ├── models.py
        ├── constants.py
        ├── utils.py
        └── tests.py
Design Requirements

Follow:

SOLID Principles
Clean Architecture
Dependency Injection
Repository Pattern where appropriate
Strong typing
Async compatible design
Comprehensive error handling
Structured logging
Production-ready code
Libraries

Use only reliable Python libraries:

Pillow
piexif
exifread
python-magic (if available)
pathlib
os
hashlib
datetime
typing
logging
pydantic v2

Do not use cloud services or external APIs.

Metadata Extraction

Extract every useful field possible.

File Information
filename
extension
MIME type
file size
SHA256 hash
MD5 hash
Image Information
width
height
aspect ratio
color mode
color profile
bit depth
compression type
DPI
EXIF Information

Extract all available EXIF tags including:

Camera Make
Camera Model
Lens
Software
DateTimeOriginal
DateModified
Exposure Time
Aperture
ISO
Flash
Focal Length
White Balance
Orientation
GPS
Artist
Copyright

If EXIF is missing, report that gracefully.

Validation Layer

Create a dedicated validator.

Check:

Corrupted metadata
Missing EXIF
Invalid timestamps
Future timestamps
Impossible dates
Invalid GPS
Empty metadata
Duplicate fields
Unsupported metadata
Broken EXIF

Generate validation issues instead of throwing exceptions.

Metadata Analysis

Create a rule-based analyzer.

Generate observations such as:

Image edited using Photoshop
Exported from GIMP
Exported using Canva
Saved using Stable Diffusion
Saved using Midjourney
Metadata completely removed
Camera information missing
GPS removed
Timestamp mismatch
Screenshot detected (when possible)
Mobile camera image
DSLR image
PNG without EXIF
Metadata inconsistent

Each observation should include:

title
description
severity
confidence
Metadata Scoring

Implement a scoring engine.

Generate:

metadata_score

0.0 → suspicious

1.0 → trustworthy

Also calculate:

confidence_score

using available metadata quality.

Module Output

Return a standardized ModuleResult:

{
  "module": "Metadata Analysis",
  "status": "success",
  "score": 0.82,
  "confidence": 0.91,
  "execution_time_ms": 15,
  "message": "Metadata analysis completed successfully",
  "data": {
    "file": {},
    "image": {},
    "exif": {},
    "validation": {},
    "observations": [],
    "metadata_score": 0.82
  }
}
Error Handling

Never crash.

If extraction fails:

{
  "status":"error",
  "message":"Unable to parse metadata",
  "error_details":"..."
}

The Orchestrator must still continue.

Performance

The module should:

use async-compatible code
minimize memory usage
avoid loading image multiple times
complete in under 100 ms for normal images where practical
Integration

The module must expose:

async def analyze(
    image_bytes: bytes,
    request_id: str
) -> ModuleResult

so the Orchestrator can execute it without modification.

Logging

Log:

Request ID
Extraction time
Validation time
Analysis time
Number of EXIF fields
Number of observations
Errors
Final score
Testing

Create automated tests using:

JPEG with EXIF
JPEG without EXIF
PNG
WEBP
Screenshot
Corrupted image
Large image
Small image

Verify:

metadata extraction
validation
scoring
orchestrator compatibility
error handling
Documentation

Generate:

docstrings
type hints
inline comments where appropriate
README explaining module architecture and extension points
Important

Do not implement AI image detection, deep learning, ELA, frequency analysis, sensor noise analysis, reverse image search, or any other forensic module.

Focus exclusively on delivering a robust, production-ready Metadata Analysis module that plugs into the existing Orchestrator, follows clean architecture, and can be extended later with additional metadata analysis rules without changing its public interface.