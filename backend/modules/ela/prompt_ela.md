🚀 Prompt — Build Enterprise Error Level Analysis (ELA) Module for VeritasX

You are a Senior Digital Forensics Engineer, AI Engineer, Computer Vision Engineer, and Python Backend Architect.

You are continuing development of an existing enterprise AI Image Forensics platform called VeritasX.

Do NOT start from scratch.

The project already contains:

Frontend
FastAPI backend
Orchestrator
Dispatcher
Executor
Aggregator
Base forensic module
Metadata Analysis module (fully implemented and tested)

Your first task is to inspect the existing project architecture and understand how the Metadata Analysis module is implemented.

Use the Metadata Analysis module as the architectural reference.

Objective

Build a production-ready Error Level Analysis (ELA) module.

This module must integrate seamlessly into the existing orchestrator and follow exactly the same architecture as the Metadata Analysis module.

Do NOT modify the Metadata Analysis implementation except when absolutely necessary for compatibility.

Before Writing Code

First:

Scan the project.
Understand the existing architecture.
Understand BaseForensicModule.
Understand ModuleResult.
Understand Dispatcher.
Understand Aggregator.
Understand MetadataAnalysisModule.
Reuse existing patterns.

Only then begin implementation.

Folder Structure

Create:

backend/
└── modules/
    └── ela/
        ├── __init__.py
        ├── module.py
        ├── analyzer.py
        ├── processor.py
        ├── scorer.py
        ├── models.py
        ├── constants.py
        ├── utils.py
        ├── visualization.py
        ├── tests.py
        └── README.md
Architecture Requirements

Follow:

SOLID Principles
Clean Architecture
Dependency Injection
Async compatible design
Strong typing
Pydantic v2
Production-ready logging
Comprehensive exception handling
Modular design
Libraries

Use only:

OpenCV
NumPy
Pillow
Pydantic
asyncio
logging
pathlib
typing

Do not introduce unnecessary dependencies.

Error Level Analysis Algorithm

Implement the standard ELA algorithm.

Steps:

Decode image.
Convert to RGB.
Save temporary JPEG at configurable quality (default 90).
Reload compressed image.
Compute absolute pixel difference.
Normalize differences.
Enhance visibility.
Produce ELA image.
Remove temporary files.
Return result.

The implementation should be deterministic and configurable.

Configuration

Support configurable JPEG quality.

Example:

ELA_JPEG_QUALITY = 90

Future configuration should allow

75
85
90
95

without code changes.

Metrics

Calculate:

Average Error
Maximum Error
Minimum Error
Standard Deviation
High Error Pixel Count
Percentage High Error Pixels
Mean Brightness
Dynamic Range
Suspicious Region Detection

Identify areas with unusually high compression differences.

Return:

Bounding boxes

Coordinates

Area

Intensity

Prepare the structure even if future visualization becomes more advanced.

Visualization

Generate:

ELA image

Store it temporarily or in memory.

Return:

Base64

or

bytes

or

relative file path

Choose the architecture already used in the project.

Forensic Observations

Generate observations such as:

Uniform compression
Localized recompression
Edited region suspected
Heavy JPEG artifacts
Multiple compression signatures
Consistent camera compression
Screenshot characteristics
Possible synthetic generation indicators (ELA only)

Each observation must include:

title
description
severity
confidence
Scoring

Implement an ELA scoring engine.

Return:

ela_score

0.0 = highly suspicious

1.0 = consistent compression

Also calculate:

confidence_score
Output

Return standard ModuleResult.

Example:

{
  "module": "Error Level Analysis",
  "status": "success",
  "score": 0.74,
  "confidence": 0.88,
  "execution_time_ms": 42,
  "message": "ELA completed successfully",
  "data": {
    "ela_score": 0.74,
    "metrics": {},
    "observations": [],
    "ela_image": "...",
    "suspicious_regions": []
  }
}
Frontend Integration

Integrate the module into the existing website.

When an image is uploaded:

Run:

Metadata Analysis

↓

Error Level Analysis

Do not run other modules.

Frontend UI

Create a professional forensic report.

Display:

Metadata Analysis

(Already implemented)

Error Level Analysis

Show:

ELA image
JPEG Quality
Average Error
Maximum Error
Standard Deviation
ELA Score
Confidence
Suspicious Regions
Observations

Use:

progress bars
badges
collapsible sections
smooth animations

Match the existing VeritasX design.

Aggregation

Update the Aggregator so it combines only:

Metadata

ELA

Generate:

Current Assessment

Display a clear disclaimer:

This assessment is currently based only on Metadata Analysis and Error Level Analysis. Additional forensic modules will be incorporated in future versions.

Do not present this as a final AI detection result.

Testing

Run automated tests using:

Camera JPEG
PNG
Screenshot
AI-generated image
Edited JPEG
Multiple JPEG quality levels
Corrupted file
Large image
Small image

Verify:

Orchestrator compatibility
Aggregator compatibility
Frontend rendering
API responses
Exception handling

Automatically fix any discovered issues.

Code Review

Before finishing:

Perform a complete backend review.

Fix:

circular imports
unused imports
duplicate logic
inconsistent typing
dead code
lint issues
async issues
logging issues
exception handling
Pydantic inconsistencies
Important Rules
Do NOT rewrite Metadata Analysis.
Do NOT implement Frequency Analysis.
Do NOT implement Sensor Noise Analysis.
Do NOT implement Reverse Image Search.
Do NOT implement Visual Artifact Detection.
Do NOT implement Adversarial Noise Detection.
Build only the ELA module.
Reuse the existing project architecture.
Preserve backward compatibility.
Final Deliverables

At the end provide:

Files created
Files modified
Architecture decisions
ELA algorithm explanation
API changes
Frontend changes
Test results
Remaining TODOs
Recommendations for the next forensic module

Do not stop after generating code. Verify the implementation, fix any issues found, and leave the project in a working state ready for localhost testing.