"""
Stage 1: Base Footprint & Ground Plane Pipeline Module.
Detects floor boundary, tub apron / shower curb, tub rim ledge, and base footprint polygon.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..perspective import LineSegment
from ..rules.config import DEFAULT_RULE_CONFIG, CVRuleConfig


def solve_base_footprint(
    img_bgr: np.ndarray,
    lines: list[LineSegment],
    vp: tuple[float, float],
    creases: list[float],
    config: CVRuleConfig = DEFAULT_RULE_CONFIG,
) -> dict[str, Any]:
    """
    Solves the 3D ground footprint [P4, P5, P6, P7] from the bottom up:
    1. Detects lowest floor boundary line (P4 -> P7).
    2. Identifies base type ('bathtub' vs 'shower_pan') from horizontal line energy.
    3. Finds tub rim / curb ledge horizontal line.
    4. Projects 3D perspective rays from front floor corners to Vanishing Point to lock P5, P6.
    """
    h, w = img_bgr.shape[:2]
    vp_x, vp_y = vp
    x_in_l, x_in_r = creases if len(creases) >= 2 else (0.25 * w, 0.75 * w)

    horiz_all = [seg for seg in lines if seg.category == "horizontal"]

    # 1. Detect Floor Boundary Line (P4 -> P7)
    floor_lines = [seg for seg in horiz_all if (seg.y1 + seg.y2) / 2.0 >= 0.65 * h]
    if floor_lines:
        floor_lines_by_depth = sorted(floor_lines, key=lambda seg: (seg.y1 + seg.y2) / 2.0, reverse=True)
        y_floor = float((floor_lines_by_depth[0].y1 + floor_lines_by_depth[0].y2) / 2.0)
    else:
        y_floor = 0.91 * h

    # 2. Header Line for wet area vertical ROI scaling
    header_lines = [seg for seg in horiz_all if (seg.y1 + seg.y2) / 2.0 <= 0.35 * h]
    y_header = float((header_lines[0].y1 + header_lines[0].y2) / 2.0) if header_lines else 0.20 * h
    h_wet = max(0.40 * h, y_floor - y_header)

    # 3. Base Type Detection (Tub vs Pan)
    tub_lines = [
        seg
        for seg in horiz_all
        if y_header + 0.50 * h_wet
        <= (seg.y1 + seg.y2) / 2.0
        <= y_header + 0.88 * h_wet
    ]
    pan_lines = [
        seg
        for seg in horiz_all
        if y_header + 0.88 * h_wet
        < (seg.y1 + seg.y2) / 2.0
        <= y_floor + 0.05 * h_wet
    ]

    tub_score = sum(seg.length for seg in tub_lines)
    pan_score = sum(seg.length for seg in pan_lines)
    base_type = "bathtub" if (tub_score >= pan_score and tub_lines) else "shower_pan"

    if base_type == "bathtub" and tub_lines:
        tub_lines_sorted = sorted(tub_lines, key=lambda seg: seg.length, reverse=True)
        y_base_target = float((tub_lines_sorted[0].y1 + tub_lines_sorted[0].y2) / 2.0)
    elif base_type == "shower_pan" and pan_lines:
        pan_lines_sorted = sorted(pan_lines, key=lambda seg: seg.length, reverse=True)
        y_base_target = float((pan_lines_sorted[0].y1 + pan_lines_sorted[0].y2) / 2.0)
    else:
        y_base_target = y_header + 0.72 * h_wet if base_type == "bathtub" else y_floor - 0.05 * h_wet

    if base_type == "bathtub" and y_floor <= y_base_target + 0.05 * h:
        y_floor = min(0.95 * h, y_base_target + 0.18 * h)
        h_wet = max(0.40 * h, y_floor - y_header)

    h_back_wall = max(0.25 * h, y_base_target - y_header)

    # 4. Front Base Points P4 (Left) and P7 (Right)
    x4 = max(0.04 * w, x_in_l - 0.15 * w)
    y4 = y_floor
    x7 = min(0.96 * w, x_in_r + 0.15 * w)
    y7 = y_floor

    # 5. Project 3D Perspective Ledge Rays from P4, P7 to Vanishing Point
    y5_target = min(y4 - 0.05 * h, y_base_target)
    y6_target = min(y7 - 0.05 * h, y_base_target)

    denom_l = vp_y - y4
    x5_proj = x4 + (y5_target - y4) * (vp_x - x4) / denom_l if abs(denom_l) > 1e-3 else x_in_l
    denom_r = vp_y - y7
    x6_proj = x7 + (y6_target - y7) * (vp_x - x7) / denom_r if abs(denom_r) > 1e-3 else x_in_r

    return {
        "base_type": base_type,
        "y_floor": y_floor,
        "y_header": y_header,
        "y_base_target": y_base_target,
        "h_wet": h_wet,
        "h_back_wall": h_back_wall,
        "p4_init": [x4, y4],
        "p7_init": [x7, y7],
        "p5_proj": [x5_proj, y5_target],
        "p6_proj": [x6_proj, y6_target],
    }
