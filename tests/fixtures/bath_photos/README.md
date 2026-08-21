# Bath Photo Test Library

This directory contains test photos for automated CV solver benchmarks and manual frontend upload validation.

---

## 1. How to Add Photos

Drop any bathroom photo into this directory:
- Supported formats: `.jpg`, `.jpeg`, `.png`
- Example: `01_master_bath.jpg`

---

## 2. Optional Ground-Truth Metadata (`.json`)

To benchmark detection accuracy against manual annotations, save a matching `.json` file alongside the image with the same base name (e.g., `01_master_bath.json`):

```json
{
  "preset_id": "alcove_bath",
  "points": [
    [32.2, 119.2],
    [277.9, 331.2],
    [997.2, 326.4],
    [1214.0, 116.0],
    [232.9, 1551.5],
    [428.8, 1191.8],
    [868.8, 1188.6],
    [1056.6, 1556.3]
  ]
}
```

---

## 3. How to Test

### In the Web Frontend:
1. Open the web application in your browser (`http://localhost:8000`).
2. Click the **"Upload Photo"** button in the top navigation bar.
3. Browse to `tests/fixtures/bath_photos/` and select any photo to test interactive auto-fit, drag snapping, and preview rendering.

### In Automated Backend Tests:
Run pytest to automatically execute the benchmark suite across all images in this folder:
```bash
.venv/bin/pytest -v tests/test_solvers.py
```
