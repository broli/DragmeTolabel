"""
Manhattan perspective geometry and vanishing point estimation for room photos.
Classifies structural line segments into vertical, horizontal, and perspective-receding rays.
"""

from __future__ import annotations

import math
from typing import NamedTuple

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks

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
    min_length_ratio: float = 0.05,
    min_peak_distance: float | None = None,
) -> list[float]:
    """
    Find dominant X coordinates of vertical room corners / wall seams.
    Builds a continuous 1D Kernel Density curve across image columns weighted by line length,
    applies Gaussian smoothing, and extracts prominent local peaks using Non-Maximum Suppression (NMS).
    """
    verticals = [line for line in lines if line.category == "vertical"]
    if not verticals:
        return []

    # Filter by minimum length
    min_len = img_width * min_length_ratio
    prominent = [line for line in verticals if line.length >= min_len]
    if not prominent:
        prominent = verticals

    # 1. Build Continuous 1D Density Array
    density = np.zeros(img_width, dtype=np.float32)
    for line in prominent:
        x_mid = int(round((line.x1 + line.x2) / 2.0))
        if 0 <= x_mid < img_width:
            x_min = max(0, x_mid - 2)
            x_max = min(img_width, x_mid + 3)
            density[x_min:x_max] += float(line.length)

    # 2. Gaussian Smoothing for continuous gradient envelope
    sigma = max(8.0, img_width * 0.012)
    smoothed = gaussian_filter1d(density, sigma=sigma)

    max_val = float(np.max(smoothed)) if len(smoothed) > 0 else 0.0
    if max_val <= 1e-5:
        return []

    # 3. Peak Detection with scipy.signal.find_peaks
    dist_thresh = int(min_peak_distance) if min_peak_distance is not None else max(40, int(img_width * 0.04))
    raw_peaks, properties = find_peaks(
        smoothed,
        height=0.05 * max_val,
        distance=dist_thresh,
    )

    peak_heights = properties.get("peak_heights", [])
    if len(peak_heights) == len(raw_peaks):
        sorted_indices = np.argsort(peak_heights)[::-1]
        sorted_peaks = [raw_peaks[idx] for idx in sorted_indices]
    else:
        sorted_peaks = list(raw_peaks)

    return [float(p) for p in sorted_peaks]


def estimate_vanishing_point(
    lines: list[LineSegment],
    img_width: int,
    img_height: int,
) -> tuple[float, float]:
    """
    Estimate dominant central vanishing point from receding perspective lines.
    Falls back to image optical center (W/2, H/2).
    """
    w, h = float(img_width), float(img_height)
    receding = [line for line in lines if line.category in ("left_receding", "right_receding")]
    default_vp = (w * 0.5, h * 0.50)

    if len(receding) < 2:
        return default_vp

    intersections: list[tuple[float, float]] = []
    for i in range(len(receding)):
        for j in range(i + 1, len(receding)):
            l1, l2 = receding[i], receding[j]
            if l1.category != l2.category:
                denom = (l1.x1 - l1.x2) * (l2.y1 - l2.y2) - (l1.y1 - l1.y2) * (l2.x1 - l2.x2)
                if abs(denom) > 1e-4:
                    ix = (
                        (l1.x1 * l1.y2 - l1.y1 * l1.x2) * (l2.x1 - l2.x2)
                        - (l1.x1 - l1.x2) * (l2.x1 * l2.y2 - l2.y1 * l2.x2)
                    ) / denom
                    iy = (
                        (l1.x1 * l1.y2 - l1.y1 * l1.x2) * (l2.y1 - l2.y2)
                        - (l1.y1 - l1.y2) * (l2.x1 * l2.y2 - l2.y1 * l2.x2)
                    ) / denom
                    if 0.15 * w <= ix <= 0.85 * w and 0.20 * h <= iy <= 0.80 * h:
                        intersections.append((ix, iy))

    if intersections:
        med_x = float(np.median([p[0] for p in intersections]))
        med_y = float(np.median([p[1] for p in intersections]))
        return (med_x, med_y)

    return default_vp
