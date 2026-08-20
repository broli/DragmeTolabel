"""
Geometric and mathematical utilities for DragMeToLabel CV solvers.
Provides robust line intersections, quadrilateral convexity verification,
Shoelace polygon area computation, and sub-pixel peak interpolation.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def intersect_lines(
    p1: Sequence[float],
    p2: Sequence[float],
    p3: Sequence[float],
    p4: Sequence[float],
) -> tuple[float, float] | None:
    """
    Calculate the intersection point of two infinite 2D lines defined by (p1, p2) and (p3, p4).
    Returns (x, y) or None if the lines are parallel or degenerate.
    """
    x1, y1 = float(p1[0]), float(p1[1])
    x2, y2 = float(p2[0]), float(p2[1])
    x3, y3 = float(p3[0]), float(p3[1])
    x4, y4 = float(p4[0]), float(p4[1])

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-7:
        return None

    t_num = (x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)
    t = t_num / denom

    ix = x1 + t * (x2 - x1)
    iy = y1 + t * (y2 - y1)
    return (ix, iy)


def is_quadrilateral_convex(
    points: Sequence[Sequence[float]],
    indices: Sequence[int] = (0, 1, 2, 3),
) -> bool:
    """
    Test whether a quadrilateral formed by 4 ordered vertices in clockwise or counter-clockwise
    order is strictly convex and non-self-intersecting using 2D cross-product signs.
    """
    if len(indices) != 4:
        return False

    pts = [points[i] for i in indices]
    signs = []

    for i in range(4):
        p_prev = pts[(i - 1) % 4]
        p_curr = pts[i]
        p_next = pts[(i + 1) % 4]

        dx1 = p_curr[0] - p_prev[0]
        dy1 = p_curr[1] - p_prev[1]
        dx2 = p_next[0] - p_curr[0]
        dy2 = p_next[1] - p_curr[1]

        cross = dx1 * dy2 - dy1 * dx2
        if abs(cross) < 1e-5:
            # Degenerate collinear segment
            return False
        signs.append(cross > 0)

    # All cross products must share the same sign
    return all(signs) or not any(signs)


def polygon_area(points: Sequence[Sequence[float]]) -> float:
    """
    Calculate the 2D polygon area using the Shoelace formula (Gauss's area formula).
    """
    n = len(points)
    if n < 3:
        return 0.0

    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += float(points[i][0]) * float(points[j][1])
        area -= float(points[j][0]) * float(points[i][1])

    return abs(area) / 2.0


def clamp_point_to_bounds(
    x: float,
    y: float,
    width: int | float,
    height: int | float,
    margin: float = 2.0,
) -> list[float]:
    """
    Clamp coordinate (x, y) within image bounds with safety margin.
    """
    cx = max(margin, min(float(width) - margin, float(x)))
    cy = max(margin, min(float(height) - margin, float(y)))
    return [round(cx, 1), round(cy, 1)]


def subpixel_peak_1d(array: Sequence[float], center_idx: int) -> float:
    """
    Refine a 1D local peak index using 3-point quadratic parabolic vertex interpolation.
    y = a*x^2 + b*x + c -> peak_offset = (y_left - y_right) / (2 * (y_left - 2*y_mid + y_right))
    """
    n = len(array)
    if center_idx <= 0 or center_idx >= n - 1:
        return float(center_idx)

    y_left = float(array[center_idx - 1])
    y_mid = float(array[center_idx])
    y_right = float(array[center_idx + 1])

    denom = 2.0 * (y_left - 2.0 * y_mid + y_right)
    if abs(denom) < 1e-6:
        return float(center_idx)

    offset = (y_left - y_right) / denom
    # Clamp offset to [-0.8, 0.8] to prevent runaway interpolation
    offset = max(-0.8, min(0.8, offset))
    return float(center_idx) + offset


def segment_angle_degrees(p1: Sequence[float], p2: Sequence[float]) -> float:
    """
    Compute angle in degrees [0, 180) of line segment relative to horizontal axis.
    """
    dx = float(p2[0]) - float(p1[0])
    dy = float(p2[1]) - float(p1[1])
    angle = math.degrees(math.atan2(dy, dx)) % 180.0
    return angle
