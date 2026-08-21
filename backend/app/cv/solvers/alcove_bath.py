"""
Alcove Bath 8-Point 2.5D Perspective Mesh Solver.
Implements the 4-Stage Bottom-Up (Floor & Tub-First) Computer Vision Reconstruction Pipeline.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from ...core.schemas import PolygonPlane, PresetDefinition
from ..perspective import (
    LineSegment,
    estimate_vanishing_point,
    estimate_vertical_creases,
)
from ..pipeline.base_footprint import solve_base_footprint
from ..pipeline.ceiling_header import solve_ceiling_and_header
from ..pipeline.vertical_extrusion import compute_upward_vertical_rays
from .base import BasePresetSolver
from .registry import register_solver

ALCOVE_BATH_PRESET = PresetDefinition(
    id="alcove_bath",
    name="Alcove Bath (3 Walls)",
    description="Recessed 3-wall alcove bathtub surround with 8 vertices, 10 lines, and 3 polygon surfaces.",
    point_count=8,
    line_count=10,
    enabled=True,
    default_normalized_points=[
        [0.080, 0.080],  # 0: Left Wall Top (Front outer ceiling)
        [0.260, 0.200],  # 1: Back-Left Top (Header corner)
        [0.740, 0.200],  # 2: Back-Right Top (Header corner)
        [0.920, 0.080],  # 3: Right Wall Top (Front outer ceiling)
        [0.080, 0.910],  # 4: Left-Front Floor Base
        [0.260, 0.680],  # 5: Back-Left Tub Rim / Ledge
        [0.740, 0.680],  # 6: Back-Right Tub Rim / Ledge
        [0.920, 0.910],  # 7: Right-Front Floor Base
    ],
    lines=[
        [0, 1],  # 1. Left top perspective header
        [1, 2],  # 2. Back wall top header
        [2, 3],  # 3. Right top perspective header
        [0, 4],  # 4. Left outer jamb vertical
        [1, 5],  # 5. Back-left corner crease
        [2, 6],  # 6. Back-right corner crease
        [3, 7],  # 7. Right outer jamb vertical
        [4, 5],  # 8. Left tub ledge / floor seam
        [5, 6],  # 9. Back tub ledge seam
        [6, 7],  # 10. Right tub ledge / floor seam
    ],
    planes=[
        PolygonPlane(
            id="left_wall",
            name="Left Wall Surround",
            point_indices=[0, 1, 5, 4],
        ),
        PolygonPlane(
            id="back_wall",
            name="Back Wall Surround",
            point_indices=[1, 2, 6, 5],
        ),
        PolygonPlane(
            id="right_wall",
            name="Right Wall Surround",
            point_indices=[2, 3, 7, 6],
        ),
    ],
)


@register_solver("alcove_bath")
class AlcoveBathSolver(BasePresetSolver):
    """
    Modular 8-point solver for alcove/recessed bathrooms using the Bottom-Up Pipeline:
    - P0: Left-Front Ceiling Corner
    - P1: Back-Left Top Wall Corner (Header)
    - P2: Back-Right Top Wall Corner (Header)
    - P3: Right-Front Ceiling Corner
    - P4: Left-Front Floor Base Corner
    - P5: Back-Left Tub Rim / Pan Ledge Corner
    - P6: Back-Right Tub Rim / Pan Ledge Corner
    - P7: Right-Front Floor Base Corner
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

        # 2. Continuous 1D KDE Vertical Crease Estimation & Optimal Crease Pair Selection
        creases = estimate_vertical_creases(
            lines,
            w,
            min_length_ratio=0.03,
            min_peak_distance=max(30.0, 0.035 * w),
        )
        left_cands = [c for c in creases if 0.15 * w <= c <= 0.45 * w]
        right_cands = [c for c in creases if 0.55 * w <= c <= 0.88 * w]

        best_crease_pair = None
        best_crease_score = -1.0
        for c_left in left_cands:
            for c_right in right_cands:
                span = (c_right - c_left) / w
                if 0.28 <= span <= 0.68:
                    center_offset = abs((c_left + c_right) / 2.0 - w / 2.0) / w
                    score = 1.0 - center_offset * 1.5
                    if score > best_crease_score:
                        best_crease_score = score
                        best_crease_pair = (c_left, c_right)

        if best_crease_pair:
            x_in_l, x_in_r = best_crease_pair
        else:
            x_in_l = left_cands[0] if left_cands else 0.26 * w
            x_in_r = right_cands[0] if right_cands else 0.74 * w

        landmarks["back_left_crease_x"] = round(x_in_l, 1)
        landmarks["back_right_crease_x"] = round(x_in_r, 1)

        # =====================================================================
        # Stage 1: Base Footprint & Tub Ledge Solver (Bottom-Up Ground Plane)
        # =====================================================================
        base_res = solve_base_footprint(img_bgr, lines, (vp_x, vp_y), [x_in_l, x_in_r], config=self.config)
        landmarks["detected_base_type"] = base_res["base_type"]
        landmarks["wet_area_real_estate_ratio"] = round(base_res["h_wet"] / h, 3)

        y_header = base_res["y_header"]
        y_floor = base_res["y_floor"]
        y_base_target = base_res["y_base_target"]
        h_wet = base_res["h_wet"]
        h_back_wall = base_res["h_back_wall"]

        # Hardware Deadband (Strictly on Back Wall: Between Header and Tub Rim)
        deadband_y_range = (
            y_header + 0.32 * h_back_wall,
            y_header + 0.68 * h_back_wall,
        )
        landmarks["deadband_y_range"] = [round(deadband_y_range[0], 1), round(deadband_y_range[1], 1)]

        # Elevation bands for graph role assignment
        elevation_bands = {
            "Band_A_Ceiling": (0.00 * h, y_header),
            "Band_B_BackTop": (max(0.0, y_header - 0.12 * h_wet), y_header + 0.25 * h_back_wall),
            "Band_C_BackBase": (
                max(0.0, y_base_target - 0.15 * h_back_wall),
                min(h, y_base_target + 0.15 * h_back_wall),
            ),
            "Band_D_FrontBase": (max(0.0, y_floor - 0.15 * h_wet), min(h, y_floor + 0.15 * h_wet)),
        }
        landmarks["elevation_bands"] = {k: [round(v[0], 1), round(v[1], 1)] for k, v in elevation_bands.items()}

        # Candidate Dot Generation & Rule Filtering
        candidates = self.extract_all_candidate_dots(img_bgr, lines, (vp_x, vp_y))
        candidates, classified_bands = self.evaluate_rules_and_filter_candidates(
            candidates, img_bgr.shape, (vp_x, vp_y), elevation_bands, deadband_y_range=deadband_y_range
        )
        landmarks["candidates"] = candidates

        band_a = classified_bands["Band_A_Ceiling"]
        band_b = classified_bands["Band_B_BackTop"]
        band_c = classified_bands["Band_C_BackBase"]
        band_d = classified_bands["Band_D_FrontBase"]

        # Match Ground Corners P4 & P7 in Band D
        cand_p4 = [d for d in band_d if d["x"] <= x_in_l + 0.05 * w and d["y"] >= 0.75 * h]
        cand_p4 = sorted(cand_p4, key=lambda d: -d["y"])
        p4_dot = cand_p4[0] if cand_p4 else None
        x4, y4 = (p4_dot["x"], p4_dot["y"]) if p4_dot else (base_res["p4_init"][0], y_floor)

        cand_p7 = [d for d in band_d if d["x"] >= x_in_r - 0.05 * w and d["y"] >= 0.75 * h]
        cand_p7 = sorted(cand_p7, key=lambda d: -d["y"])
        p7_dot = cand_p7[0] if cand_p7 else None
        x7, y7 = (p7_dot["x"], p7_dot["y"]) if p7_dot else (base_res["p7_init"][0], y_floor)

        # Match Tub Rim / Pan Ledge Corners P5 & P6 in Band C
        y5_target = min(y4 - 0.05 * h, y_base_target)
        y6_target = min(y7 - 0.05 * h, y_base_target)

        denom_l = vp_y - y4
        x5_proj = x4 + (y5_target - y4) * (vp_x - x4) / denom_l if abs(denom_l) > 1e-3 else x_in_l
        denom_r = vp_y - y7
        x6_proj = x7 + (y6_target - y7) * (vp_x - x7) / denom_r if abs(denom_r) > 1e-3 else x_in_r

        A_l, B_l, C_l = (vp_y - y4), -(vp_x - x4), (vp_x * y4 - vp_y * x4)
        norm_l = max(1e-3, math.hypot(A_l, B_l))
        A_r, B_r, C_r = (vp_y - y7), -(vp_x - x7), (vp_x * y7 - vp_y * x7)
        norm_r = max(1e-3, math.hypot(A_r, B_r))

        cand_p5_pool = [
            d
            for d in band_c
            if abs(d["x"] - x_in_l) <= 0.12 * w and abs(d["y"] - y5_target) <= 0.08 * h_back_wall and d["y"] < y4
        ]
        cand_p6_pool = [
            d
            for d in band_c
            if abs(d["x"] - x_in_r) <= 0.12 * w and abs(d["y"] - y6_target) <= 0.08 * h_back_wall and d["y"] < y7
        ]

        best_pair = None
        best_cost = float("inf")

        for d5 in cand_p5_pool:
            dist_l = abs(A_l * d5["x"] + B_l * d5["y"] + C_l) / norm_l
            for d6 in cand_p6_pool:
                if d6["x"] <= d5["x"] + 0.25 * w:
                    continue
                dist_r = abs(A_r * d6["x"] + B_r * d6["y"] + C_r) / norm_r
                pair_angle = math.degrees(math.atan2(d6["y"] - d5["y"], d6["x"] - d5["x"]))
                if abs(pair_angle) > 3.0:
                    continue
                cost = dist_l + dist_r + abs(pair_angle) * 10.0 + abs(d5["y"] - y5_target) * 2.0 + abs(d6["y"] - y6_target) * 2.0
                if cost < best_cost:
                    best_cost = cost
                    best_pair = (d5, d6)

        if best_pair:
            x5, y5 = best_pair[0]["x"], best_pair[0]["y"]
            x6, y6 = best_pair[1]["x"], best_pair[1]["y"]
        else:
            x5, y5 = x5_proj, y5_target
            x6, y6 = x6_proj, y6_target

        p4 = [x4, y4]
        p5 = [x5, y5]
        p6 = [x6, y6]
        p7 = [x7, y7]

        # =====================================================================
        # Stage 2: Upward Vertical Perspective Extrusions
        # =====================================================================
        rays = compute_upward_vertical_rays(p4, p5, p6, p7, lines, (vp_x, vp_y), img_bgr.shape)

        # =====================================================================
        # Stage 3: Ceiling & Header Intersections
        # =====================================================================
        top_res = solve_ceiling_and_header(rays, lines, y_header, img_bgr.shape)

        p1_init = [top_res["p1"][0], y_header]
        p2_init = [top_res["p2"][0], y_header]

        # Snap P1 & P2 to best candidate dots in Band B if closely aligned
        cand_p1 = [
            d for d in band_b if abs(d["x"] - p1_init[0]) <= 0.04 * w and abs(d["y"] - y_header) <= 0.02 * h
        ]
        p1 = [cand_p1[0]["x"], cand_p1[0]["y"]] if cand_p1 else p1_init

        cand_p2 = [
            d for d in band_b if abs(d["x"] - p2_init[0]) <= 0.04 * w and abs(d["y"] - p1[1]) <= 0.02 * h
        ]
        p2 = [cand_p2[0]["x"], cand_p2[0]["y"]] if cand_p2 else p2_init

        # Snap P0 & P3 to outermost candidate dots in Band A if available
        cand_p0 = [d for d in band_a if d["x"] <= p1[0] - 0.05 * w]
        cand_p0 = sorted(cand_p0, key=lambda d: d["x"])
        p0 = [cand_p0[0]["x"], cand_p0[0]["y"]] if cand_p0 else top_res["p0"]

        cand_p3 = [d for d in band_a if d["x"] >= p2[0] + 0.05 * w]
        cand_p3 = sorted(cand_p3, key=lambda d: -d["x"])
        p3 = [cand_p3[0]["x"], cand_p3[0]["y"]] if cand_p3 else top_res["p3"]

        selected_points = [p0, p1, p2, p3, p4, p5, p6, p7]
        base_confidence = 0.92 if best_pair else 0.85

        return selected_points, base_confidence, landmarks
