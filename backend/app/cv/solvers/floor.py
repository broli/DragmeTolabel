"""
Modular Floor Surface geometry definition and specialized CV auto-fit solver.
Detects wall-floor baseboard seam and receding side wall perspective for ground plane mesh.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ...core.schemas import PolygonPlane, PresetDefinition
from ..geometry_utils import subpixel_peak_1d
from ..perspective import LineSegment
from .base import BasePresetSolver
from .registry import register_solver

FLOOR_PRESET = PresetDefinition(
    id="floor",
    name="Floor Surface",
    description="Standard 4-point quadrilateral floor plane with ground perspective.",
    point_count=4,
    line_count=4,
    enabled=True,
    default_normalized_points=[
        [0.15, 0.58],  # 0: Top-left
        [0.85, 0.58],  # 1: Top-right
        [0.95, 0.94],  # 2: Bottom-right
        [0.05, 0.94],  # 3: Bottom-left
    ],
    lines=[
        [0, 1],
        [1, 2],
        [2, 3],
        [3, 0],
    ],
    planes=[
        PolygonPlane(
            id="floor_plane",
            name="Floor Plane",
            point_indices=[0, 1, 2, 3],
        )
    ],
)


@register_solver("floor")
class FloorSolver(BasePresetSolver):
    """
    Specialized solver for 4-point floor ground planes.
    """

    @property
    def preset_definition(self) -> PresetDefinition:
        return FLOOR_PRESET

    def find_optimal_mesh(
        self,
        img_bgr: np.ndarray,
        lines: list[LineSegment],
    ) -> tuple[list[list[float]], float, dict[str, Any]]:
        h, w = img_bgr.shape[:2]
        confidence_factors: list[float] = []
        landmarks: dict[str, Any] = {}

        # 1. Detect Wall-Floor Baseboard Seam (Y_baseboard)
        h_profile, y_start, _ = self.compute_horizontal_energy_profile(img_bgr, 0.40, 0.80)
        peak_idx = int(np.argmax(h_profile))
        peak_val = float(h_profile[peak_idx])
        mean_val = float(np.mean(h_profile)) + 1e-5
        ratio = peak_val / mean_val

        if ratio > 1.35:
            refined_idx = subpixel_peak_1d(h_profile, peak_idx)
            y_baseboard = y_start + refined_idx
            confidence_factors.append(min(0.88, 0.55 + ratio * 0.1))
            landmarks["baseboard_source"] = "horizontal_sobel_profile"
        else:
            y_baseboard = 0.58 * h
            confidence_factors.append(0.50)
            landmarks["baseboard_source"] = "default_perspective"

        landmarks["baseboard_y"] = round(y_baseboard, 1)

        # 2. Baseboard Width & Receding Angles
        # Top-left and Top-right recede inward from screen edges
        top_inset = 0.15 * w
        bottom_inset = 0.05 * w

        x_tl = top_inset
        x_tr = w - top_inset
        x_br = w - bottom_inset
        x_bl = bottom_inset

        y_bottom = min(0.96 * h, h - 10.0)

        points = [
            [x_tl, y_baseboard],  # 0: Top-left
            [x_tr, y_baseboard],  # 1: Top-right
            [x_br, y_bottom],  # 2: Bottom-right
            [x_bl, y_bottom],  # 3: Bottom-left
        ]

        overall_confidence = float(np.mean(confidence_factors)) if confidence_factors else 0.55
        return points, overall_confidence, landmarks
