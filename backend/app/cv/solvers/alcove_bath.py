"""
Modular Alcove Bath geometry definition and specialized CV auto-fit solver.
Detects 3-wall recessed alcove boundaries, dual vertical corner creases, and tub surround ledge.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ...core.schemas import PolygonPlane, PresetDefinition
from ..geometry_utils import subpixel_peak_1d
from ..perspective import LineSegment, estimate_vertical_creases
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
        [0.14, 0.16],  # 0: Left-Front Top
        [0.34, 0.22],  # 1: Back-Left Top
        [0.66, 0.22],  # 2: Back-Right Top
        [0.86, 0.16],  # 3: Right-Front Top
        [0.14, 0.72],  # 4: Left-Front Bottom
        [0.34, 0.66],  # 5: Back-Left Tub Rim
        [0.66, 0.66],  # 6: Back-Right Tub Rim
        [0.86, 0.72],  # 7: Right-Front Bottom
    ],
    lines=[
        [0, 1],  # 1. Left wall top
        [1, 2],  # 2. Back wall top
        [2, 3],  # 3. Right wall top
        [0, 4],  # 4. Left front vertical
        [1, 5],  # 5. Back left corner seam
        [2, 6],  # 6. Back right corner seam
        [3, 7],  # 7. Right front vertical
        [4, 5],  # 8. Left bottom ledge
        [5, 6],  # 9. Back tub rim
        [6, 7],  # 10. Right bottom ledge
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
    Specialized solver for 3-wall recessed alcove bathtub surrounds (8 control points).
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
        confidence_factors: list[float] = []
        landmarks: dict[str, Any] = {}

        # 1. Detect Dual Back-Wall Corner Creases (X_back_left, X_back_right)
        creases = estimate_vertical_creases(lines, w, min_length_ratio=0.15)
        # We need two vertical creases in central 60% of image with separation >= 0.20 * w
        left_candidates = [c for c in creases if 0.20 * w <= c <= 0.48 * w]
        right_candidates = [c for c in creases if 0.52 * w <= c <= 0.80 * w]

        if left_candidates:
            x_back_left = left_candidates[0]
            confidence_factors.append(0.85)
        else:
            x_back_left = 0.34 * w
            confidence_factors.append(0.45)

        if right_candidates:
            x_back_right = right_candidates[0]
            confidence_factors.append(0.85)
        else:
            x_back_right = 0.66 * w
            confidence_factors.append(0.45)

        # Enforce minimum back wall span
        if x_back_right - x_back_left < 0.20 * w:
            x_back_left = 0.34 * w
            x_back_right = 0.66 * w

        landmarks["back_crease_left_x"] = round(x_back_left, 1)
        landmarks["back_crease_right_x"] = round(x_back_right, 1)

        # 2. Detect Back Tub Rim (Y_tub)
        h_profile, y_start, _ = self.compute_horizontal_energy_profile(img_bgr, 0.50, 0.85)
        tub_peak_idx = int(np.argmax(h_profile))
        if float(h_profile[tub_peak_idx]) / (float(np.mean(h_profile)) + 1e-5) > 1.4:
            refined_tub_idx = subpixel_peak_1d(h_profile, tub_peak_idx)
            y_tub_back = y_start + refined_tub_idx
            confidence_factors.append(0.85)
        else:
            y_tub_back = 0.66 * h
            confidence_factors.append(0.45)

        landmarks["back_tub_rim_y"] = round(y_tub_back, 1)

        # 3. Detect Top Ceiling / Tile Surround Line (Y_top)
        top_profile, top_start, _ = self.compute_horizontal_energy_profile(img_bgr, 0.10, 0.35)
        top_peak_idx = int(np.argmax(top_profile))
        if float(top_profile[top_peak_idx]) / (float(np.mean(top_profile)) + 1e-5) > 1.4:
            refined_top_idx = subpixel_peak_1d(top_profile, top_peak_idx)
            y_top_back = top_start + refined_top_idx
            confidence_factors.append(0.80)
        else:
            y_top_back = 0.22 * h
            confidence_factors.append(0.50)

        landmarks["back_top_y"] = round(y_top_back, 1)

        # 4. Compute Front Outer Flanges (X_front_left, X_front_right)
        back_width = x_back_right - x_back_left
        flange_offset = max(0.12 * w, back_width * 0.40)
        x_front_left = max(0.06 * w, x_back_left - flange_offset)
        x_front_right = min(0.94 * w, x_back_right + flange_offset)

        # Recessed Perspective Slant: front top is higher, front bottom is lower
        y_span = y_tub_back - y_top_back
        perspective_slant_y = y_span * 0.12

        points = [
            [x_front_left, y_top_back - perspective_slant_y],  # 0: Left-Front Top
            [x_back_left, y_top_back],  # 1: Back-Left Top
            [x_back_right, y_top_back],  # 2: Back-Right Top
            [x_front_right, y_top_back - perspective_slant_y],  # 3: Right-Front Top
            [x_front_left, y_tub_back + perspective_slant_y],  # 4: Left-Front Bottom
            [x_back_left, y_tub_back],  # 5: Back-Left Tub Rim
            [x_back_right, y_tub_back],  # 6: Back-Right Tub Rim
            [x_front_right, y_tub_back + perspective_slant_y],  # 7: Right-Front Bottom
        ]

        overall_confidence = float(np.mean(confidence_factors)) if confidence_factors else 0.50
        return points, overall_confidence, landmarks
