"""
Stage 2: Upward Vertical Perspective Extrusion Pipeline Module.
Extrudes vertical rays upward from base footprint corners (P4, P5, P6, P7) to find back wall creases and outer jambs.
"""

from __future__ import annotations

import math
from typing import Any

from ..perspective import LineSegment


def compute_upward_vertical_rays(
    p4: list[float],
    p5: list[float],
    p6: list[float],
    p7: list[float],
    lines: list[LineSegment],
    vp: tuple[float, float],
    img_shape: tuple[int, ...],
) -> dict[str, Any]:
    """
    Extrudes 4 perspective vertical rays upward from the 4 ground corners:
    - Ray 1 (Outer Left Drywall): From P4 pointing upward
    - Ray 2 (Back Left Crease): From P5 pointing upward
    - Ray 3 (Back Right Crease): From P6 pointing upward
    - Ray 4 (Outer Right Drywall): From P7 pointing upward
    """
    h, w = img_shape[:2]
    vp_x, vp_y = vp
    vert_lines = [seg for seg in lines if seg.category == "vertical"]

    def find_best_ray_slope(base_pt: list[float], is_outer: bool, is_left: bool) -> tuple[float, float]:
        """
        Finds the directional vector (dx, dy) pointing upward (dy < 0).
        """
        bx, by = base_pt
        # Find nearby vertical segments within 6% of image width
        near_lines = [seg for seg in vert_lines if abs((seg.x1 + seg.x2) / 2.0 - bx) <= 0.06 * w]
        if near_lines:
            dx_sum = 0.0
            dy_sum = 0.0
            total_len = 0.0
            for seg in near_lines:
                # Point vector from lower point (higher Y) to upper point (lower Y)
                if seg.y1 > seg.y2:
                    dx = seg.x2 - seg.x1
                    dy = seg.y2 - seg.y1
                else:
                    dx = seg.x1 - seg.x2
                    dy = seg.y1 - seg.y2
                dx_sum += dx * seg.length
                dy_sum += dy * seg.length
                total_len += seg.length

            if total_len > 0 and abs(dy_sum) > 1e-3:
                tilt_ratio = dx_sum / dy_sum  # dy_sum is negative
                if abs(tilt_ratio) < 0.20:  # <= ~11 degrees tilt
                    norm = math.hypot(dx_sum, dy_sum)
                    return (dx_sum / norm, dy_sum / norm)

        # Default upward vertical ray
        return (0.0, -1.0)

    return {
        "ray_outer_l": {"origin": p4, "dir": find_best_ray_slope(p4, is_outer=True, is_left=True)},
        "ray_crease_l": {"origin": p5, "dir": find_best_ray_slope(p5, is_outer=False, is_left=True)},
        "ray_crease_r": {"origin": p6, "dir": find_best_ray_slope(p6, is_outer=False, is_left=False)},
        "ray_outer_r": {"origin": p7, "dir": find_best_ray_slope(p7, is_outer=True, is_left=False)},
    }
