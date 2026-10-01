# VeritasX Enterprise Frequency Analysis Module

## Role

You are a Senior Computer Vision Engineer, Digital Image Forensics Engineer, Signal Processing Engineer, Python Backend Architect, and Software Engineer.

You are continuing the existing VeritasX project.

The project is already partially completed.

The following modules already exist and are fully working:

- Backend Orchestrator
- Dispatcher
- Executor
- Aggregator
- Metadata Analysis
- Error Level Analysis (ELA)
- Frontend Integration

DO NOT rewrite existing modules.

DO NOT redesign the architecture.

Continue from the current project state.

---

# Objective

Implement a production-ready Frequency Analysis module based on Fast Fourier Transform (FFT).

This module should analyze the frequency-domain characteristics of an uploaded image and provide forensic evidence.

It must integrate seamlessly into the existing VeritasX architecture.

---

# Before Writing Code

First inspect the project.

Read and understand:

- BaseForensicModule
- MetadataAnalysisModule
- ErrorLevelAnalysisModule
- ModuleResult
- Dispatcher
- Executor
- Aggregator
- Schemas
- Frontend architecture

Reuse the existing architecture.

Do NOT create a different coding style.

---

# Folder Structure

Create or complete:

backend/modules/frequency/

- __init__.py
- module.py
- processor.py
- analyzer.py
- scorer.py
- visualization.py
- constants.py
- models.py
- utils.py
- tests.py
- README.md

---

# Architecture

Follow:

- SOLID Principles
- Clean Architecture
- Dependency Injection
- Async compatible implementation
- Strong type hints
- Pydantic v2
- Structured logging
- Production-quality exception handling

---

# Frequency Analysis Algorithm

Implement a deterministic FFT-based forensic analysis.

The pipeline should include:

1. Decode image.
2. Convert to grayscale.
3. Apply optional windowing (e.g., Hann window) if appropriate.
4. Compute a 2D Fast Fourier Transform (FFT).
5. Shift the zero-frequency component to the center.
6. Compute the magnitude spectrum using logarithmic scaling.
7. Normalize the spectrum for visualization.
8. Calculate frequency-domain statistics.

Do not use placeholder logic.

---

# Frequency Metrics

Calculate meaningful, reproducible metrics such as:

- Low-frequency energy
- High-frequency energy
- Energy ratio
- Mean spectral magnitude
- Standard deviation
- Radial energy distribution
- Horizontal/vertical frequency balance
- Spectral entropy
- Dominant frequency peaks (if applicable)

Document the formulas used.

---

# Artifact Analysis

Analyze the spectrum for measurable patterns such as:

- Unusual periodic structures
- Checkerboard-like frequency patterns
- Aliasing artifacts
- High-frequency anomalies
- Spectral symmetry
- Banding
- Ringing artifacts

These observations must be based on measurable characteristics.

Do not make unsupported assumptions.

---

# Visualization

Generate a normalized FFT magnitude visualization.

Return it in the same manner used by the ELA module (e.g., Base64, bytes, or relative path).

The visualization should be suitable for display in the existing frontend.

---

# Observations

Produce observations with the following structure:

- title
- description
- severity
- confidence

Examples include:

- High-frequency content is unusually concentrated.
- Spectrum appears balanced.
- Periodic components detected.
- No strong periodic artifacts observed.

Avoid definitive statements such as "This image is AI-generated."

---

# Scoring

Implement a Frequency Analysis score.

Return:

- frequency_score
- confidence_score

The score should summarize the frequency-domain findings only.

Do not interpret it as a final authenticity score.

---

# Module Output

Return the existing ModuleResult format already used in the project.

Do not introduce new response schemas.

---

# Frontend Integration

Add a new forensic card:

Frequency Analysis

The design must match:

- Metadata Analysis
- Error Level Analysis

When expanded, display:

- Frequency Assessment Summary
- Frequency Score
- Confidence
- FFT Magnitude Spectrum
- Frequency Metrics
- Observations
- Processing Time

Use existing UI components wherever possible.

---

# Aggregation

Update the Aggregator to include:

Metadata Analysis

+

Error Level Analysis

+

Frequency Analysis

The aggregation should clearly state that only the implemented modules contribute to the current assessment.

Do not present a definitive AI-generated or real verdict based on Frequency Analysis alone.

---

# Performance

Optimize for speed.

Avoid unnecessary image copies.

Use vectorized NumPy/OpenCV operations where appropriate.

Reuse decoded image data when possible.

Do not change the output format.

---

# Testing

Verify with:

- Camera JPEG
- PNG
- WEBP
- Screenshot
- AI-generated image
- Edited image
- Large image
- Small image
- Corrupted image

Ensure:

- Backend works
- Frontend works
- Orchestrator integration
- Aggregator integration
- No import errors
- No API errors
- No React errors

Automatically fix any safe issues.

---

# Documentation

Create README.md including:

- Overview
- Theory of FFT-based frequency analysis
- Architecture
- Folder structure
- Metrics
- Observations
- API usage
- Testing
- Limitations

Clearly explain that Frequency Analysis is one forensic signal and is not sufficient on its own to determine image authenticity.

---

# Final Review

Before finishing:

Review the complete implementation.

Fix:

- unused imports
- dead code
- duplicate logic
- typing issues
- lint issues
- async issues
- logging issues
- exception handling
- architecture inconsistencies

Do not modify unrelated forensic modules.

---

# Final Deliverables

Provide:

1. Files created
2. Files modified
3. Architecture summary
4. Frequency analysis algorithm explanation
5. Metrics explanation
6. Test results
7. Verification summary
8. Remaining TODOs
9. Confirmation that the project is ready for localhost testing

Most importantly:

Continue the existing project.

Do NOT start from scratch.

Do NOT replace completed work.

Preserve the current architecture and leave the project in a fully working state.