"""
Stage 3: Ceiling & Header Intersections Pipeline Module.
Intersects upward vertical rays with detected ceiling / header lines to lock P0, P1, P2, P3.
"""

from __future__ import annotations

from typing import Any

from ..geometry_utils import intersect_lines
from ..perspective import LineSegment


def solve_ceiling_and_header(
    rays: dict[str, Any],
    lines: list[LineSegment],
    y_header: float,
    img_shape: tuple[int, ...],
) -> dict[str, list[float]]:
    """
    Computes top vertices P0, P1, P2, P3 by intersecting upward vertical rays
    with detected ceiling and header horizontal lines.
    """
    h, w = img_shape[:2]
    horiz_all = [seg for seg in lines if seg.category == "horizontal"]

    # Header line across the back wall
    header_segs = [seg for seg in horiz_all if abs((seg.y1 + seg.y2) / 2.0 - y_header) <= 0.10 * h]
    if header_segs:
        header_segs_sorted = sorted(header_segs, key=lambda s: s.length, reverse=True)
        h_seg = header_segs_sorted[0]
        p_h1 = (h_seg.x1, h_seg.y1)
        p_h2 = (h_seg.x2, h_seg.y2)
    else:
        p_h1 = (0.0, y_header)
        p_h2 = (float(w), y_header)

    # Ceiling line (above header or outer bulkhead)
    ceiling_segs = [seg for seg in horiz_all if (seg.y1 + seg.y2) / 2.0 <= y_header * 0.7]
    if ceiling_segs:
        ceiling_segs_sorted = sorted(ceiling_segs, key=lambda s: s.length, reverse=True)
        c_seg = ceiling_segs_sorted[0]
        p_c1 = (c_seg.x1, c_seg.y1)
        p_c2 = (c_seg.x2, c_seg.y2)
        y_ceil = float((c_seg.y1 + c_seg.y2) / 2.0)
    else:
        y_ceil = max(0.05 * h, y_header * 0.4)
        p_c1 = (0.0, y_ceil)
        p_c2 = (float(w), y_ceil)

    def intersect_ray_with_line(ray_data: dict[str, Any], line_p1: tuple[float, float], line_p2: tuple[float, float]) -> list[float]:
        orig = ray_data["origin"]
        d = ray_data["dir"]
        # Point far along upward ray
        p_ray2 = (orig[0] + d[0] * 2000.0, orig[1] + d[1] * 2000.0)
        res = intersect_lines((orig[0], orig[1]), p_ray2, line_p1, line_p2)
        if res is not None:
            return [round(res[0], 1), round(res[1], 1)]
        # Fallback projection
        t = (line_p1[1] - orig[1]) / (d[1] if abs(d[1]) > 1e-3 else -1.0)
        return [round(orig[0] + d[0] * t, 1), round(line_p1[1], 1)]

    p1 = intersect_ray_with_line(rays["ray_crease_l"], p_h1, p_h2)
    p2 = intersect_ray_with_line(rays["ray_crease_r"], p_h1, p_h2)
    p0 = intersect_ray_with_line(rays["ray_outer_l"], p_c1, p_c2)
    p3 = intersect_ray_with_line(rays["ray_outer_r"], p_c1, p_c2)

    return {
        "p0": p0,
        "p1": p1,
        "p2": p2,
        "p3": p3,
        "y_header": y_header,
        "y_ceiling": y_ceil,
    }
