# DragMeToLabel Domain Context & Glossary

This glossary defines the domain vocabulary and conceptual data model of **DragMeToLabel**, a web-based computer vision application designed for sales representatives to replace architectural surfaces in room photos in real time.

---

## Domain Vocabulary

### Surface Geometry & Presets

**Preset**:
A predefined 2.5D architectural surface template (e.g. `floor`, `ceiling`, `corner_bath`, `alcove_bath`, `cali_bath`) defining default polygon vertices, interconnected quadrilateral planes, and perspective constraints for common room geometries.
_Avoid_: layout template, template, macro, wireframe.

**Plane**:
A single quadrilateral surface component (4 ordered vertices: Top-Left, Top-Right, Bottom-Right, Bottom-Left) within a Preset. Each plane represents an independent physical surface (e.g. `back_wall`, `left_wall`, `right_wall`, `floor_plane`, `tub_apron`) onto which a distinct material texture can be projected.
_Avoid_: quad, polygon (when referring to an architectural facet), shape, bounding box.

**Control Point (Vertex)**:
A 2D coordinate $(x, y)$ in image space representing an editable vertex of a Plane. Draggable via mouse or touch input to align the virtual plane with the actual physical boundaries in the room photo.
_Avoid_: corner, anchor point, node, marker.

**Shared Vertex**:
A Control Point that is referenced by more than one adjacent Plane within the same Preset (e.g., the intersection between the back wall and left wall in an alcove bath). Moving a shared vertex updates all connected planes simultaneously to preserve topological continuity.
_Avoid_: joined point, common point, corner pin.

---

### Computer Vision & Rendering Engine

**Homography (Perspective Transformation)**:
A $3 \times 3$ projective transformation matrix computed using OpenCV (`cv2.getPerspectiveTransform`) that maps a canonical rectangular material texture $([0, 0], [W, 0], [W, H], [0, H])$ onto an arbitrary convex quadrilateral defined by 4 Control Points. Applied to pixel data via `cv2.warpPerspective`.
_Avoid_: 2D affine transform, skew, distortion, mapping.

**Lighting Engine**:
The image processing pipeline that extracts local luminance and shading gradients from the original room photo (in LAB or grayscale color space) and blends them onto the warped material texture to realistically preserve shadows, highlights, and ambient illumination.
_Avoid_: filter, shader, brightness adjuster.

**Luminance Extraction**:
Calculating the relative brightness channel of the background image across the bounding polygon of a Plane to modulate the material's diffuse color without washing out texture details.
_Avoid_: grayscale conversion, ambient map.

**Material**:
A surface texture definition applied to a Plane. Can be loaded from an image asset or generated procedurally (e.g., `oak_hardwood`, `carrara_marble`, `slate_tile`, `herringbone`, `subway_tile`). Materials include properties such as repeat scale, surface roughness, and metallic sheen.
_Avoid_: skin, paint, wallpaper, swatch (the swatch is the UI icon, not the texture).

**Renderer**:
The end-to-end composite pipeline (`backend/app/cv/renderer.py`) that takes a room photo, a list of Planes with active Control Points, and their selected Materials, and produces the final composite image as a high-quality JPEG/PNG or base64 data URI.
_Avoid_: drawing canvas, graphics engine.

---

### User Interface & Interaction

**Touch Loupe**:
A floating high-magnification lens widget that appears above the user's fingertip or cursor during drag operations, displaying a zoomed-in view of the canvas crosshairs and the exact image pixels beneath the active Control Point.
_Avoid_: magnifier, zoom tool, bubble lens.

**Whole-Polygon Drag**:
An interaction mode allowing the user to translate all vertices of a Plane or an entire Preset across the canvas simultaneously without altering their relative proportions or angles.
_Avoid_: group move, pan polygon, batch shift.

**Comparison Slider**:
An interactive split-screen divider overlaid on the canvas that allows users and clients to swipe horizontally between the original unmodified room photo and the newly rendered material replacement.
_Avoid_: before/after divider, split view, swipe bar.

---

### Data Interoperability & Export

**Labelme Bridge**:
The headless serialization and conversion module (`backend/app/core/labelme_bridge.py`) that exports DragMeToLabel surface geometry into standard Labelme 5.x JSON format (`version`, `flags`, `shapes`, `imagePath`, `imageData`).
_Avoid_: JSON exporter, file converter, serializer.

**Labelme Shape**:
A single polygon dictionary within a standard Labelme JSON file containing `label`, `points`, `group_id`, `description`, `shape_type="polygon"`, and `flags`.
_Avoid_: annotation entry, shape object.

---

## Example Architecture Flow

```
[Sales Rep / Tablet Browser]
        │
        ▼ (1) Drag Control Points on Canvas with Touch Loupe
[Interactive Frontend UI]
        │
        ▼ (2) POST /api/v1/preview (image_b64, planes, materials)
[FastAPI REST Backend]
        │
        ├──► (3) Homography Matrix Calculation (cv2.getPerspectiveTransform)
        ├──► (4) Texture Warping (cv2.warpPerspective)
        ├──► (5) Lighting & Shadow Extraction (LAB L-channel blending)
        └──► (6) Alpha Mask Composite
        │
        ▼ (7) Base64 Preview Response
[Canvas Comparison Slider Display]
```
