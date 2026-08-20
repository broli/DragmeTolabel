"""
Modular Cali Bath (Walk-in Shower) geometry definition and specialized CV auto-fit solver.
Modular placeholder ready for upcoming walk-in shower geometry and threshold detectors.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ...core.schemas import PresetDefinition
from ..perspective import LineSegment
from .base import BasePresetSolver
from .registry import register_solver

CALI_BATH_PRESET = PresetDefinition(
    id="cali_bath",
    name="Cali Bath",
    description="California walk-in shower configuration (In Development).",
    point_count=0,
    line_count=0,
    enabled=False,
    default_normalized_points=[],
    lines=[],
    planes=[],
)


@register_solver("cali_bath")
class CaliBathSolver(BasePresetSolver):
    """
    Modular solver for California walk-in shower configurations.
    """

    @property
    def preset_definition(self) -> PresetDefinition:
        return CALI_BATH_PRESET

    def find_optimal_mesh(
        self,
        img_bgr: np.ndarray,
        lines: list[LineSegment],
    ) -> tuple[list[list[float]], float, dict[str, Any]]:
        # Currently disabled/in development
        return [], 0.0, {"status": "in_development"}
