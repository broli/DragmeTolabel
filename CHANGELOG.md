# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-20

### Added

- **DragMeToLabel Initial Alpha Release**: A specialized web application designed for sales representatives and field estimators to replace architectural surfaces in room photos in real time.
- **2.5D Architectural Presets**: Built-in surface templates with topological quad constraints for `floor`, `ceiling`, `corner_bath`, `alcove_bath`, and `cali_bath`.
- **OpenCV Homography Engine**: Real-time perspective projection (`cv2.getPerspectiveTransform` and `cv2.warpPerspective`) that maps rectangular material textures to arbitrary quadrilateral planes.
- **Lighting & Shadow Preservation Engine**: Luminance extraction and channel blending in LAB color space to preserve ambient lighting, gradients, shadows, and specular highlights on replaced materials.
- **Extensible Material Catalog**: High-resolution material textures and procedural generators for oak hardwood, carrara marble, slate tile, herringbone, subway tile, and custom patterns.
- **Mobile & Tablet Touch Loupe**: High-precision floating magnifier widget providing sub-pixel accuracy when positioning control points on touch devices.
- **Whole-Polygon & Multi-Plane Translation**: Smooth multi-point translation mode allowing sales reps to position entire presets simultaneously.
- **Interactive Comparison Slider**: Dynamic split-screen before/after slider on the HTML5 canvas for immediate client visualization.
- **Labelme 5.x Interoperability Bridge**: Headless export tool converting active surface plane geometries into standard Labelme JSON annotation format (`shapes`, `points`, `imagePath`, `imageData`).
- **FastAPI REST Service**: Robust API endpoints (`/api/v1/presets`, `/api/v1/materials`, `/api/v1/preview`, `/api/v1/export-labelme`) with static asset delivery.
- **Modern Packaging & CI Workflow**: Streamlined `pyproject.toml` (PEP 621), `Makefile` automation, and GitHub Actions CI matrix testing Python 3.12, 3.13, and 3.14.

---

## Legacy Labelme Archive

*(Historical changelog entries for the upstream desktop Qt tool `labelme` prior to the DragMeToLabel adaptation are preserved in `_legacy_archive/`.)*
