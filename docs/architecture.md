# DragMeToLabel System Architecture

This document describes the software architecture, data flow, and rendering pipeline of **DragMeToLabel**.

---

## 1. High-Level System Architecture

DragMeToLabel is architected as a lightweight, high-performance web application designed for field sales reps on mobile tablets and laptops. The frontend is a responsive single-page web visualizer that communicates with a FastAPI and OpenCV backend.

```mermaid
graph TD
    subgraph Client ["Client Browser (Tablet / Desktop)"]
        UI[Interactive UI Controls]
        Canvas[HTML5 Canvas Viewport]
        Loupe[Touch Loupe Magnifier]
        Slider[Comparison Slider]
        State[Client State & Preset Store]
    end

    subgraph Backend ["FastAPI REST Backend (backend/app)"]
        API[API Router /api/v1]
        Schemas[Pydantic Geometry Schemas]
        Presets[2.5D Architectural Presets]
        Bridge[Labelme 5.x Interop Bridge]
    end

    subgraph CVEngine ["Computer Vision Engine (backend/app/cv)"]
        Homo[Homography Engine<br/>cv2.getPerspectiveTransform]
        Mat[Material Catalog & Synthesizer]
        Light[Lighting & Shadow Engine<br/>LAB L-Channel Blending]
        Rend[Composite Renderer Pipeline]
    end

    UI --> State
    Canvas --> Loupe
    Canvas --> Slider
    State -->|Control Points & Materials| Canvas

    Canvas -->|POST /api/v1/preview<br/>(image_b64, planes, materials)| API
    State -->|POST /api/v1/export-labelme| API

    API --> Schemas
    API --> Rend
    API --> Bridge

    Rend --> Homo
    Rend --> Mat
    Rend --> Light

    Rend -->|Base64 Composite Preview| API
    Bridge -->|Labelme 5.x JSON| API

    API -->|Rendered Preview| Canvas
    API -->|JSON File Download| UI
```

---

## 2. Component Breakdown

### 2.1 Frontend (`frontend/`)
- **HTML5 Canvas Viewport**: Renders the background room photo, interactive polygon planes, editable control point vertices, and selection outlines.
- **Touch Loupe**: Automatically activates during touch/mouse dragging of control points, rendering a $2\times$ magnified circle with crosshairs offset from the user's fingertip for sub-pixel accuracy.
- **Comparison Slider**: Split-screen canvas overlay that allows interactive horizontal wiping between the original room photo and the newly rendered material replacement.
- **Preset & Material Selectors**: Fast preset loading (`floor`, `ceiling`, `corner_bath`, `alcove_bath`, `cali_bath`) and material palette swatches.
- **API Client (`api.js`)**: Asynchronous HTTP client communicating with backend endpoints via `fetch`.

### 2.2 Backend API (`backend/app/api/`)
- `GET /api/v1/presets`: Returns available 2.5D architectural surface presets and default plane vertex configurations.
- `GET /api/v1/materials`: Returns the catalog of available materials, texture styles, and procedural surface options.
- `POST /api/v1/preview`: Processes an uploaded room photo, polygon coordinates, and assigned materials, returning a rendered preview as a base64-encoded image.
- `POST /api/v1/export-labelme`: Converts active 2.5D plane geometries and image metadata into a standard Labelme 5.x JSON file for downstream machine learning datasets.

### 2.3 Computer Vision Engine (`backend/app/cv/`)
- **`homography.py`**: Calculates the $3 \times 3$ perspective transformation matrix between rectangular material textures and arbitrary planar quadrilaterals:
  $$H = \text{cv2.getPerspectiveTransform}(\text{src\_pts}, \text{dst\_pts})$$
  and applies the projective warp via `cv2.warpPerspective`.
- **`materials.py`**: Manages realistic texture assets and procedural pattern generation (wood planks, marble veining, subway tiles, stone slate) with configurable repeat scale.
- **`lighting.py`**: Extracts the luminance channel ($L$) in CIELAB color space from the original image under each polygon plane, calculates local contrast and shading gradients, and blends them onto the warped material to preserve natural ambient lighting, shadows, and specular highlights.
- **`renderer.py`**: Coordinates the multi-plane rendering pipeline, applies anti-aliased polygon masking (`cv2.fillPoly`), and composites the surfaces onto the original room photo.

### 2.4 Core & Interoperability (`backend/app/core/`)
- **`schemas.py`**: Pydantic models enforcing strict validation on 2D coordinates, quadrilateral planes, material assignments, and render requests.
- **`presets.py`**: Standard 2.5D architectural layouts with default normalized vertex coordinates.
- **`labelme_bridge.py`**: Serializes internal plane geometries into standard `shapes` arrays compatible with Labelme 5.x JSON schema.

---

## 3. Real-Time Rendering Pipeline & Data Flow

```
[1. User adjusts Control Point on Canvas]
                     │
                     ▼
[2. Frontend captures normalized quad vertices for each active plane]
                     │
                     ▼
[3. HTTP POST /api/v1/preview]
    Payload: {
      "image_base64": "data:image/jpeg;base64,...",
      "planes": [
        {
          "plane_id": "floor_plane",
          "points": [[x0, y0], [x1, y1], [x2, y2], [x3, y3]],
          "material_id": "oak_hardwood"
        }
      ]
    }
                     │
                     ▼
[4. Backend decodes image_base64 to OpenCV BGR numpy array]
                     │
                     ▼
[5. For each plane in render request:]
    ├── a. Load / generate material texture (W x H)
    ├── b. Compute 3x3 Homography H from [0,0..W,H] to Quad Points
    ├── c. Warp material texture into target quadrilateral
    ├── d. Extract LAB luminance from original image within Quad mask
    ├── e. Apply lighting & shadow transfer onto warped texture
    └── f. Alpha blend shaded material into composite image buffer
                     │
                     ▼
[6. Encode composite BGR numpy array to JPEG / PNG base64]
                     │
                     ▼
[7. Return JSON response: {"preview_base64": "data:image/jpeg;base64,..."}]
                     │
                     ▼
[8. Frontend Canvas updates rendered overlay & comparison slider]
```

---

## 4. Labelme 5.x Interoperability Flow

DragMeToLabel maintains 100% downstream compatibility with the open-source **Labelme 5.x** JSON format:

```json
{
  "version": "5.5.0",
  "flags": {},
  "shapes": [
    {
      "label": "floor",
      "points": [[120.5, 450.0], [680.0, 440.5], [780.0, 710.0], [40.0, 710.0]],
      "group_id": 1,
      "description": "material:oak_hardwood",
      "shape_type": "polygon",
      "flags": {}
    }
  ],
  "imagePath": "room_sample.jpg",
  "imageData": null,
  "imageHeight": 720,
  "imageWidth": 1280
}
```

This headless bridge allows sales annotations collected in the field to be directly imported into CV training pipelines for semantic segmentation, depth estimation, or automated plane extraction without format conversion.

---

## 5. Performance & Reliability Guarantees

- **Low-Latency Rendering**: Sub-100ms response time on typical $1920 \times 1080$ room photos using native OpenCV C++ bindings.
- **Headless Architecture**: Zero dependency on desktop GUI frameworks (PySide6 / PyQt5 / X11 / Wayland), ensuring reliable deployment across cloud containers, Linux servers, and mobile web clients.
- **Strict Data Validation**: Pydantic models validate all geometric input to prevent singular homography matrices or degenerate polygons before reaching OpenCV.
