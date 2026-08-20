"""
Modular Ceiling Surface geometry definition and specialized CV auto-fit solver.
Detects crown molding / wall-ceiling perimeter for overhead quadrilateral mesh.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ...core.schemas import PolygonPlane, PresetDefinition
from ..geometry_utils import subpixel_peak_1d
from ..perspective import LineSegment
from .base import BasePresetSolver
from .registry import register_solver

CEILING_PRESET = PresetDefinition(
    id="ceiling",
    name="Ceiling Surface",
    description="Standard 4-point quadrilateral ceiling plane with overhead perspective.",
    point_count=4,
    line_count=4,
    enabled=True,
    default_normalized_points=[
        [0.05, 0.06],  # 0: Top-left
        [0.95, 0.06],  # 1: Top-right
        [0.85, 0.42],  # 2: Bottom-right
        [0.15, 0.42],  # 3: Bottom-left
    ],
    lines=[
        [0, 1],
        [1, 2],
        [2, 3],
        [3, 0],
    ],
    planes=[
        PolygonPlane(
            id="ceiling_plane",
            name="Ceiling Plane",
            point_indices=[0, 1, 2, 3],
        )
    ],
)


@register_solver("ceiling")
class CeilingSolver(BasePresetSolver):
    """
    Specialized solver for 4-point overhead ceiling planes.
    """

    @property
    def preset_definition(self) -> PresetDefinition:
        return CEILING_PRESET

    def find_optimal_mesh(
        self,
        img_bgr: np.ndarray,
        lines: list[LineSegment],
    ) -> tuple[list[list[float]], float, dict[str, Any]]:
        h, w = img_bgr.shape[:2]
        confidence_factors: list[float] = []
        landmarks: dict[str, Any] = {}

        # 1. Detect Wall-Ceiling Crown Molding Seam (Y_molding)
        h_profile, y_start, _ = self.compute_horizontal_energy_profile(img_bgr, 0.20, 0.55)
        peak_idx = int(np.argmax(h_profile))
        peak_val = float(h_profile[peak_idx])
        mean_val = float(np.mean(h_profile)) + 1e-5
        ratio = peak_val / mean_val

        if ratio > 1.35:
            refined_idx = subpixel_peak_1d(h_profile, peak_idx)
            y_molding = y_start + refined_idx
            confidence_factors.append(min(0.88, 0.55 + ratio * 0.1))
        else:
            y_molding = 0.42 * h
            confidence_factors.append(0.50)

        landmarks["crown_molding_y"] = round(y_molding, 1)

        y_top = max(10.0, 0.05 * h)
        top_inset = 0.05 * w
        bottom_inset = 0.15 * w

        points = [
            [top_inset, y_top],  # 0: Top-left
            [w - top_inset, y_top],  # 1: Top-right
            [w - bottom_inset, y_molding],  # 2: Bottom-right
            [bottom_inset, y_molding],  # 3: Bottom-left
        ]

        overall_confidence = float(np.mean(confidence_factors)) if confidence_factors else 0.50
        return points, overall_confidence, landmarks
