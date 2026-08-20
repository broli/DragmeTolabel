"""
Abstract Base Class for modular geometry preset solvers.
Provides shared CV feature extraction pipelines, energy profiles,
convexity verification, and timing lifecycle for all geometry types.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d

from ...core.schemas import AutoFitResponse, PresetDefinition
from ..geometry_utils import clamp_point_to_bounds, is_quadrilateral_convex
from ..perspective import LineSegment, extract_structural_lines


class BasePresetSolver(ABC):
    """
    Abstract Base Class for all preset geometry solvers.
    Each architectural surface implements its own specialized landmark detection
    and topological fitting logic while inheriting shared CV utilities.
    """

    @property
    @abstractmethod
    def preset_definition(self) -> PresetDefinition:
        """
        The PresetDefinition metadata, lines, and plane topologies for this geometry.
        """
        pass

    @abstractmethod
    def find_optimal_mesh(
        self,
        img_bgr: np.ndarray,
        lines: list[LineSegment],
    ) -> tuple[list[list[float]], float, dict[str, Any]]:
        """
        Solve for the optimal polygon vertex coordinates in image pixel coordinates.

        Returns:
            points: List of [x, y] coordinates in pixel space matching preset point_count.
            confidence: Overall fit confidence score [0.0, 1.0].
            landmarks: Dictionary of detected architectural landmarks.
        """
        pass

    def solve(self, img_bgr: np.ndarray) -> AutoFitResponse:
        """
        Execute the end-to-end auto-fitting pipeline with timing and safety validation.
        """
        t0 = time.perf_counter()
        h, w = img_bgr.shape[:2]

        if not self.preset_definition.enabled or self.preset_definition.point_count == 0:
            return AutoFitResponse(
                success=False,
                preset_id=self.preset_definition.id,
                points=[],
                confidence=0.0,
                execution_time_ms=(time.perf_counter() - t0) * 1000.0,
                message=f"Preset '{self.preset_definition.id}' is disabled or in development.",
            )

        try:
            # 1. Extract structural line segments
            lines = extract_structural_lines(img_bgr)

            # 2. Specialized modular solver execution
            points, confidence, landmarks = self.find_optimal_mesh(img_bgr, lines)

            # 3. Clamp points safely within image bounds
            clamped_points = [clamp_point_to_bounds(p[0], p[1], w, h) for p in points]

            # 4. Topology & convexity safety verification
            is_valid = self.validate_planes_convexity(clamped_points)
            if not is_valid:
                # If solver produced an inverted polygon, fallback gracefully to default perspective
                clamped_points = self.default_pixel_points(w, h)
                confidence = max(0.25, confidence * 0.5)
                landmarks["fallback_reason"] = "Topology convexity violation detected; reverted to adaptive default."

            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return AutoFitResponse(
                success=True,
                preset_id=self.preset_definition.id,
                points=clamped_points,
                confidence=round(confidence, 3),
                execution_time_ms=round(elapsed_ms, 2),
                landmarks=landmarks,
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            # Graceful fallback to default preset points on unexpected CV error
            fallback_pts = self.default_pixel_points(w, h)
            return AutoFitResponse(
                success=True,
                preset_id=self.preset_definition.id,
                points=fallback_pts,
                confidence=0.20,
                execution_time_ms=round(elapsed_ms, 2),
                landmarks={"error": str(exc)},
                message=f"Auto-fit solver encountered an error; used default layout: {exc}",
            )

    def default_pixel_points(self, width: int, height: int) -> list[list[float]]:
        """
        Scale preset's normalized [0, 1] coordinates to actual image pixel coordinates.
        """
        pts: list[list[float]] = []
        for nx, ny in self.preset_definition.default_normalized_points:
            pts.append([round(nx * width, 1), round(ny * height, 1)])
        return pts

    def validate_planes_convexity(self, points: list[list[float]]) -> bool:
        """
        Ensure every quadrilateral plane defined in preset topology is strictly convex.
        """
        for plane in self.preset_definition.planes:
            if len(plane.point_indices) == 4:
                if not is_quadrilateral_convex(points, plane.point_indices):
                    return False
        return True

    # =========================================================================
    # Shared CV Utility Methods for Concrete Solvers
    # =========================================================================

    def compute_horizontal_energy_profile(
        self,
        img_bgr: np.ndarray,
        y_min_ratio: float = 0.20,
        y_max_ratio: float = 0.90,
    ) -> tuple[np.ndarray, int, int]:
        """
        Collapse horizontal edge gradients across rows to produce a 1D vertical profile.
        Sharp peaks correspond to baseboard seams, tub rims, or ceiling molding.
        """
        h, w = img_bgr.shape[:2]
        y_start = int(h * y_min_ratio)
        y_end = int(h * y_max_ratio)

        roi = img_bgr[y_start:y_end, :]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        # Sobel Y detects horizontal transitions
        sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        sobel_y = np.abs(sobel_y)

        # Average energy across columns
        profile = np.mean(sobel_y, axis=1)
        # 1D Gaussian smoothing to remove texture noise
        smoothed = gaussian_filter1d(profile, sigma=3.0)
        return smoothed, y_start, y_end

    def compute_vertical_energy_profile(
        self,
        img_bgr: np.ndarray,
        x_min_ratio: float = 0.15,
        x_max_ratio: float = 0.85,
    ) -> tuple[np.ndarray, int, int]:
        """
        Collapse vertical edge gradients across columns to produce a 1D horizontal profile.
        Sharp peaks correspond to vertical room corners, shower frame edges, or wall creases.
        """
        h, w = img_bgr.shape[:2]
        x_start = int(w * x_min_ratio)
        x_end = int(w * x_max_ratio)

        roi = img_bgr[:, x_start:x_end]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        # Sobel X detects vertical transitions
        sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sobel_x = np.abs(sobel_x)

        # Average energy across rows
        profile = np.mean(sobel_x, axis=0)
        # 1D Gaussian smoothing
        smoothed = gaussian_filter1d(profile, sigma=3.0)
        return smoothed, x_start, x_end
