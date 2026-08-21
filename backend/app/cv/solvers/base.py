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
from ..image_utils import encode_image_base64
from ..perspective import LineSegment, extract_structural_lines
from ..rules import DEFAULT_RULE_CONFIG, CVRuleConfig, MeshRuleEvaluator


class BasePresetSolver(ABC):
    """
    Abstract Base Class for all preset geometry solvers.
    Each architectural surface implements its own specialized landmark detection
    and topological fitting logic while inheriting shared CV utilities.
    """

    def __init__(self, config: CVRuleConfig | None = None) -> None:
        self.config: CVRuleConfig = config or DEFAULT_RULE_CONFIG
        self.rule_evaluator: MeshRuleEvaluator = MeshRuleEvaluator(config=self.config)

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
        Specialized solver implementation returning (points, confidence, landmarks).
        """
        pass

    def solve(self, img_bgr: np.ndarray) -> AutoFitResponse:
        """
        Executes the full automated landmark detection pipeline for this preset:
        1. Extract structural lines and perspective geometry.
        2. Detect surface boundaries and wall junctions.
        3. Clamp coordinates and verify topological convexity.
        4. Evaluate against geometric & architectural rules.
        5. Generate debug heatmap and timing metrics.
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

            # 5. Evaluate mesh against geometric and architectural rule engine
            eval_report = self.rule_evaluator.evaluate_mesh(clamped_points, w, h)
            if not eval_report.is_valid:
                landmarks["rule_warnings"] = eval_report.hard_pruned_reasons

            # Weight confidence by rule composite score
            confidence = round(0.4 * confidence + 0.6 * eval_report.composite_score, 3)

            # 6. Extract candidate dots if returned in landmarks
            candidates = landmarks.get("candidates", [])

            # 7. Generate Visual Debug Heatmap Overlay
            heatmap_b64 = self.generate_debug_heatmap(img_bgr, landmarks, clamped_points, lines, candidates)

            # 8. Detailed Debug Tuning Metrics
            debug_info = {
                "image_width": w,
                "image_height": h,
                "detected_lines_count": len(lines),
                "lines": lines,
                "landmarks": landmarks,
                "confidence_score": round(confidence, 3),
                "normalized_points": [[round(p[0] / w, 4), round(p[1] / h, 4)] for p in clamped_points],
                "rule_evaluation": eval_report.to_dict(),
                "candidates": candidates,
            }
            if candidates:
                debug_info["candidate_dots_count"] = len(candidates)
                debug_info["candidates_kept"] = sum(1 for c in candidates if c.get("status") == "KEPT")
                debug_info["candidates_discarded"] = sum(1 for c in candidates if c.get("status") == "DISCARDED")

            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return AutoFitResponse(
                success=True,
                preset_id=self.preset_definition.id,
                points=clamped_points,
                confidence=round(confidence, 3),
                execution_time_ms=round(elapsed_ms, 2),
                landmarks=landmarks,
                heatmap_base64=heatmap_b64,
                debug_info=debug_info,
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            # Graceful fallback to default preset points on unexpected CV error
            default_pts = self.default_pixel_points(w, h)
            return AutoFitResponse(
                success=True,
                preset_id=self.preset_definition.id,
                points=default_pts,
                confidence=0.30,
                execution_time_ms=round(elapsed_ms, 2),
                landmarks={"fallback": "error", "error_details": str(exc)},
                debug_info={"error": str(exc)},
                message=f"CV solver encountered an issue: {exc}. Using adaptive default.",
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

    def extract_all_candidate_dots(
        self,
        img_bgr: np.ndarray,
        lines: list[LineSegment],
        vp: tuple[float, float] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Multi-source candidate dot generator.
        Extracts 2D junction points from:
        1. Line segment intersections (vertical x horizontal, vertical x receding).
        2. Shi-Tomasi / Harris corner features.
        3. Merges spatial duplicates within adaptive radius.
        """
        import math

        h, w = img_bgr.shape[:2]
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        candidates: list[dict[str, Any]] = []
        dot_id = 0

        # 1. Line Intersection Candidates
        for i in range(len(lines)):
            l1 = lines[i]
            for j in range(i + 1, min(len(lines), i + 45)):
                l2 = lines[j]
                angle_diff = abs(l1.angle_deg - l2.angle_deg)
                if angle_diff < 18.0 or angle_diff > 162.0:
                    continue

                denom = (l1.x1 - l1.x2) * (l2.y1 - l2.y2) - (l1.y1 - l1.y2) * (l2.x1 - l2.x2)
                if abs(denom) < 1e-4:
                    continue

                ix = (
                    (l1.x1 * l1.y2 - l1.y1 * l1.x2) * (l2.x1 - l2.x2)
                    - (l1.x1 - l1.x2) * (l2.x1 * l2.y2 - l2.y1 * l2.x2)
                ) / denom
                iy = (
                    (l1.x1 * l1.y2 - l1.y1 * l1.x2) * (l2.y1 - l2.y2)
                    - (l1.y1 - l1.y2) * (l2.x1 * l2.y2 - l2.y1 * l2.x2)
                ) / denom

                if -0.05 * w <= ix <= 1.05 * w and -0.05 * h <= iy <= 1.05 * h:
                    dist1 = min(math.hypot(ix - l1.x1, iy - l1.y1), math.hypot(ix - l1.x2, iy - l1.y2))
                    dist2 = min(math.hypot(ix - l2.x1, iy - l2.y1), math.hypot(ix - l2.x2, iy - l2.y2))
                    if dist1 < 80.0 or dist2 < 80.0:
                        strength = min(1.0, (l1.length + l2.length) / (0.45 * max(w, h)))
                        candidates.append(
                            {
                                "id": dot_id,
                                "x": round(float(ix), 1),
                                "y": round(float(iy), 1),
                                "source": f"line_intersect({l1.category}x{l2.category})",
                                "strength": round(float(strength), 3),
                                "status": "PENDING",
                                "role": "UNASSIGNED",
                                "discard_reason": "",
                            }
                        )
                        dot_id += 1

        # 2. Shi-Tomasi / Harris Corners
        corners = cv2.goodFeaturesToTrack(
            gray,
            maxCorners=160,
            qualityLevel=0.035,
            minDistance=max(15, int(w * 0.018)),
            blockSize=7,
            useHarrisDetector=True,
            k=0.04,
        )
        if corners is not None:
            for c in corners:
                cx, cy = float(c[0][0]), float(c[0][1])
                candidates.append(
                    {
                        "id": dot_id,
                        "x": round(cx, 1),
                        "y": round(cy, 1),
                        "source": "shi_tomasi_harris",
                        "strength": 0.75,
                        "status": "PENDING",
                        "role": "UNASSIGNED",
                        "discard_reason": "",
                    }
                )
                dot_id += 1

        # 3. Spatial Clustering / Deduplication (Merge radius ~18px)
        merged: list[dict[str, Any]] = []
        used = set()
        for i, c1 in enumerate(candidates):
            if i in used:
                continue
            cluster = [c1]
            for j, c2 in enumerate(candidates[i + 1 :], start=i + 1):
                if j not in used:
                    if math.hypot(c1["x"] - c2["x"], c1["y"] - c2["y"]) < max(18.0, w * 0.015):
                        cluster.append(c2)
                        used.add(j)
            avg_x = sum(c["x"] for c in cluster) / len(cluster)
            avg_y = sum(c["y"] for c in cluster) / len(cluster)
            max_str = max(c["strength"] for c in cluster)
            sources = "+".join(list(set(c["source"].split("(")[0] for c in cluster)))
            merged.append(
                {
                    "id": len(merged),
                    "x": round(avg_x, 1),
                    "y": round(avg_y, 1),
                    "source": sources,
                    "strength": round(max_str, 3),
                    "status": "PENDING",
                    "role": "UNASSIGNED",
                    "discard_reason": "",
                }
            )

        return merged

    def evaluate_rules_and_filter_candidates(
        self,
        candidates: list[dict[str, Any]],
        img_shape: tuple[int, ...],
        vp: tuple[float, float],
        elevation_bands: dict[str, tuple[float, float]],
        deadband_y_range: tuple[float, float] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
        """
        Apply architectural and geometric discard rules:
        - Rule 1: Outside frame boundary
        - Rule 2: Hardware Deadband (relative to wet area ROI or 35% to 56% height)
        - Rule 3: Central Floor Drain / Clutter
        - Rule 4: Elevation Gap (not in any valid structural plane band)
        """
        h, w = img_shape[:2]
        classified_bands: dict[str, list[dict[str, Any]]] = {k: [] for k in elevation_bands.keys()}

        db_min_y, db_max_y = deadband_y_range if deadband_y_range is not None else (
            self.config.deadband_y_min_ratio * h,
            self.config.deadband_y_max_ratio * h,
        )

        for dot in candidates:
            x, y = dot["x"], dot["y"]

            # Rule 1: Out of bounds
            if x < -0.02 * w or x > 1.02 * w or y < -0.02 * h or y > 1.02 * h:
                dot["status"] = "DISCARDED"
                dot["discard_reason"] = "Rule 1: Outside photo boundaries"
                continue

            # Rule 2: Hardware Deadband (faucets, grab bars, valves)
            if db_min_y <= y <= db_max_y:
                dot["status"] = "DISCARDED"
                dot["discard_reason"] = f"Rule 2: Hardware Deadband (Y={y:.0f}px is inside [{db_min_y:.0f}, {db_max_y:.0f}]px hardware zone)"
                continue

            # Rule 3: Central Floor Drain / Clutter
            if y > 0.94 * h and 0.35 * w <= x <= 0.65 * w:
                dot["status"] = "DISCARDED"
                dot["discard_reason"] = f"Rule 3: Central Floor Drain / Clutter (Y={y:.0f}px, center X)"
                continue

            # Rule 4: Match elevation band for graph role assignment
            matched_band = None
            for b_name, (y_min, y_max) in elevation_bands.items():
                if y_min <= y <= y_max:
                    matched_band = b_name
                    classified_bands[matched_band].append(dot)
                    break

            dot["status"] = "KEPT"
            dot["role"] = matched_band if matched_band else "STRUCTURAL_TRANSITION"
            dot["discard_reason"] = "Passed: Valid structural candidate"

        return candidates, classified_bands

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
        sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        sobel_y = np.abs(sobel_y)

        profile = np.mean(sobel_y, axis=1)
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
        sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sobel_x = np.abs(sobel_x)

        profile = np.mean(sobel_x, axis=0)
        smoothed = gaussian_filter1d(profile, sigma=3.0)
        return smoothed, x_start, x_end

    def generate_debug_heatmap(
        self,
        img_bgr: np.ndarray,
        landmarks: dict[str, Any],
        points: list[list[float]],
        lines: list[LineSegment],
        candidates: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        Synthesize a high-precision 2D gradient energy heatmap and guideline overlay.
        Renders candidate dots (Red X: discarded, Green: kept) and final mesh in Cyan.
        """
        h, w = img_bgr.shape[:2]
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # 1. Compute 2D Sobel gradient energy
        sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        magnitude = np.sqrt(sobel_x**2 + sobel_y**2)

        norm_map = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
        color_map = cv2.applyColorMap(norm_map, cv2.COLORMAP_TURBO)

        canvas = cv2.addWeighted(img_bgr, 0.45, color_map, 0.55, 0)

        # 2. Hardware Deadband Overlay
        dead_top = int(0.35 * h)
        dead_bot = int(0.56 * h)
        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, dead_top), (w, dead_bot), (0, 0, 80), -1)
        cv2.putText(
            overlay,
            "HARDWARE DEADBAND",
            (20, int((dead_top + dead_bot) / 2)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (120, 120, 255),
            2,
        )
        canvas = cv2.addWeighted(overlay, 0.25, canvas, 0.75, 0)

        # 3. Draw Candidate Dots if present
        if candidates:
            # Draw discarded candidates in RED X
            for d in candidates:
                pt = (int(d["x"]), int(d["y"]))
                if d.get("status") == "DISCARDED":
                    r = 5
                    cv2.line(canvas, (pt[0] - r, pt[1] - r), (pt[0] + r, pt[1] + r), (0, 0, 240), 2)
                    cv2.line(canvas, (pt[0] - r, pt[1] + r), (pt[0] + r, pt[1] - r), (0, 0, 240), 2)
                elif d.get("status") == "KEPT":
                    cv2.circle(canvas, pt, 4, (0, 230, 100), -1)
                    cv2.circle(canvas, pt, 5, (255, 255, 255), 1)

        # 4. Draw detected landmark guide lines
        for k, v in landmarks.items():
            if isinstance(v, (int, float)):
                if "y" in k or "tub" in k or "header" in k or "baseboard" in k:
                    y_val = int(v)
                    if 0 <= y_val < h:
                        cv2.line(canvas, (0, y_val), (w, y_val), (0, 255, 255), 1)
                elif "x" in k or "crease" in k or "outer" in k:
                    x_val = int(v)
                    if 0 <= x_val < w:
                        color = (0, 255, 0) if "crease" in k else (255, 0, 255)
                        cv2.line(canvas, (x_val, 0), (x_val, h), color, 1)

        # 5. Draw connecting preset lines in bright cyan
        for p1_idx, p2_idx in self.preset_definition.lines:
            if p1_idx < len(points) and p2_idx < len(points):
                pt1 = (int(points[p1_idx][0]), int(points[p1_idx][1]))
                pt2 = (int(points[p2_idx][0]), int(points[p2_idx][1]))
                cv2.line(canvas, pt1, pt2, (255, 255, 0), 2, cv2.LINE_AA)

        # 6. Draw point markers
        for idx, pt in enumerate(points):
            p = (int(pt[0]), int(pt[1]))
            cv2.circle(canvas, p, 8, (0, 0, 255), -1)
            cv2.circle(canvas, p, 10, (255, 255, 255), 2)
            cv2.putText(
                canvas,
                str(idx),
                (p[0] + 12, p[1] + 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

        return encode_image_base64(canvas, format="jpeg", quality=85)
