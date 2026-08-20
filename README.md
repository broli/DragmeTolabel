<h1 align="center">
  DragMeToLabel
</h1>

<h4 align="center">
  Computer Vision & 2.5D Polygon Surface Replacement Web Application for Sales Representatives
</h4>

<div align="center">
  <a href="https://github.com/broli/DragmeTolabel/actions"><img src="https://img.shields.io/badge/CI-passing-brightgreen.svg" alt="CI"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue.svg" alt="Python Versions"></a>
  <a href="https://github.com/broli/DragmeTolabel"><img src="https://img.shields.io/badge/version-0.2.0--alpha-orange.svg" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0-lightgrey.svg" alt="License"></a>
</div>

<div align="center">
  <a href="#overview"><b>Overview</b></a>
  | <a href="#key-features"><b>Key Features</b></a>
  | <a href="#quickstart"><b>Quickstart</b></a>
  | <a href="#architecture"><b>Architecture</b></a>
  | <a href="#upstream-attribution"><b>Attribution</b></a>
</div>

<br/>

---

## Upstream Attribution & Fork Heritage

> **Note on Upstream Project**:
> **DragMeToLabel** originated as an adaptation and fork inspired by [**labelme**](https://github.com/wkentaro/labelme) (created by [Kentaro Wada](https://github.com/wkentaro) and inspired by MIT CSAIL LabelMe).
>
> While `labelme` is a general-purpose desktop image annotation tool for computer vision datasets, **DragMeToLabel** focuses specifically on in-the-field sales visualization: enabling sales reps on tablets and mobile devices to load room photos, snap 2.5D architectural surface presets (floors, ceilings, bathtubs, walls), adjust vertices with a touch loupe, and generate real-time perspective-correct material replacements with OpenCV homography and shadow preservation.
>
> For users looking for the general-purpose desktop annotation tool with PySide6/Qt or SAM integration, please visit the upstream [labelme repository](https://github.com/wkentaro/labelme) or [labelme.io](https://labelme.io).

---

## Overview

**DragMeToLabel** transforms room photos into interactive sales visualization canvases. Sales representatives can photograph a customer's bathroom, kitchen, or living room, select an architectural preset (e.g. *Floor*, *Alcove Bath*, *Corner Bath*), align surface planes in seconds with precision touch controls, and preview realistic surface material upgrades (hardwood, marble tile, slate, herringbone) rendered with true optical perspective, luminance matching, and shadow preservation.

Annotations can also be exported with one click into standard **Labelme 5.x JSON format** for downstream CV/ML pipelines and automated geometry estimation.

---

## Key Features

- 🎯 **2.5D Architectural Presets**: Instant geometry initialization for common architectural layouts:
  - `floor` (1 plane quad)
  - `ceiling` (1 plane quad)
  - `corner_bath` (2 connected wall quads + floor quad)
  - `alcove_bath` (3 connected wall quads: left, back, right + floor quad)
  - `cali_bath` (3 wall quads + tub deck + apron quads)
- 🔍 **Mobile & Tablet Touch Loupe**: High-precision floating magnifier widget that activates during touch and mouse dragging to ensure pinpoint vertex positioning on small screens.
- 📐 **OpenCV Homography Engine**: Real-time perspective transformations (`cv2.getPerspectiveTransform` + `cv2.warpPerspective`) that warp rectangular material textures directly into arbitrary quadrilaterals.
- 💡 **Lighting & Shadow Preservation**: Advanced luminance extraction and overlay blending that preserves ambient room lighting, shadows, and surface highlights on newly applied materials.
- 🎨 **Extensible Material Catalog**: Realistic high-res textures and procedural patterns (Oak Hardwood, Marble Tile, Slate, Herringbone, Travertine, Matte Paint).
- 🎚️ **Interactive Comparison Slider**: Split-screen before/after slider on the canvas for instant visual proofing with customers.
- 🔄 **Headless Labelme 5.x Bridge**: Seamless bidirectional compatibility with standard Labelme JSON annotation formats (`shapes`, `points`, `imagePath`, `imageData`).

---

## Quickstart

### Prerequisites
- Python 3.12 or newer
- Modern web browser (Chrome, Safari, Edge, Firefox)

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/broli/DragmeTolabel.git
cd DragmeTolabel

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package and dependencies
pip install -e .
```

### 2. Launch Development Server

```bash
# Using Makefile
make dev

# Or directly with uvicorn
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser at **`http://localhost:8000`**.

---

## Development & Testing

```bash
# Run backend pytest suite
make test

# Run linter checks (Ruff)
make lint

# Auto-format codebase
make format

# Full validation (linter + tests)
make check
```

---

## Project Structure

```
DragMeToLabel/
├── backend/
│   └── app/
│       ├── api/               # FastAPI route handlers (/presets, /materials, /preview, /export-labelme)
│       ├── core/              # Geometry schemas, preset definitions, and Labelme bridge
│       ├── cv/                # OpenCV homography, material textures, lighting & rendering pipeline
│       └── main.py            # FastAPI application entrypoint & static file mounts
├── frontend/                  # Interactive HTML5/CSS3/ES6 web visualizer
│   ├── index.html             # Main visualizer page
│   ├── css/style.css          # Responsive design & touch loupe styles
│   └── js/                    # Canvas renderer, touch loupe, slider, and API client
├── tests/                     # Pytest suite
│   └── test_backend.py        # CV, homography, renderer, preset, and API tests
├── docs/                      # Documentation and architecture guides
│   ├── architecture.md        # Detailed system data flow and rendering architecture
│   └── agents/                # LLM / agent guidance
├── pyproject.toml             # Modern PEP 621 packaging & pytest/ruff config
├── Makefile                   # Convenient dev, test, lint, and format commands
├── CONTEXT.md                 # Domain glossary and language definitions
├── AGENTS.md                  # Development workflows & branching rules
└── CHANGELOG.md               # Version history (Keep a Changelog)
```

---

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0), carrying forward the open-source legacy of `labelme`. See [LICENSE](LICENSE) for details.
