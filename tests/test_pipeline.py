"""
Unit tests for the modular 4-Stage Bottom-Up (Floor & Tub-First) Computer Vision Pipeline.
"""

from __future__ import annotations

from backend.app.cv.perspective import estimate_vanishing_point, extract_structural_lines
from backend.app.cv.pipeline.base_footprint import solve_base_footprint
from backend.app.cv.pipeline.ceiling_header import solve_ceiling_and_header
from backend.app.cv.pipeline.vertical_extrusion import compute_upward_vertical_rays
from backend.app.cv.sample_generator import generate_sample_alcove_bath


def test_stage1_base_footprint():
    img_bgr = generate_sample_alcove_bath(800, 600)
    lines = extract_structural_lines(img_bgr, min_length=15.0)
    vp = estimate_vanishing_point(lines, 800, 600)

    base_res = solve_base_footprint(img_bgr, lines, vp, [200.0, 600.0])
    assert "base_type" in base_res
    assert base_res["y_floor"] > base_res["y_header"]
    assert base_res["h_wet"] > 0
    assert len(base_res["p4_init"]) == 2
    assert len(base_res["p7_init"]) == 2
    assert len(base_res["p5_proj"]) == 2
    assert len(base_res["p6_proj"]) == 2


def test_stage2_vertical_extrusion():
    img_bgr = generate_sample_alcove_bath(800, 600)
    lines = extract_structural_lines(img_bgr, min_length=15.0)
    vp = estimate_vanishing_point(lines, 800, 600)

    p4, p5, p6, p7 = [100.0, 540.0], [200.0, 420.0], [600.0, 420.0], [700.0, 540.0]
    rays = compute_upward_vertical_rays(p4, p5, p6, p7, lines, vp, img_bgr.shape)

    assert "ray_outer_l" in rays
    assert "ray_crease_l" in rays
    assert "ray_crease_r" in rays
    assert "ray_outer_r" in rays
    # Direction vectors must point upward (dy < 0)
    for ray_name, r_data in rays.items():
        assert r_data["dir"][1] < 0.0


def test_stage3_ceiling_header_intersections():
    img_bgr = generate_sample_alcove_bath(800, 600)
    lines = extract_structural_lines(img_bgr, min_length=15.0)
    vp = estimate_vanishing_point(lines, 800, 600)

    p4, p5, p6, p7 = [100.0, 540.0], [200.0, 420.0], [600.0, 420.0], [700.0, 540.0]
    rays = compute_upward_vertical_rays(p4, p5, p6, p7, lines, vp, img_bgr.shape)
    top_res = solve_ceiling_and_header(rays, lines, y_header=150.0, img_shape=img_bgr.shape)

    assert len(top_res["p0"]) == 2
    assert len(top_res["p1"]) == 2
    assert len(top_res["p2"]) == 2
    assert len(top_res["p3"]) == 2
    # P1 and P2 must be inside P0 and P3
    assert top_res["p0"][0] <= top_res["p1"][0]
    assert top_res["p1"][0] < top_res["p2"][0]
    assert top_res["p2"][0] <= top_res["p3"][0]
