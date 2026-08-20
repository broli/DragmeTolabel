"""
Manhattan perspective geometry and vanishing point estimation for room photos.
Classifies structural line segments into vertical, horizontal, and perspective-receding rays.
"""

from __future__ import annotations

import math
from typing import NamedTuple

import cv2
import numpy as np

from .geometry_utils import segment_angle_degrees


class LineSegment(NamedTuple):
    x1: float
    y1: float
    x2: float
    y2: float
    length: float
    angle_deg: float
    category: str  # 'vertical' | 'horizontal' | 'left_receding' | 'right_receding'


def extract_structural_lines(
    img_bgr: np.ndarray,
    min_length: float = 25.0,
) -> list[LineSegment]:
    """
    Extract prominent line segments from an image using Line Segment Detector (LSD)
    or Progressive Probabilistic Hough Transform as fallback.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    lines: list[LineSegment] = []

    # 1. Try OpenCV Line Segment Detector
    try:
        lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
        detected, _, _, _ = lsd.detect(gray)
        if detected is not None:
            for d in detected:
                coords = np.asarray(d).flatten()
                if len(coords) >= 4:
                    x1, y1, x2, y2 = float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])
                    length = math.hypot(x2 - x1, y2 - y1)
                    if length >= min_length:
                        angle = segment_angle_degrees((x1, y1), (x2, y2))
                        category = _classify_line_angle(angle)
                        lines.append(LineSegment(x1, y1, x2, y2, length, angle, category))
    except Exception:
        # Fallback to Canny + HoughLinesP
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        hough_lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=40, minLineLength=int(min_length), maxLineGap=10)
        if hough_lines is not None:
            for hl in hough_lines:
                coords = np.asarray(hl).flatten()
                if len(coords) >= 4:
                    x1, y1, x2, y2 = float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])
                    length = math.hypot(x2 - x1, y2 - y1)
                    if length >= min_length:
                        angle = segment_angle_degrees((x1, y1), (x2, y2))
                        category = _classify_line_angle(angle)
                        lines.append(LineSegment(x1, y1, x2, y2, length, angle, category))

    return lines


def _classify_line_angle(angle_deg: float) -> str:
    """
    Classify line segment angle into vertical, horizontal, or perspective receding.
    """
    if 75.0 <= angle_deg <= 105.0:
        return "vertical"
    elif angle_deg <= 15.0 or angle_deg >= 165.0:
        return "horizontal"
    elif 15.0 < angle_deg < 75.0:
        return "right_receding"
    else:
        return "left_receding"


def estimate_vertical_creases(
    lines: list[LineSegment],
    img_width: int,
    min_length_ratio: float = 0.15,
) -> list[float]:
    """
    Find dominant X coordinates of vertical room corners / wall seams.
    Groups near-vertical lines by X coordinate weighted by segment length.
    """
    verticals = [line for line in lines if line.category == "vertical"]
    if not verticals:
        return []

    # Filter by minimum length
    min_len = img_width * min_length_ratio
    prominent = [line for line in verticals if line.length >= min_len]
    if not prominent:
        prominent = verticals

    # 1D Kernel Density / Histogram on mid-X
    x_coords = [(line.x1 + line.x2) / 2.0 for line in prominent]
    weights = [line.length for line in prominent]

    # Cluster within 20px bins
    bins: dict[int, float] = {}
    bin_size = max(10, int(img_width * 0.02))

    for x, w in zip(x_coords, weights, strict=False):
        b = int(round(x / bin_size)) * bin_size
        bins[b] = bins.get(b, 0.0) + w

    sorted_creases = sorted(bins.keys(), key=lambda k: bins[k], reverse=True)
    return [float(c) for c in sorted_creases]
