"""
Unit tests for DragMeToLabel modular geometry solvers, registry, and auto-fit CV engine.
"""

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.cv.geometry_utils import (
    intersect_lines,
    is_quadrilateral_convex,
    polygon_area,
    subpixel_peak_1d,
)
from backend.app.cv.renderer import encode_image_base64
from backend.app.cv.solvers import (
    AlcoveBathSolver,
    CaliBathSolver,
    CeilingSolver,
    CornerBathSolver,
    FloorSolver,
    SolverRegistry,
)
from backend.app.main import app


def test_solver_registry_registration():
    """Verify all 5 preset solvers are properly registered in the SolverRegistry."""
    preset_ids = SolverRegistry.list_preset_ids()
    assert "floor" in preset_ids
    assert "ceiling" in preset_ids
    assert "corner_bath" in preset_ids
    assert "alcove_bath" in preset_ids
    assert "cali_bath" in preset_ids

    # Check solver instances and types
    assert isinstance(SolverRegistry.get_solver("floor"), FloorSolver)
    assert isinstance(SolverRegistry.get_solver("ceiling"), CeilingSolver)
    assert isinstance(SolverRegistry.get_solver("corner_bath"), CornerBathSolver)
    assert isinstance(SolverRegistry.get_solver("alcove_bath"), AlcoveBathSolver)
    assert isinstance(SolverRegistry.get_solver("cali_bath"), CaliBathSolver)

    # Check unknown preset returns None
    assert SolverRegistry.get_solver("unknown_fixture") is None


def test_geometry_utils_line_intersection():
    """Test line intersection calculation and parallel line handling."""
    # Orthogonal intersection at (50, 50)
    p1 = (50, 0)
    p2 = (50, 100)
    p3 = (0, 50)
    p4 = (100, 50)
    pt = intersect_lines(p1, p2, p3, p4)
    assert pt is not None
    assert pytest.approx(pt[0], 1e-4) == 50.0
    assert pytest.approx(pt[1], 1e-4) == 50.0

    # Parallel lines (no intersection)
    p_par1 = (0, 0)
    p_par2 = (100, 0)
    p_par3 = (0, 20)
    p_par4 = (100, 20)
    assert intersect_lines(p_par1, p_par2, p_par3, p_par4) is None


def test_geometry_utils_convexity():
    """Test quadrilateral convexity verification."""
    # Convex rectangle
    convex_quad = [[0, 0], [100, 0], [100, 100], [0, 100]]
    assert is_quadrilateral_convex(convex_quad, (0, 1, 2, 3)) is True

    # Convex trapezoid
    convex_trapezoid = [[20, 20], [80, 20], [90, 80], [10, 80]]
    assert is_quadrilateral_convex(convex_trapezoid, (0, 1, 2, 3)) is True

    # Concave (dart / arrowhead) quadrilateral
    concave_quad = [[0, 0], [100, 0], [50, 50], [0, 100]]
    assert is_quadrilateral_convex(concave_quad, (0, 1, 2, 3)) is False

    # Self-intersecting (twisted bowtie) polygon
    twisted_quad = [[0, 0], [100, 100], [100, 0], [0, 100]]
    assert is_quadrilateral_convex(twisted_quad, (0, 1, 2, 3)) is False


def test_geometry_utils_polygon_area():
    """Test Shoelace formula polygon area calculation."""
    # 100x100 square
    square = [[0, 0], [100, 0], [100, 100], [0, 100]]
    assert pytest.approx(polygon_area(square), 1e-4) == 10000.0

    # Triangle with base 100 and height 50 -> area 2500
    triangle = [[0, 0], [100, 0], [50, 50]]
    assert pytest.approx(polygon_area(triangle), 1e-4) == 2500.0


def test_geometry_utils_subpixel_peak():
    """Test 1D quadratic parabolic peak interpolation."""
    # Symmetrical peak exactly at index 5
    arr_sym = [0.0, 1.0, 3.0, 6.0, 9.0, 10.0, 9.0, 6.0, 3.0, 0.0]
    peak = subpixel_peak_1d(arr_sym, 5)
    assert pytest.approx(peak, 1e-3) == 5.0

    # Asymmetrical peak leaning slightly right of index 5
    arr_asym = [0.0, 1.0, 3.0, 6.0, 8.0, 10.0, 9.5, 6.0, 3.0, 0.0]
    peak_right = subpixel_peak_1d(arr_asym, 5)
    assert peak_right > 5.0


