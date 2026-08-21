"""
Modular Alcove Bath geometry definition and specialized CV auto-fit solver.
Detects 3-wall recessed alcove boundaries, dual vertical corner creases, and tub/pan surround ledge
using 4-column vertical clustering, middle deadband hardware suppression, and dual-elevation floor perspective.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ...core.schemas import PolygonPlane, PresetDefinition
from ..perspective import LineSegment, estimate_vanishing_point, estimate_vertical_creases
from .base import BasePresetSolver
from .registry import register_solver

ALCOVE_BATH_PRESET = PresetDefinition(
    id="alcove_bath",
    name="Alcove Bath",
    description="3-wall recessed alcove bathtub with 8 vertices and 10 connecting lines (Left Wall, Back Wall, Right Wall).",
    point_count=8,
    line_count=10,
    enabled=True,
    default_normalized_points=[
        [0.025, 0.070],  # 0: Left-Front Top (Outer ceiling bulkhead)
        [0.215, 0.195],  # 1: Back-Left Top (Back wall inner top)
        [0.775, 0.195],  # 2: Back-Right Top (Back wall inner top)
        [0.945, 0.070],  # 3: Right-Front Top (Outer ceiling bulkhead)
        [0.180, 0.910],  # 4: Left-Front Bottom (Front curb / tub skirt)
        [0.330, 0.700],  # 5: Back-Left Pan Seam (Back wall ledge)
        [0.675, 0.700],  # 6: Back-Right Pan Seam (Back wall ledge)
        [0.820, 0.910],  # 7: Right-Front Bottom (Front curb / tub skirt)
    ],
    lines=[
        [0, 1],  # 1. Left wall top perspective slant
        [1, 2],  # 2. Back wall top
        [2, 3],  # 3. Right wall top perspective slant
        [0, 4],  # 4. Left front vertical / outer drywall
        [1, 5],  # 5. Back left corner crease
        [2, 6],  # 6. Back right corner crease
        [3, 7],  # 7. Right front vertical / outer drywall
        [4, 5],  # 8. Left bottom tub/pan perspective seam
        [5, 6],  # 9. Back tub/pan rim ledge
        [6, 7],  # 10. Right bottom tub/pan perspective seam
    ],
    planes=[
        PolygonPlane(
            id="left_wall",
            name="Left Alcove Wall",
            point_indices=[0, 1, 5, 4],
        ),
        PolygonPlane(
            id="back_wall",
            name="Back Alcove Wall",
            point_indices=[1, 2, 6, 5],
        ),
        PolygonPlane(
            id="right_wall",
            name="Right Alcove Wall",
            point_indices=[2, 3, 7, 6],
        ),
    ],
)


@register_solver("alcove_bath")
class AlcoveBathSolver(BasePresetSolver):
    """
    Specialized solver for 3-wall recessed alcove bathtub / shower surrounds (8 control points).
    Applies physical architectural invariants:
    - Multi-source 2D candidate dot generation (line intersections, Shi-Tomasi/Harris corners).
    - Middle deadband suppression (35% - 56% of height) to ignore grab bars, faucets, and valves.
    - Continuous KDE 4-column vertical ordering (outer_left < inner_left < inner_right < outer_right).
    - Dual-elevation top ceiling vs header and bottom pan seam vs front floor apron.
    """

    @property
    def preset_definition(self) -> PresetDefinition:
        return ALCOVE_BATH_PRESET

    def find_optimal_mesh(
        self,
        img_bgr: np.ndarray,
        lines: list[LineSegment],
    ) -> tuple[list[list[float]], float, dict[str, Any]]:
        h, w = img_bgr.shape[:2]
        landmarks: dict[str, Any] = {}

        # 1. Vanishing Point Estimation
        vp_x, vp_y = estimate_vanishing_point(lines, w, h)
        landmarks["vp_x"] = round(vp_x, 1)
        landmarks["vp_y"] = round(vp_y, 1)

        # 2. Continuous 1D KDE Vertical Crease Detection
        creases = estimate_vertical_creases(
            lines,
            w,
            min_length_ratio=0.03,
            min_peak_distance=max(30.0, 0.035 * w),
        )

        c_left_inner = [c for c in creases if 0.15 * w <= c <= 0.42 * w]
        x_in_l = c_left_inner[0] if c_left_inner else 0.26 * w

        c_right_inner = [c for c in creases if 0.58 * w <= c <= 0.85 * w]
        x_in_r = c_right_inner[0] if c_right_inner else 0.74 * w

        # 3. 2D Candidate Dot Generation and Rule Filtering
        elevation_bands = {
            "Band_A_Ceiling": (0.00 * h, 0.16 * h),
            "Band_B_BackTop": (0.12 * h, 0.35 * h),
            "Band_C_BackTub": (0.58 * h, 0.76 * h),
            "Band_D_FrontBase": (0.78 * h, 0.98 * h),
        }
        candidates = self.extract_all_candidate_dots(img_bgr, lines, (vp_x, vp_y))
        candidates, classified_bands = self.evaluate_rules_and_filter_candidates(
            candidates, img_bgr.shape, (vp_x, vp_y), elevation_bands
        )

        band_a = classified_bands["Band_A_Ceiling"]
        band_b = classified_bands["Band_B_BackTop"]
        band_c = classified_bands["Band_C_BackTub"]
        band_d = classified_bands["Band_D_FrontBase"]

        # 4. Graph Selection: Match candidate dots to P0-P7 vertices
        # P1: Back-Left Top (Band B near x_in_l)
        cand_p1 = [d for d in band_b if d["x"] < x_in_r - 0.15 * w]
        cand_p1 = sorted(cand_p1, key=lambda d: abs(d["x"] - x_in_l) + abs(d["y"] - 0.20 * h) * 0.3)
        p1 = cand_p1[0] if cand_p1 else None
        x1, y1 = (p1["x"], p1["y"]) if p1 else (x_in_l, 0.20 * h)

        # P2: Back-Right Top (Band B near x_in_r, aligned with y1)
        cand_p2 = [d for d in band_b if d["x"] >= x1 + 0.18 * w]
        cand_p2 = sorted(cand_p2, key=lambda d: abs(d["x"] - x_in_r) + abs(d["y"] - y1) * 0.6)
        p2 = cand_p2[0] if cand_p2 else None
        x2, y2 = (p2["x"], p2["y"]) if p2 else (x_in_r, y1)

        # P5: Back-Left Tub Rim (Band C near x1)
        cand_p5 = [d for d in band_c if d["x"] < x2 - 0.15 * w]
        cand_p5 = sorted(cand_p5, key=lambda d: abs(d["x"] - x1) + abs(d["y"] - 0.68 * h) * 0.3)
        p5 = cand_p5[0] if cand_p5 else None
        x5, y5 = (p5["x"], p5["y"]) if p5 else (x1, 0.68 * h)

        # P6: Back-Right Tub Rim (Band C near x2, aligned with y5)
        cand_p6 = [d for d in band_c if d["x"] >= x5 + 0.18 * w]
        cand_p6 = sorted(cand_p6, key=lambda d: abs(d["x"] - x2) + abs(d["y"] - y5) * 0.6)
        p6 = cand_p6[0] if cand_p6 else None
        x6, y6 = (p6["x"], p6["y"]) if p6 else (x2, y5)

        # P0: Left-Front Ceiling (Outermost left in Band A)
        cand_p0 = [d for d in band_a if d["x"] < x1 - 0.05 * w]
        cand_p0 = sorted(cand_p0, key=lambda d: d["x"])
        p0 = cand_p0[0] if cand_p0 else None
        x0, y0 = (p0["x"], p0["y"]) if p0 else (max(0.02 * w, x1 - 0.20 * w), 0.08 * h)

        # P3: Right-Front Ceiling (Outermost right in Band A)
        cand_p3 = [d for d in band_a if d["x"] > x2 + 0.05 * w]
        cand_p3 = sorted(cand_p3, key=lambda d: -d["x"])
        p3 = cand_p3[0] if cand_p3 else None
        x3, y3 = (p3["x"], p3["y"]) if p3 else (min(0.98 * w, x2 + 0.20 * w), 0.08 * h)

        # P4: Left-Front Base (Deepest floor point on left in Band D)
        cand_p4 = [d for d in band_d if d["x"] <= x5 and d["y"] >= 0.82 * h]
        cand_p4 = sorted(cand_p4, key=lambda d: -d["y"])
        p4 = cand_p4[0] if cand_p4 else None
        x4, y4 = (p4["x"], p4["y"]) if p4 else (max(0.04 * w, x0 + 0.08 * w), 0.91 * h)

        # P7: Right-Front Base (Deepest floor point on right in Band D)
        cand_p7 = [d for d in band_d if d["x"] >= x6 and d["y"] >= 0.82 * h]
        cand_p7 = sorted(cand_p7, key=lambda d: -d["y"])
        p7 = cand_p7[0] if cand_p7 else None
        x7, y7 = (p7["x"], p7["y"]) if p7 else (min(0.96 * w, x3 - 0.08 * w), 0.91 * h)

        landmarks["outer_left_x"] = round(x0, 1)
        landmarks["back_left_crease_x"] = round(x1, 1)
        landmarks["back_right_crease_x"] = round(x2, 1)
        landmarks["outer_right_x"] = round(x3, 1)
        landmarks["y_front_ceiling"] = round(min(y0, y3), 1)
        landmarks["y_back_top"] = round(min(y1, y2), 1)
        landmarks["y_back_tub"] = round(max(y5, y6), 1)
        landmarks["y_front_floor_base"] = round(max(y4, y7), 1)
        landmarks["candidates"] = candidates

        points = [
            [x0, y0],  # 0: Left-Front Top (Outer ceiling bulkhead)
            [x1, y1],  # 1: Back-Left Top (Back wall inner top)
            [x2, y2],  # 2: Back-Right Top (Back wall inner top)
            [x3, y3],  # 3: Right-Front Top (Outer ceiling bulkhead)
            [x4, y4],  # 4: Left-Front Bottom (Front curb / tub skirt)
            [x5, y5],  # 5: Back-Left Pan Seam (Back wall ledge)
            [x6, y6],  # 6: Back-Right Pan Seam (Back wall ledge)
            [x7, y7],  # 7: Right-Front Bottom (Front curb / tub skirt)
        ]

        matched_count = sum(1 for p in (p0, p1, p2, p3, p4, p5, p6, p7) if p is not None)
        confidence = round(0.60 + (matched_count / 8.0) * 0.35, 2)
        return points, confidence, landmarks
