"""
Centralized Diagnostic Composite Visualizer.
Directly visualizes the exact output, detected lines, candidate dots, dynamic rules,
and fitted polygons produced by the Computer Vision backend solver with ZERO duplication.
"""

from __future__ import annotations

import cv2
import numpy as np

from ..core.schemas import AutoFitResponse, PresetDefinition


def render_solver_diagnostic_composite(
    img_bgr: np.ndarray,
    response: AutoFitResponse,
    preset: PresetDefinition | None = None,
    max_dim: int = 1400,
) -> np.ndarray:
    """
    Renders a unified 3-panel side-by-side diagnostic composite image strictly from
    the solver's actual AutoFitResponse:
    - Panel 1: Raw Lines, Candidate Dots, and Central Vanishing Point
    - Panel 2: Rule Filter, Dynamic Deadband, Dynamic Elevation Bands, & Discard Audit
    - Panel 3: Fitted Preset Mesh, Surface Planes, and Geometric Quality Score
    """
    h, w = img_bgr.shape[:2]
    scale = min(1.0, float(max_dim) / max(h, w))
    dw, dh = int(w * scale), int(h * scale)
    base_resized = cv2.resize(img_bgr, (dw, dh), interpolation=cv2.INTER_AREA)

    landmarks = response.landmarks or {}
    debug_info = response.debug_info or {}
    rule_eval = debug_info.get("rule_evaluation", {})
    candidates = debug_info.get("candidates", [])
    raw_lines = debug_info.get("lines", [])
    selected_points = response.points or []

    vp_x = float(landmarks.get("vp_x", w / 2.0))
    vp_y = float(landmarks.get("vp_y", h / 2.0))

    # =========================================================================
    # Panel 1: What the Computer Sees (Raw Lines & Raw Candidate Dots)
    # =========================================================================
    p1 = base_resized.copy()
    p1 = cv2.addWeighted(p1, 0.65, np.zeros_like(p1), 0.35, 0)

    color_map = {
        "vertical": (0, 255, 0),
        "horizontal": (0, 255, 255),
        "left_receding": (255, 150, 0),
        "right_receding": (255, 0, 255),
    }

    for l_data in raw_lines:
        if isinstance(l_data, dict):
            cat = l_data.get("category", "other")
            x1, y1 = l_data.get("x1", 0), l_data.get("y1", 0)
            x2, y2 = l_data.get("x2", 0), l_data.get("y2", 0)
        else:
            cat = getattr(l_data, "category", "other")
            x1, y1 = getattr(l_data, "x1", 0), getattr(l_data, "y1", 0)
            x2, y2 = getattr(l_data, "x2", 0), getattr(l_data, "y2", 0)

        c = color_map.get(cat, (180, 180, 180))
        pt1 = (int(x1 * scale), int(y1 * scale))
        pt2 = (int(x2 * scale), int(y2 * scale))
        cv2.line(p1, pt1, pt2, c, 1, cv2.LINE_AA)

    for dot in candidates:
        cx, cy = int(dot["x"] * scale), int(dot["y"] * scale)
        if 0 <= cx < dw and 0 <= cy < dh:
            cv2.circle(p1, (cx, cy), 3, (255, 255, 255), -1)
            cv2.circle(p1, (cx, cy), 4, (0, 0, 0), 1)

    vpx_s, vpy_s = int(vp_x * scale), int(vp_y * scale)
    if 0 <= vpx_s < dw and 0 <= vpy_s < dh:
        cv2.drawMarker(p1, (vpx_s, vpy_s), (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
        cv2.putText(
            p1, f"VP ({vp_x:.0f},{vp_y:.0f})", (vpx_s + 8, vpy_s - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1
        )

    cv2.rectangle(p1, (0, 0), (dw, 32), (30, 30, 30), -1)
    cv2.putText(
        p1,
        f"1. Raw Lines ({len(raw_lines)}) & Raw Dots ({len(candidates)})",
        (10, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (255, 255, 255),
        1,
    )

    # =========================================================================
    # Panel 2: Rule Filter & Discard Audit
    # =========================================================================
    p2 = base_resized.copy()
    p2 = cv2.addWeighted(p2, 0.60, np.zeros_like(p2), 0.40, 0)

    # Dynamic Deadband Overlay from backend
    db_range = landmarks.get("deadband_y_range")
    if db_range:
        d_top, d_bot = int(db_range[0] * scale), int(db_range[1] * scale)
        overlay = p2.copy()
        cv2.rectangle(overlay, (0, d_top), (dw, d_bot), (0, 0, 100), -1)
        p2 = cv2.addWeighted(overlay, 0.30, p2, 0.70, 0)
        cv2.putText(
            p2,
            f"HARDWARE DEADBAND ({int(db_range[0])}px - {int(db_range[1])}px)",
            (10, int((d_top + d_bot) / 2)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (100, 100, 255),
            1,
        )

    # Dynamic Elevation Bands from backend
    elevation_bands = landmarks.get("elevation_bands")
    if elevation_bands:
        for b_name, (y_min, y_max) in elevation_bands.items():
            y_s = int(y_max * scale)
            label = b_name.replace("Band_", "").replace("_", " ")
            cv2.line(p2, (0, y_s), (dw, y_s), (100, 120, 100), 1, cv2.LINE_AA)
            cv2.putText(p2, label, (dw - 110, y_s - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (120, 150, 120), 1)

    # Plot Kept and Discarded Candidate Dots with Rule Color-Coding
    kept_count = 0
    discarded_count = 0
    reason_counts: dict[str, int] = {}

    for dot in candidates:
        cx, cy = int(dot["x"] * scale), int(dot["y"] * scale)
        if 0 <= cx < dw and 0 <= cy < dh:
            if dot.get("status") == "DISCARDED":
                discarded_count += 1
                reason = dot.get("discard_reason", "")
                r = 4

                # Color-code discard reasons:
                if "Hardware Deadband" in reason:
                    color = (0, 0, 255)  # Red: Hardware Deadband
                    tag = "Deadband"
                elif "Elevation gap" in reason:
                    color = (0, 140, 255)  # Orange: Elevation Gap (floating between bands)
                    tag = "ElevationGap"
                elif "Floor Drain" in reason or "Clutter" in reason:
                    color = (255, 0, 255)  # Magenta: Floor Drain / Clutter
                    tag = "FloorClutter"
                else:
                    color = (180, 180, 180)  # Gray: Outside boundary / other
                    tag = "Other"

                reason_counts[tag] = reason_counts.get(tag, 0) + 1
                cv2.line(p2, (cx - r, cy - r), (cx + r, cy + r), color, 1, cv2.LINE_AA)
                cv2.line(p2, (cx - r, cy + r), (cx + r, cy - r), color, 1, cv2.LINE_AA)
            elif dot.get("status") == "KEPT":
                kept_count += 1
                cv2.circle(p2, (cx, cy), 3, (0, 240, 100), -1)

    # Top Header Bar
    cv2.rectangle(p2, (0, 0), (dw, 32), (30, 30, 30), -1)
    cv2.putText(
        p2,
        f"2. Filter: Kept ({kept_count}) | Discarded ({discarded_count})",
        (10, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (255, 255, 255),
        1,
    )

    # Bottom Legend Bar
    cv2.rectangle(p2, (0, dh - 26), (dw, dh), (20, 20, 20), -1)
    cv2.putText(
        p2,
        "Legend: [O] Kept | [X Red] Deadband | [X Orange] Elev Gap | [X Magenta] Floor Drain",
        (8, dh - 8),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.36,
        (200, 200, 200),
        1,
    )

    # =========================================================================
    # Panel 3: Fitted Preset Mesh & Geometry Distortion Analysis
    # =========================================================================
    p3 = base_resized.copy()
    plane_overlay = p3.copy()

    # Color palette for planes
    plane_colors = [
        (180, 100, 0),    # Left Wall (Cyan/Blue tint)
        (0, 180, 100),    # Back Wall (Green/Lime tint)
        (180, 0, 180),    # Right Wall (Magenta/Pink tint)
        (0, 140, 255),    # Floor/Tub
    ]

    planes = preset.planes if (preset and preset.planes) else []
    for idx, plane in enumerate(planes):
        color = plane_colors[idx % len(plane_colors)]
        plane_pts = np.array(
            [[int(selected_points[p_idx][0] * scale), int(selected_points[p_idx][1] * scale)] for p_idx in plane.point_indices if p_idx < len(selected_points)],
            dtype=np.int32,
        )
        if len(plane_pts) >= 3:
            cv2.fillPoly(plane_overlay, [plane_pts], color)

    p3 = cv2.addWeighted(plane_overlay, 0.40, p3, 0.60, 0)

    # Draw mesh connecting lines
    lines_def = preset.lines if (preset and preset.lines) else []
    for line_pair in lines_def:
        idx1, idx2 = line_pair
        if idx1 < len(selected_points) and idx2 < len(selected_points):
            pt1 = (int(selected_points[idx1][0] * scale), int(selected_points[idx1][1] * scale))
            pt2 = (int(selected_points[idx2][0] * scale), int(selected_points[idx2][1] * scale))
            cv2.line(p3, pt1, pt2, (255, 255, 255), 2, cv2.LINE_AA)

    # Draw vertices with IDs
    for idx, pt in enumerate(selected_points):
        px, py = int(pt[0] * scale), int(pt[1] * scale)
        cv2.circle(p3, (px, py), 6, (0, 0, 255), -1)
        cv2.circle(p3, (px, py), 7, (255, 255, 255), 1)
        cv2.putText(p3, f"P{idx}", (px + 6, py - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)

    score = rule_eval.get("composite_score", response.confidence)
    back_aspect = 0.0
    if len(selected_points) >= 8:
        bw = abs(selected_points[2][0] - selected_points[1][0])
        bh = abs(selected_points[5][1] - selected_points[1][1])
        back_aspect = bw / max(1.0, bh)
    elif "aspect_ratio" in rule_eval.get("rule_results", {}):
        back_aspect = rule_eval["rule_results"]["aspect_ratio"].get("details", {}).get("aspect_ratio", 0.0)

    cv2.rectangle(p3, (0, 0), (dw, 32), (30, 30, 30), -1)
    cv2.putText(
        p3,
        f"3. Mesh (Aspect: {back_aspect:.2f} | Score: {score:.2f})",
        (10, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (255, 255, 255),
        1,
    )

    # Combine 3 panels horizontally with title header
    composite_body = np.hstack([p1, p2, p3])
    header = np.zeros((40, composite_body.shape[1], 3), dtype=np.uint8)
    preset_name = preset.name if preset else response.preset_id
    cv2.putText(
        header,
        f"Backend CV Solver Diagnostic: {preset_name} ({w}x{h} px) - Composite Score: {score:.2f}",
        (15, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        1,
    )

    return np.vstack([header, composite_body])
