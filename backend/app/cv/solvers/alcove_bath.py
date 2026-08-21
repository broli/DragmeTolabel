"""
Modular Alcove Bath geometry definition and specialized CV auto-fit solver.
Detects 3-wall recessed alcove boundaries, dual vertical corner creases, and tub/pan surround ledge
using 4-column vertical clustering, middle deadband hardware suppression, and dual-elevation floor perspective.
"""

from __future__ import annotations

import math
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
        [0.08, 0.08],  # P0: Left-Front Top (Outer ceiling bulkhead)
        [0.26, 0.20],  # P1: Back-Left Top (Back wall inner top)
        [0.74, 0.20],  # P2: Back-Right Top (Back wall inner top)
        [0.92, 0.08],  # P3: Right-Front Top (Outer ceiling bulkhead)
        [0.18, 0.92],  # P4: Left-Front Bottom (Front curb / tub skirt)
        [0.32, 0.68],  # P5: Back-Left Pan Seam (Back wall ledge)
        [0.68, 0.68],  # P6: Back-Right Pan Seam (Back wall ledge)
        [0.82, 0.92],  # P7: Right-Front Bottom (Front curb / tub skirt)
    ],
    lines=[
        [0, 1],  # 0: Left ceiling slant
        [1, 2],  # 1: Back wall top header
        [2, 3],  # 2: Right ceiling slant
        [0, 4],  # 3: Left outer wall / frame boundary
        [1, 5],  # 4: Back-left corner crease
        [2, 6],  # 5: Back-right corner crease
        [3, 7],  # 6: Right outer wall / frame boundary
        [4, 5],  # 7: Left tub rim / pan ledge seam
        [5, 6],  # 8: Back wall tub rim / pan ledge seam
        [6, 7],  # 9: Right tub rim / pan ledge seam
    ],
    planes=[
        PolygonPlane(
            id="left_wall",
            name="Left Wall",
            point_indices=[0, 1, 5, 4],
            default_material="carrara_marble",
        ),
        PolygonPlane(
            id="back_wall",
            name="Back Wall",
            point_indices=[1, 2, 6, 5],
            default_material="carrara_marble",
        ),
        PolygonPlane(
            id="right_wall",
            name="Right Wall",
            point_indices=[2, 3, 7, 6],
            default_material="carrara_marble",
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

        # 3. Dynamic Wet Area Real Estate & Framing Detection (Header vs Floor Boundary)
        horiz_all = [seg for seg in lines if seg.category == "horizontal"]
        header_lines = [seg for seg in horiz_all if (seg.y1 + seg.y2) / 2.0 <= 0.35 * h]
        y_header = float((header_lines[0].y1 + header_lines[0].y2) / 2.0) if header_lines else 0.20 * h

        floor_lines = [seg for seg in horiz_all if (seg.y1 + seg.y2) / 2.0 >= 0.65 * h]
        if floor_lines:
            floor_lines_by_depth = sorted(floor_lines, key=lambda seg: (seg.y1 + seg.y2) / 2.0, reverse=True)
            y_floor = float((floor_lines_by_depth[0].y1 + floor_lines_by_depth[0].y2) / 2.0)
        else:
            y_floor = 0.91 * h

        h_wet = max(0.40 * h, y_floor - y_header)
        landmarks["wet_area_real_estate_ratio"] = round(h_wet / h, 3)

        # Relative Hardware Deadband (Middle 32% - 56% of wet area wall)
        deadband_y_range = (y_header + 0.32 * h_wet, y_header + 0.56 * h_wet)
        landmarks["deadband_y_range"] = [round(deadband_y_range[0], 1), round(deadband_y_range[1], 1)]

        # 4. Base Type & Elevation Auto-Detection (Bathtub vs Shower Pan)
        tub_lines = [
            seg for seg in horiz_all
            if y_header + 0.55 * h_wet <= (seg.y1 + seg.y2) / 2.0 <= y_header + 0.88 * h_wet
        ]
        pan_lines = [
            seg for seg in horiz_all
            if y_header + 0.88 * h_wet < (seg.y1 + seg.y2) / 2.0 <= y_floor + 0.05 * h_wet
        ]

        tub_score = sum(seg.length for seg in tub_lines)
        pan_score = sum(seg.length for seg in pan_lines)

        base_type = "bathtub" if (tub_score >= pan_score and tub_lines) else "shower_pan"
        landmarks["detected_base_type"] = base_type

        # Dominant back base seam Y
        if base_type == "bathtub" and tub_lines:
            tub_lines_sorted = sorted(tub_lines, key=lambda seg: seg.length, reverse=True)
            y_base_target = float((tub_lines_sorted[0].y1 + tub_lines_sorted[0].y2) / 2.0)
        elif base_type == "shower_pan" and pan_lines:
            pan_lines_sorted = sorted(pan_lines, key=lambda seg: seg.length, reverse=True)
            y_base_target = float((pan_lines_sorted[0].y1 + pan_lines_sorted[0].y2) / 2.0)
        else:
            y_base_target = y_header + 0.72 * h_wet if base_type == "bathtub" else y_floor - 0.05 * h_wet

        # 5. 2D Candidate Dot Generation and Dynamic Rule Filtering
        elevation_bands = {
            "Band_A_Ceiling": (0.00 * h, y_header),
            "Band_B_BackTop": (max(0.0, y_header - 0.08 * h_wet), y_header + 0.20 * h_wet),
            "Band_C_BackBase": (max(0.40 * h, y_base_target - 0.12 * h_wet), min(h, y_base_target + 0.12 * h_wet)),
            "Band_D_FrontBase": (max(0.60 * h, y_floor - 0.15 * h_wet), min(h, y_floor + 0.15 * h_wet)),
        }
        landmarks["elevation_bands"] = {
            k: [round(v[0], 1), round(v[1], 1)] for k, v in elevation_bands.items()
        }
        candidates = self.extract_all_candidate_dots(img_bgr, lines, (vp_x, vp_y))
        candidates, classified_bands = self.evaluate_rules_and_filter_candidates(
            candidates, img_bgr.shape, (vp_x, vp_y), elevation_bands, deadband_y_range=deadband_y_range
        )

        band_a = classified_bands["Band_A_Ceiling"]
        band_b = classified_bands["Band_B_BackTop"]
        band_c = classified_bands["Band_C_BackBase"]
        band_d = classified_bands["Band_D_FrontBase"]

        # 6. Graph Selection: Match candidate dots to P0-P7 vertices
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

        # P4: Left-Front Floor Base (Deepest floor point on left in Band D)
        cand_p4 = [d for d in band_d if d["x"] <= x1 + 0.05 * w and d["y"] >= 0.80 * h]
        cand_p4 = sorted(cand_p4, key=lambda d: -d["y"])
        p4 = cand_p4[0] if cand_p4 else None
        x4, y4 = (p4["x"], p4["y"]) if p4 else (max(0.04 * w, x0 + 0.08 * w), 0.91 * h)

        # P7: Right-Front Floor Base (Deepest floor point on right in Band D)
        cand_p7 = [d for d in band_d if d["x"] >= x2 - 0.05 * w and d["y"] >= 0.80 * h]
        cand_p7 = sorted(cand_p7, key=lambda d: -d["y"])
        p7 = cand_p7[0] if cand_p7 else None
        x7, y7 = (p7["x"], p7["y"]) if p7 else (min(0.96 * w, x3 - 0.08 * w), 0.91 * h)

        # 6. Perspective Ledge Ray Projection for P5 and P6
        y5_target = min(y4 - 0.05 * h, y_base_target)
        y6_target = min(y7 - 0.05 * h, y_base_target)

        denom_l = vp_y - y4
        x5_proj = x4 + (y5_target - y4) * (vp_x - x4) / denom_l if abs(denom_l) > 1e-3 else x1
        denom_r = vp_y - y7
        x6_proj = x7 + (y6_target - y7) * (vp_x - x7) / denom_r if abs(denom_r) > 1e-3 else x2

        # Ray equations for perpendicular distance
        A_l, B_l, C_l = (vp_y - y4), -(vp_x - x4), (vp_x * y4 - vp_y * x4)
        norm_l = max(1e-3, math.hypot(A_l, B_l))
        A_r, B_r, C_r = (vp_y - y7), -(vp_x - x7), (vp_x * y7 - vp_y * x7)
        norm_r = max(1e-3, math.hypot(A_r, B_r))

        header_angle = math.degrees(math.atan2(y2 - y1, x2 - x1))

        # Evaluate candidate pairs (p5, p6) in Band C
        cand_p5_pool = [d for d in band_c if d["x"] < x2 - 0.10 * w and d["y"] < y4]
        cand_p6_pool = [d for d in band_c if d["x"] > x1 + 0.10 * w and d["y"] < y7]

        best_pair = None
        best_cost = float("inf")

        for d5 in cand_p5_pool:
            dist_l = abs(A_l * d5["x"] + B_l * d5["y"] + C_l) / norm_l
            for d6 in cand_p6_pool:
                if d6["x"] <= d5["x"] + 0.15 * w:
                    continue
                dist_r = abs(A_r * d6["x"] + B_r * d6["y"] + C_r) / norm_r
                pair_angle = math.degrees(math.atan2(d6["y"] - d5["y"], d6["x"] - d5["x"]))
                angle_diff = abs(pair_angle - header_angle)

                cost = dist_l * 1.0 + dist_r * 1.0 + angle_diff * 15.0 + abs(d5["y"] - d6["y"]) * 0.5
                if cost < best_cost:
                    best_cost = cost
                    best_pair = (d5, d6)

        p5_match = None
        p6_match = None
        if best_pair is not None and best_cost < 250.0:
            p5_match, p6_match = best_pair
            x5, y5 = p5_match["x"], p5_match["y"]
            x6, y6 = p6_match["x"], p6_match["y"]
        else:
            x5, y5 = x5_proj, y5_target
            x6, y6 = x6_proj, y6_target

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

        matched_count = sum(1 for p in (p0, p1, p2, p3, p4, p5_match, p6_match, p7) if p is not None)
        confidence = round(0.60 + (matched_count / 8.0) * 0.35, 2)
        return points, confidence, landmarks
