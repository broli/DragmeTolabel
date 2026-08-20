"""
Unit and integration tests for DragmeTolabel Backend & OpenCV Renderer.
"""

import numpy as np

from backend.app.core.labelme_bridge import export_to_labelme_json
from backend.app.core.presets import get_all_presets, get_preset_by_id
from backend.app.core.schemas import PreviewRequest
from backend.app.cv.materials import get_material_texture, get_materials_catalog
from backend.app.cv.renderer import decode_base64_image, encode_image_base64, render_preview


def test_presets_structure():
    presets = get_all_presets()
    assert len(presets) == 5

    floor = get_preset_by_id("floor")
    assert floor is not None
    assert floor.point_count == 4
    assert floor.line_count == 4
    assert len(floor.planes) == 1

    ceiling = get_preset_by_id("ceiling")
    assert ceiling is not None
    assert ceiling.point_count == 4
    assert ceiling.line_count == 4

    corner = get_preset_by_id("corner_bath")
    assert corner is not None
    assert corner.point_count == 6
    assert corner.line_count == 7
    assert len(corner.planes) == 2

    alcove = get_preset_by_id("alcove_bath")
    assert alcove is not None
    assert alcove.point_count == 8
    assert alcove.line_count == 10
    assert len(alcove.planes) == 3

    cali = get_preset_by_id("cali_bath")
    assert cali is not None
    assert cali.enabled is False


def test_materials_generation():
    catalog = get_materials_catalog()
    assert len(catalog) >= 5

    texture = get_material_texture("carrara_marble")
    assert texture is not None
    assert texture.shape[0] > 0 and texture.shape[1] > 0


def test_renderer_floor_preview():
    # Create test image (600x800 white room with gradient)
    h, w = 600, 800
    test_img = np.full((h, w, 3), 200, dtype=np.uint8)
    # Add a shadow gradient
    for y in range(h):
        test_img[y, :] = np.clip(test_img[y, :] - int(y * 0.1), 30, 255)

    img_b64 = encode_image_base64(test_img)

    floor_preset = get_preset_by_id("floor")
    # Convert normalized points to pixel coordinates
    pixel_points = [[pt[0] * w, pt[1] * h] for pt in floor_preset.default_normalized_points]

    req = PreviewRequest(
        image_base64=img_b64,
        preset_id="floor",
        points=pixel_points,
        material_id="carrara_marble",
        lighting_intensity=0.85,
        tile_scale=1.0,
    )

    res = render_preview(req)
    assert res.success is True
    assert res.planes_rendered == 1
    assert len(res.processed_image_base64) > 100

    # Verify resulting image can be decoded
    decoded = decode_base64_image(res.processed_image_base64)
    assert decoded.shape == (h, w, 3)


def test_renderer_corner_bath_multi_plane():
    h, w = 600, 800
    test_img = np.full((h, w, 3), 220, dtype=np.uint8)
    img_b64 = encode_image_base64(test_img)

    corner_preset = get_preset_by_id("corner_bath")
    pixel_points = [[pt[0] * w, pt[1] * h] for pt in corner_preset.default_normalized_points]

    req = PreviewRequest(
        image_base64=img_b64,
        preset_id="corner_bath",
        points=pixel_points,
        material_id="modern_subway_tile",
        lighting_intensity=0.9,
        tile_scale=2.0,
    )

    res = render_preview(req)
    assert res.success is True
    assert res.planes_rendered == 2


def test_renderer_alcove_bath_multi_plane():
    h, w = 600, 800
    test_img = np.full((h, w, 3), 220, dtype=np.uint8)
    img_b64 = encode_image_base64(test_img)

    alcove_preset = get_preset_by_id("alcove_bath")
    pixel_points = [[pt[0] * w, pt[1] * h] for pt in alcove_preset.default_normalized_points]

    req = PreviewRequest(
        image_base64=img_b64,
        preset_id="alcove_bath",
        points=pixel_points,
        material_id="slate_grey_tile",
        lighting_intensity=0.8,
        tile_scale=1.5,
    )

    res = render_preview(req)
    assert res.success is True
    assert res.planes_rendered == 3


def test_labelme_export():
    alcove_preset = get_preset_by_id("alcove_bath")
    pixel_points = [[pt[0] * 800, pt[1] * 600] for pt in alcove_preset.default_normalized_points]

    json_dict = export_to_labelme_json(
        preset_id="alcove_bath",
        points=pixel_points,
        image_width=800,
        image_height=600,
    )

    assert json_dict["version"] == "5.5.0"
    assert len(json_dict["shapes"]) == 3
    assert json_dict["shapes"][0]["shape_type"] == "polygon"
    assert json_dict["imageWidth"] == 800
    assert json_dict["imageHeight"] == 600


def test_api_endpoints():
    from fastapi.testclient import TestClient

    from backend.app.main import app

    client = TestClient(app)

    # Test presets endpoint
    resp = client.get("/api/v1/presets")
    assert resp.status_code == 200
    presets = resp.json()
    assert len(presets) == 5

    # Test materials endpoint
    resp = client.get("/api/v1/materials")
    assert resp.status_code == 200
    materials = resp.json()
    assert len(materials) >= 5

    # Test preview endpoint
    test_img = np.full((300, 400, 3), 200, dtype=np.uint8)
    img_b64 = encode_image_base64(test_img)
    preview_req = {
        "image_base64": img_b64,
        "preset_id": "floor",
        "points": [[40, 200], [360, 200], [380, 280], [20, 280]],
        "material_id": "carrara_marble",
        "lighting_intensity": 0.85,
        "tile_scale": 1.0,
    }
    resp = client.post("/api/v1/preview", json=preview_req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["planes_rendered"] == 1

    # Test export labelme endpoint (supports both /export and /export-labelme)
    export_req = {
        "image_base64": img_b64,
        "preset_id": "floor",
        "points": [[40, 200], [360, 200], [380, 280], [20, 280]],
    }
    resp = client.post("/api/v1/export-labelme", json=export_req)
    assert resp.status_code == 200
    assert "shapes" in resp.json()

    resp_alias = client.post("/api/v1/export", json=export_req)
    assert resp_alias.status_code == 200
    assert "shapes" in resp_alias.json()

    # Test frontend root endpoint
    resp = client.get("/")
    assert resp.status_code == 200