def test_corner_bath_solver_synthetic_room():
    """Test CornerBathSolver on synthetic bathroom image with prominent corner crease and tub rim."""
    h, w = 600, 800
    img = np.full((h, w, 3), 220, dtype=np.uint8)

    # Draw vertical corner crease at x=420
    crease_x = 420
    cv2.line(img, (crease_x, 50), (crease_x, 550), (40, 40, 40), 3)

    # Draw horizontal tub ledge at y=380
    tub_y = 380
    cv2.line(img, (50, tub_y), (750, tub_y), (50, 50, 50), 3)

    solver = CornerBathSolver()
    res = solver.solve(img)

    assert res.success is True
    assert res.preset_id == "corner_bath"
    assert len(res.points) == 6
    assert res.confidence >= 0.60
    assert res.execution_time_ms > 0

    # Verify detected crease and tub apex landmarks
    assert abs(res.landmarks.get("corner_crease_x", 0) - crease_x) < 20
    assert abs(res.landmarks.get("tub_apex_y", 0) - tub_y) < 20


def test_alcove_bath_solver_synthetic_room():
    """Test AlcoveBathSolver on synthetic 3-wall alcove bathroom."""
    h, w = 600, 800
    img = np.full((h, w, 3), 220, dtype=np.uint8)

    # Draw dual back wall creases at x=280 and x=540
    cv2.line(img, (280, 80), (280, 500), (30, 30, 30), 3)
    cv2.line(img, (540, 80), (540, 500), (30, 30, 30), 3)

    # Draw back tub rim at y=400
    cv2.line(img, (280, 400), (540, 400), (40, 40, 40), 3)

    solver = AlcoveBathSolver()
    res = solver.solve(img)

    assert res.success is True
    assert res.preset_id == "alcove_bath"
    assert len(res.points) == 8
    assert res.confidence >= 0.60
    assert "back_crease_left_x" in res.landmarks
    assert "back_crease_right_x" in res.landmarks


def test_floor_solver_synthetic_room():
    """Test FloorSolver on synthetic room with prominent baseboard."""
    h, w = 600, 800
    img = np.full((h, w, 3), 230, dtype=np.uint8)

    # Baseboard line at y=360
    baseboard_y = 360
    cv2.line(img, (0, baseboard_y), (w, baseboard_y), (30, 30, 30), 4)

    solver = FloorSolver()
    res = solver.solve(img)

    assert res.success is True
    assert res.preset_id == "floor"
    assert len(res.points) == 4
    assert res.confidence >= 0.50
    assert abs(res.landmarks.get("baseboard_y", 0) - baseboard_y) < 20


def test_api_autofit_endpoint():
    """Test POST /api/v1/autofit-preset REST endpoint."""
    client = TestClient(app)

    h, w = 400, 600
    test_img = np.full((h, w, 3), 210, dtype=np.uint8)
    cv2.line(test_img, (300, 50), (300, 350), (30, 30, 30), 3)
    cv2.line(test_img, (50, 260), (550, 260), (30, 30, 30), 3)

    img_b64 = encode_image_base64(test_img)

    # 1. Test corner_bath auto-fit
    req_corner = {"image_base64": img_b64, "preset_id": "corner_bath"}
    resp = client.post("/api/v1/autofit-preset", json=req_corner)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["preset_id"] == "corner_bath"
    assert len(data["points"]) == 6
    assert data["confidence"] > 0.4
    assert data["execution_time_ms"] > 0

    # 2. Test floor auto-fit via alias /autofit
    req_floor = {"image_base64": img_b64, "preset_id": "floor"}
    resp_floor = client.post("/api/v1/autofit", json=req_floor)
    assert resp_floor.status_code == 200
    data_floor = resp_floor.json()
    assert data_floor["success"] is True
    assert len(data_floor["points"]) == 4

    # 3. Test unknown preset 404 handling
    req_bad = {"image_base64": img_b64, "preset_id": "nonexistent_preset"}
    resp_bad = client.post("/api/v1/autofit-preset", json=req_bad)
    assert resp_bad.status_code == 404
