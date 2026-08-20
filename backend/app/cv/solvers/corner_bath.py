"""
Modular Corner Bath geometry definition and specialized CV auto-fit solver.
Detects 2-wall corner crease seam, tub rim apex, and surround boundaries for 6-point mesh.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ...core.schemas import PolygonPlane, PresetDefinition
from ..geometry_utils import subpixel_peak_1d
from ..perspective import LineSegment, estimate_vertical_creases
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
        [0.15, 0.18],  # 0: Left Wall Top
        [0.50, 0.12],  # 1: Corner Top
        [0.85, 0.18],  # 2: Right Wall Top
        [0.15, 0.68],  # 3: Left Wall Tub Rim
        [0.50, 0.62],  # 4: Corner Bottom / Tub Apex
        [0.85, 0.68],  # 5: Right Wall Tub Rim
    ],
    lines=[
        [0, 1],  # 1. Left top
        [1, 2],  # 2. Right top
        [0, 3],  # 3. Left outer vertical
        [1, 4],  # 4. Center corner seam
        [2, 5],  # 5. Right outer vertical
        [3, 4],  # 6. Left tub ledge
        [4, 5],  # 7. Right tub ledge
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
        confidence_factors: list[float] = []
        landmarks: dict[str, Any] = {}

        # 1. Detect Central Vertical Corner Crease (X_corner)
        creases = estimate_vertical_creases(lines, w, min_length_ratio=0.18)
        central_creases = [c for c in creases if 0.28 * w <= c <= 0.72 * w]

        if central_creases:
            # Pick strongest central vertical crease
            x_corner = central_creases[0]
            confidence_factors.append(0.88)
            landmarks["crease_source"] = "LSD_vertical_segment"
        else:
            # Profile fallback
            v_profile, x_start, _ = self.compute_vertical_energy_profile(img_bgr, 0.30, 0.70)
            peak_idx = int(np.argmax(v_profile))
            peak_val = float(v_profile[peak_idx])
            mean_val = float(np.mean(v_profile)) + 1e-5
            ratio = peak_val / mean_val

            if ratio > 1.5:
                refined_idx = subpixel_peak_1d(v_profile, peak_idx)
                x_corner = x_start + refined_idx
                confidence_factors.append(min(0.80, 0.50 + ratio * 0.1))
                landmarks["crease_source"] = "sobel_vertical_profile"
            else:
                x_corner = 0.50 * w
                confidence_factors.append(0.40)
                landmarks["crease_source"] = "center_default"

        landmarks["corner_crease_x"] = round(x_corner, 1)

        # 2. Detect Tub Ledge / Apex (Y_tub)
        h_profile, y_start, _ = self.compute_horizontal_energy_profile(img_bgr, 0.45, 0.85)
        tub_peak_idx = int(np.argmax(h_profile))
        tub_peak_val = float(h_profile[tub_peak_idx])
        tub_mean_val = float(np.mean(h_profile)) + 1e-5
        tub_ratio = tub_peak_val / tub_mean_val

        if tub_ratio > 1.4:
            refined_tub_idx = subpixel_peak_1d(h_profile, tub_peak_idx)
            y_tub_apex = y_start + refined_tub_idx
            confidence_factors.append(min(0.85, 0.50 + tub_ratio * 0.1))
            landmarks["tub_ledge_source"] = "sobel_horizontal_profile"
        else:
            y_tub_apex = 0.62 * h
            confidence_factors.append(0.45)
            landmarks["tub_ledge_source"] = "perspective_default"

        landmarks["tub_apex_y"] = round(y_tub_apex, 1)

        # 3. Detect Top Ceiling / Tile Surround Line (Y_top)
        top_profile, top_start, _ = self.compute_horizontal_energy_profile(img_bgr, 0.06, 0.35)
        top_peak_idx = int(np.argmax(top_profile))
        if float(top_profile[top_peak_idx]) / (float(np.mean(top_profile)) + 1e-5) > 1.4:
            refined_top_idx = subpixel_peak_1d(top_profile, top_peak_idx)
            y_top_apex = top_start + refined_top_idx
            confidence_factors.append(0.80)
        else:
            y_top_apex = 0.12 * h
            confidence_factors.append(0.50)

        landmarks["top_apex_y"] = round(y_top_apex, 1)

        # 4. Outer Wall Bounds (X_left, X_right)
        left_creases = [c for c in creases if 0.05 * w <= c < x_corner - 0.15 * w]
        right_creases = [c for c in creases if x_corner + 0.15 * w < c <= 0.95 * w]

        x_left = left_creases[0] if left_creases else max(0.08 * w, x_corner - 0.35 * w)
        x_right = right_creases[0] if right_creases else min(0.92 * w, x_corner + 0.35 * w)

        # 5. Dihedral Perspective Slant for Corner Surround
        # In corner perspective, outer tub ledge and top edges flare slightly downward/upward
        slant_tub = (y_tub_apex - y_top_apex) * 0.08
        slant_top = slant_tub * 0.8

        points = [
            [x_left, y_top_apex + slant_top],  # 0: Left Top
            [x_corner, y_top_apex],  # 1: Corner Top
            [x_right, y_top_apex + slant_top],  # 2: Right Top
            [x_left, y_tub_apex + slant_tub],  # 3: Left Tub Rim
            [x_corner, y_tub_apex],  # 4: Corner Bottom / Tub Apex
            [x_right, y_tub_apex + slant_tub],  # 5: Right Tub Rim
        ]

        overall_confidence = float(np.mean(confidence_factors)) if confidence_factors else 0.50
        return points, overall_confidence, landmarks
