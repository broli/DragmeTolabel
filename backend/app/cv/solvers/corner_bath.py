"""
Modular Corner Bath geometry definition and specialized CV auto-fit solver.
Detects 2-wall corner crease seam, tub rim apex, and surround boundaries for 6-point mesh
using middle deadband hardware suppression, corner crease tracking, and dual-elevation floor perspective.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ...core.schemas import PolygonPlane, PresetDefinition
from ..perspective import LineSegment, estimate_vanishing_point, estimate_vertical_creases
from .base import BasePresetSolver
from .registry import register_solver

CORNER_BATH_PRESET = PresetDefinition(
    id="corner_bath",
    name="Corner Bath",
    description="Corner bathtub surround with 6 vertices and 7 connecting lines defining Left and Right walls.",
    point_count=6,
    line_count=7,
    enabled=True,
    default_normalized_points=[
        [0.080, 0.000],  # 0: Left Wall Top (Front outer ceiling)
        [0.500, 0.030],  # 1: Corner Top (Center corner apex)
        [0.920, 0.000],  # 2: Right Wall Top (Front outer ceiling)
        [0.150, 0.850],  # 3: Left Wall Tub Rim / Floor Base
        [0.500, 0.680],  # 4: Corner Bottom / Tub Apex
        [0.850, 0.850],  # 5: Right Wall Tub Rim / Floor Base
    ],
    lines=[
        [0, 1],  # 1. Left top perspective slant
        [1, 2],  # 2. Right top perspective slant
        [0, 3],  # 3. Left outer vertical
        [1, 4],  # 4. Center corner crease
        [2, 5],  # 5. Right outer vertical
        [3, 4],  # 6. Left tub ledge / floor perspective
        [4, 5],  # 7. Right tub ledge / floor perspective
    ],
    planes=[
        PolygonPlane(
            id="left_wall",
            name="Left Wall Surround",
            point_indices=[0, 1, 4, 3],
        ),
        PolygonPlane(
            id="right_wall",
            name="Right Wall Surround",
            point_indices=[1, 2, 5, 4],
        ),
    ],
)


@register_solver("corner_bath")
class CornerBathSolver(BasePresetSolver):
    """
    Specialized solver for 2-wall corner bathtub surrounds (6 control points).
    Applies physical architectural rules:
    - Multi-source 2D candidate dot generation.
    - Middle deadband suppression (35% - 56% of height).
    - Continuous KDE central corner crease tracking.
    - Dual-elevation floor perspective (recessed corner tub apex vs outer floor base).
    """

    @property
    def preset_definition(self) -> PresetDefinition:
        return CORNER_BATH_PRESET

    def find_optimal_mesh(
        self,
        img_bgr: np.ndarray,
        lines: list[LineSegment],
    ) -> tuple[list[list[float]], float, dict[str, Any]]:
        h, w = img_bgr.shape[:2]
        landmarks: dict[str, Any] = {}

        # 1. Estimate Vanishing Point
        vp_x, vp_y = estimate_vanishing_point(lines, w, h)
        landmarks["vp_x"] = round(vp_x, 1)
        landmarks["vp_y"] = round(vp_y, 1)

        # 2. Continuous 1D KDE Corner Crease Detection
        creases = estimate_vertical_creases(
            lines,
            w,
            min_length_ratio=0.04,
            min_peak_distance=max(35.0, 0.04 * w),
        )
        mid_cands = [c for c in creases if 0.30 * w <= c <= 0.70 * w]
        x_corner = mid_cands[0] if mid_cands else vp_x
        landmarks["corner_crease_x"] = round(x_corner, 1)

        # 3. 2D Candidate Dot Generation and Rule Filtering
        elevation_bands = {
            "Band_A_Ceiling": (0.00 * h, 0.20 * h),
            "Band_B_CornerTop": (0.05 * h, 0.30 * h),
            "Band_C_TubApex": (0.58 * h, 0.76 * h),
            "Band_D_FloorBase": (0.76 * h, 0.98 * h),
        }
        candidates = self.extract_all_candidate_dots(img_bgr, lines, (vp_x, vp_y))
        candidates, classified_bands = self.evaluate_rules_and_filter_candidates(
            candidates, img_bgr.shape, (vp_x, vp_y), elevation_bands
        )

        band_a = classified_bands["Band_A_Ceiling"]
        band_b = classified_bands["Band_B_CornerTop"]
        band_c = classified_bands["Band_C_TubApex"]
        band_d = classified_bands["Band_D_FloorBase"]

        # P1: Corner Top (Band B near x_corner)
        cand_p1 = sorted(band_b, key=lambda d: abs(d["x"] - x_corner) + abs(d["y"] - 0.10 * h) * 0.4)
        p1 = cand_p1[0] if cand_p1 else None
        x1, y1 = (p1["x"], p1["y"]) if p1 else (x_corner, 0.08 * h)

        # P4: Corner Tub Apex (Band C near x_corner)
        cand_p4 = sorted(band_c, key=lambda d: abs(d["x"] - x_corner) + abs(d["y"] - 0.68 * h) * 0.4)
        p4 = cand_p4[0] if cand_p4 else None
        x4, y4 = (p4["x"], p4["y"]) if p4 else (x_corner, 0.68 * h)

        # P0: Left Outer Top (Band A, leftmost x < x1 - 0.10*w)
        cand_p0 = [d for d in band_a if d["x"] < x1 - 0.10 * w]
        cand_p0 = sorted(cand_p0, key=lambda d: d["x"])
        p0 = cand_p0[0] if cand_p0 else None
        x0, y0 = (p0["x"], p0["y"]) if p0 else (max(0.05 * w, x1 - 0.38 * w), max(0.0, y1 - 0.02 * h))

        # P2: Right Outer Top (Band A, rightmost x > x1 + 0.10*w)
        cand_p2 = [d for d in band_a if d["x"] > x1 + 0.10 * w]
        cand_p2 = sorted(cand_p2, key=lambda d: -d["x"])
        p2 = cand_p2[0] if cand_p2 else None
        x2, y2 = (p2["x"], p2["y"]) if p2 else (min(0.95 * w, x1 + 0.38 * w), max(0.0, y1 - 0.02 * h))

        # P3: Left Outer Base (Band D, deepest floor on left x <= x4)
        cand_p3 = [d for d in band_d if d["x"] <= x4]
        cand_p3 = sorted(cand_p3, key=lambda d: -d["y"])
        p3 = cand_p3[0] if cand_p3 else None
        x3, y3 = (p3["x"], p3["y"]) if p3 else (x0, 0.85 * h)

        # P5: Right Outer Base (Band D, deepest floor on right x >= x4)
        cand_p5 = [d for d in band_d if d["x"] >= x4]
        cand_p5 = sorted(cand_p5, key=lambda d: -d["y"])
        p5 = cand_p5[0] if cand_p5 else None
        x5, y5 = (p5["x"], p5["y"]) if p5 else (x2, 0.85 * h)

        landmarks["outer_left_x"] = round(x0, 1)
        landmarks["corner_crease_x"] = round(x1, 1)
        landmarks["outer_right_x"] = round(x2, 1)
        landmarks["top_apex_y"] = round(y1, 1)
        landmarks["tub_apex_y"] = round(y4, 1)
        landmarks["y_front_base"] = round(max(y3, y5), 1)
        landmarks["candidates"] = candidates

        points = [
            [x0, y0],  # 0: Left Wall Top (Front outer ceiling)
            [x1, y1],  # 1: Corner Top (Center corner apex)
            [x2, y2],  # 2: Right Wall Top (Front outer ceiling)
            [x3, y3],  # 3: Left Wall Tub Rim / Floor Base
            [x4, y4],  # 4: Corner Bottom / Tub Apex
            [x5, y5],  # 5: Right Wall Tub Rim / Floor Base
        ]

        matched_count = sum(1 for p in (p0, p1, p2, p3, p4, p5) if p is not None)
        confidence = round(0.60 + (matched_count / 6.0) * 0.35, 2)
        return points, confidence, landmarks
