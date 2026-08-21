#!/usr/bin/env python3
"""
CLI Tool for Batch Photo Library Diagnostic Audit.
Creates a timestamped run folder (e.g., docs/reports/cv_diagnostics/run_YYYY-MM-DD_HH-MM-SS/)
containing 3-panel multi-candidate visual composites, summary metrics JSON, and a markdown report.
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from backend.app.cv.perspective import (
    estimate_vanishing_point,
    estimate_vertical_creases,
    extract_structural_lines,
)
from backend.app.cv.rules.config import DEFAULT_RULE_CONFIG, CVRuleConfig
from backend.app.cv.solvers.alcove_bath import AlcoveBathSolver


def create_multi_panel_diagnostic(
    img_bgr: np.ndarray,
    lines: list[Any],
    vp: tuple[float, float],
    creases: list[float],
    candidates: list[dict[str, Any]],
    selected_points: list[list[float]],
    landmarks: dict[str, Any],
    rule_report: dict[str, Any],
    photo_name: str,
    output_path: str,
) -> dict[str, Any]:
    """
    Renders a 3-panel side-by-side diagnostic composite image:
    1. Raw Lines & Raw Candidate Dots
    2. Rule Filters, Hardware Deadband, & Kept Candidate Pools
    3. Fitted Preset Mesh, Surface Planes, & Geometric Proportions
    """
    h, w = img_bgr.shape[:2]
    vp_x, vp_y = vp

    scale = min(1.0, 1400.0 / max(h, w))
    dw, dh = int(w * scale), int(h * scale)
    base_resized = cv2.resize(img_bgr, (dw, dh), interpolation=cv2.INTER_AREA)

    # -------------------------------------------------------------------------
    # Panel 1: What the Computer Sees (Raw Lines & All Candidate Dots)
    # -------------------------------------------------------------------------
    p1 = base_resized.copy()
    p1 = cv2.addWeighted(p1, 0.65, np.zeros_like(p1), 0.35, 0)

    color_map = {
        "vertical": (0, 255, 0),
        "horizontal": (0, 255, 255),
        "left_receding": (255, 150, 0),
        "right_receding": (255, 0, 255),
    }
    for line in lines:
        c = color_map.get(line.category, (180, 180, 180))
        pt1 = (int(line.x1 * scale), int(line.y1 * scale))
        pt2 = (int(line.x2 * scale), int(line.y2 * scale))
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
        f"1. Raw Lines ({len(lines)}) & Raw Dots ({len(candidates)})",
        (10, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (255, 255, 255),
        1,
    )

    # -------------------------------------------------------------------------
    # Panel 2: Rule Filter & Discard Audit
    # -------------------------------------------------------------------------
    p2 = base_resized.copy()
    p2 = cv2.addWeighted(p2, 0.60, np.zeros_like(p2), 0.40, 0)

    # Deadband overlay
    d_top, d_bot = int(0.35 * dh), int(0.56 * dh)
    overlay = p2.copy()
    cv2.rectangle(overlay, (0, d_top), (dw, d_bot), (0, 0, 100), -1)
    p2 = cv2.addWeighted(overlay, 0.30, p2, 0.70, 0)
    cv2.putText(
        p2,
        "HARDWARE DEADBAND (Faucets/Valves Discarded)",
        (10, int((d_top + d_bot) / 2)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (100, 100, 255),
        1,
    )

    for b_y, label in [(0.16 * dh, "Ceiling"), (0.35 * dh, "Header"), (0.76 * dh, "Tub Rim"), (0.98 * dh, "Floor")]:
        cv2.line(p2, (0, int(b_y)), (dw, int(b_y)), (100, 120, 100), 1, cv2.LINE_AA)
        cv2.putText(p2, label, (dw - 65, int(b_y) - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (120, 150, 120), 1)

    for crease in creases:
        cx_s = int(crease * scale)
        if 0 <= cx_s < dw:
            cv2.line(p2, (cx_s, 0), (cx_s, dh), (0, 255, 120), 1, cv2.LINE_AA)

    kept_count = 0
    discarded_count = 0
    for dot in candidates:
        cx, cy = int(dot["x"] * scale), int(dot["y"] * scale)
        if 0 <= cx < dw and 0 <= cy < dh:
            if dot.get("status") == "DISCARDED":
                discarded_count += 1
                r = 4
                cv2.line(p2, (cx - r, cy - r), (cx + r, cy + r), (0, 0, 240), 1)
                cv2.line(p2, (cx - r, cy + r), (cx + r, cy - r), (0, 0, 240), 1)
            elif dot.get("status") == "KEPT":
                kept_count += 1
                cv2.circle(p2, (cx, cy), 3, (0, 240, 100), -1)

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

    # -------------------------------------------------------------------------
    # Panel 3: Fitted Preset Mesh & Geometry Distortion Analysis
    # -------------------------------------------------------------------------
    p3 = base_resized.copy()

    plane_overlay = p3.copy()
    alcove_planes = [
        ([0, 1, 5, 4], (180, 100, 0)),
        ([1, 2, 6, 5], (0, 180, 100)),
        ([2, 3, 7, 6], (100, 0, 180)),
    ]
    for p_indices, color in alcove_planes:
        pts = np.array(
            [[int(selected_points[i][0] * scale), int(selected_points[i][1] * scale)] for i in p_indices],
            dtype=np.int32,
        )
        cv2.fillPoly(plane_overlay, [pts], color)
    p3 = cv2.addWeighted(plane_overlay, 0.35, p3, 0.65, 0)

    alcove_lines = [[0, 1], [1, 2], [2, 3], [0, 4], [1, 5], [2, 6], [3, 7], [4, 5], [5, 6], [6, 7]]
    for p1_idx, p2_idx in alcove_lines:
        pt1 = (int(selected_points[p1_idx][0] * scale), int(selected_points[p1_idx][1] * scale))
        pt2 = (int(selected_points[p2_idx][0] * scale), int(selected_points[p2_idx][1] * scale))
        cv2.line(p3, pt1, pt2, (255, 255, 0), 2, cv2.LINE_AA)

    for idx, pt in enumerate(selected_points):
        px, py = int(pt[0] * scale), int(pt[1] * scale)
        cv2.circle(p3, (px, py), 6, (0, 0, 255), -1)
        cv2.circle(p3, (px, py), 8, (255, 255, 255), 1)
        cv2.putText(p3, f"P{idx}", (px + 7, py - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    bw_top = math.hypot(selected_points[2][0] - selected_points[1][0], selected_points[2][1] - selected_points[1][1])
    bh_l = math.hypot(selected_points[5][0] - selected_points[1][0], selected_points[5][1] - selected_points[1][1])
    bh_r = math.hypot(selected_points[6][0] - selected_points[2][0], selected_points[6][1] - selected_points[2][1])
    back_aspect = round(bw_top / max(1.0, (bh_l + bh_r) / 2.0), 2)
    score = rule_report.get("composite_score", 0.0)

    cv2.rectangle(p3, (0, 0), (dw, 32), (30, 30, 30), -1)
    cv2.putText(
        p3,
        f"3. Mesh (Aspect: {back_aspect} | Score: {score:.2f})",
        (10, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (255, 255, 255),
        1,
    )

    # Combine Panels
    composite = np.hstack([p1, p2, p3])
    full_banner = np.zeros((40, composite.shape[1], 3), dtype=np.uint8)
    cv2.putText(
        full_banner,
        f"Photo: {photo_name} ({w}x{h} px) - CV Diagnostic & Rule Audit",
        (20, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
    )
    composite = np.vstack([full_banner, composite])

    cv2.imwrite(output_path, composite)
    return {
        "photo_name": photo_name,
        "width": w,
        "height": h,
        "raw_lines": len(lines),
        "total_candidates": len(candidates),
        "kept_candidates": kept_count,
        "discarded_candidates": discarded_count,
        "back_wall_aspect": back_aspect,
        "selected_points": selected_points,
        "rule_evaluation": rule_report,
    }


def run_audit(
    library_dir: Path = Path("tests/fixtures/bath_photos"),
    base_output_dir: Path = Path("docs/reports/cv_diagnostics"),
    config: CVRuleConfig = DEFAULT_RULE_CONFIG,
) -> Path:
    """
    Executes a full batch audit run across all photos, saving into a dated directory.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = base_output_dir / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    valid_extensions = {".jpg", ".jpeg", ".png"}
    photos = sorted([f for f in library_dir.iterdir() if f.suffix.lower() in valid_extensions])

    if not photos:
        print(f"No photos found in {library_dir}")
        return run_dir

    print("============================================================")
    print(f"Starting CV Diagnostic Audit Run: {run_dir.name}")
    print(f"Found {len(photos)} photos in {library_dir}")
    print("============================================================")

    solver = AlcoveBathSolver(config=config)
    audit_results: list[dict[str, Any]] = []

    for photo_path in photos:
        img = cv2.imread(str(photo_path))
        if img is None:
            continue

        h, w = img.shape[:2]
        lines = extract_structural_lines(img, min_length=18.0)
        vp = estimate_vanishing_point(lines, w, h)
        creases = estimate_vertical_creases(lines, w, min_length_ratio=0.03, min_peak_distance=max(30.0, 0.035 * w))

        # Solve mesh
        res = solver.solve(img)
        landmarks = res.landmarks
        rule_eval = res.debug_info.get("rule_evaluation", {})

        # Extract and evaluate candidates for diagnostic panels
        elevation_bands = {
            "Band_A_Ceiling": (config.band_ceiling_y_min_ratio * h, config.band_ceiling_y_max_ratio * h),
            "Band_B_BackTop": (config.band_header_y_min_ratio * h, config.band_header_y_max_ratio * h),
            "Band_C_BackTub": (config.band_tub_rim_y_min_ratio * h, config.band_tub_rim_y_max_ratio * h),
            "Band_D_FrontBase": (config.band_floor_y_min_ratio * h, config.band_floor_y_max_ratio * h),
        }
        raw_candidates = solver.extract_all_candidate_dots(img, lines, vp)
        evaluated_candidates, _ = solver.evaluate_rules_and_filter_candidates(
            raw_candidates, img.shape, vp, elevation_bands
        )

        out_img_name = f"audit_{photo_path.stem}.jpg"
        out_img_path = str(run_dir / out_img_name)

        metrics = create_multi_panel_diagnostic(
            img_bgr=img,
            lines=lines,
            vp=vp,
            creases=creases,
            candidates=evaluated_candidates,
            selected_points=res.points,
            landmarks=landmarks,
            rule_report=rule_eval,
            photo_name=photo_path.name,
            output_path=out_img_path,
        )
        audit_results.append(metrics)
        print(
            f"  [PROCESSED] {photo_path.name:<35} | Dots: {len(evaluated_candidates):<4} | Score: {rule_eval.get('composite_score', 0.0):.2f} -> {out_img_name}"
        )

    # 1. Save summary metrics JSON
    metrics_path = run_dir / "summary_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(audit_results, f, indent=2)

    # 2. Save Markdown Report
    report_md_path = run_dir / "report.md"
    with open(report_md_path, "w") as f:
        f.write(f"# CV Diagnostic Audit Report: {run_dir.name}\n\n")
        f.write(f"- **Timestamp**: `{timestamp}`\n")
        f.write(f"- **Total Photos Audited**: `{len(audit_results)}`\n\n")
        f.write("## Summary Table\n\n")
        f.write("| Photo Name | Dimensions | Lines | Candidates | Kept | Discarded | Back Aspect | Score | Valid |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for r in audit_results:
            reval = r.get("rule_evaluation", {})
            f.write(
                f"| {r['photo_name']} | {r['width']}x{r['height']} | {r['raw_lines']} | "
                f"{r['total_candidates']} | {r['kept_candidates']} | {r['discarded_candidates']} | "
                f"{r['back_wall_aspect']} | {reval.get('composite_score', 0.0):.2f} | "
                f"{'YES' if reval.get('is_valid', True) else 'NO'} |\n"
            )
        f.write("\n## Generated Diagnostic Images\n\n")
        for r in audit_results:
            img_file = f"audit_{Path(r['photo_name']).stem}.jpg"
            f.write(f"- [{img_file}]({img_file})\n")

    # 3. Update 'latest' Symlink or Copy
    latest_dir = base_output_dir / "latest"
    try:
        if latest_dir.is_symlink() or latest_dir.exists():
            if latest_dir.is_symlink():
                latest_dir.unlink()
            elif latest_dir.is_dir():
                import shutil

                shutil.rmtree(latest_dir)
        os.symlink(run_dir.name, latest_dir, target_is_directory=True)
    except Exception:
        pass

    print("============================================================")
    print("Audit completed successfully!")
    print(f"Saved results to: {run_dir}")
    print("============================================================\n")
    return run_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run batch CV diagnostic audit on bath photos.")
    parser.add_argument("--library-dir", type=str, default="tests/fixtures/bath_photos")
    parser.add_argument("--output-dir", type=str, default="docs/reports/cv_diagnostics")
    args = parser.parse_args()

    run_audit(
        library_dir=Path(args.library_dir),
        base_output_dir=Path(args.output_dir),
    )
