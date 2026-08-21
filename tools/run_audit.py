#!/usr/bin/env python3
"""
CLI Tool for Batch Photo Library Diagnostic Audit.
Creates a timestamped run folder (e.g., docs/reports/cv_diagnostics/run_YYYY-MM-DD_HH-MM-SS/)
containing 3-panel multi-candidate visual composites, summary metrics JSON, and a markdown report.

Uses the backend CV solver and diagnostics renderer directly with ZERO logic duplication.
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
from pathlib import Path
from typing import Any

import cv2

from backend.app.cv.diagnostics import render_solver_diagnostic_composite
from backend.app.cv.rules.config import DEFAULT_RULE_CONFIG, CVRuleConfig
from backend.app.cv.solvers.alcove_bath import AlcoveBathSolver


def run_audit(
    library_dir: Path = Path("tests/fixtures/bath_photos"),
    base_output_dir: Path = Path("docs/reports/cv_diagnostics"),
    config: CVRuleConfig = DEFAULT_RULE_CONFIG,
) -> Path:
    """
    Executes a full batch audit run across all photos, saving into a dated directory.
    Uses the backend solver directly as the single source of truth.
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

        # 1. Execute Backend Solver (Single Source of Truth)
        res = solver.solve(img)
        landmarks = res.landmarks
        debug_info = res.debug_info or {}
        rule_eval = debug_info.get("rule_evaluation", {})
        candidates = debug_info.get("candidates", [])
        lines = debug_info.get("lines", [])

        # 2. Render Diagnostic Composite directly via Backend Diagnostics Engine
        out_img_name = f"audit_{photo_path.stem}.jpg"
        out_img_path = run_dir / out_img_name
        composite_bgr = render_solver_diagnostic_composite(img, res, solver.preset_definition)
        cv2.imwrite(str(out_img_path), composite_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 92])

        # 3. Check for ground-truth JSON annotation
        json_path = photo_path.with_suffix(".json")
        gt_mean_error = None
        if json_path.exists():
            try:
                with open(json_path) as f:
                    gt_data = json.load(f)
                    gt_points = gt_data.get("points")
                    if gt_points and len(gt_points) == len(res.points):
                        errors = [
                            math.hypot(res.points[i][0] - gt_points[i][0], res.points[i][1] - gt_points[i][1])
                            for i in range(len(gt_points))
                        ]
                        gt_mean_error = round(sum(errors) / len(errors), 1)
            except Exception:
                pass

        score = rule_eval.get("composite_score", res.confidence)
        is_valid = rule_eval.get("is_valid", True)
        back_aspect = rule_eval.get("rule_results", {}).get("aspect_ratio", {}).get("details", {}).get("aspect_ratio", 0.0)

        kept_count = sum(1 for c in candidates if c.get("status") == "KEPT")
        discarded_count = sum(1 for c in candidates if c.get("status") == "DISCARDED")

        print(
            f"  [PROCESSED] {photo_path.name:<32} | Dots: {len(candidates):<4} | Score: {score:.2f}  -> {out_img_name}"
        )

        audit_results.append(
            {
                "photo_name": photo_path.name,
                "width": w,
                "height": h,
                "lines_count": len(lines),
                "total_candidates": len(candidates),
                "kept_candidates": kept_count,
                "discarded_candidates": discarded_count,
                "back_wall_aspect": back_aspect,
                "composite_score": score,
                "is_valid": is_valid,
                "gt_mean_error": gt_mean_error,
                "selected_points": res.points,
                "landmarks": landmarks,
                "rule_evaluation": rule_eval,
            }
        )

    # Write summary JSON
    summary_path = run_dir / "summary_metrics.json"
    with open(summary_path, "w") as f:
        json.dump(
            {
                "timestamp": timestamp,
                "run_dir": str(run_dir),
                "photos_audited": len(audit_results),
                "results": audit_results,
            },
            f,
            indent=2,
        )

    # Write Markdown Report
    generate_markdown_report(run_dir, timestamp, audit_results)

    # Update latest symlink
    latest_link = base_output_dir / "latest"
    try:
        if latest_link.is_symlink() or latest_link.exists():
            latest_link.unlink()
        latest_link.symlink_to(run_dir.resolve(), target_is_directory=True)
    except Exception:
        pass

    print("============================================================")
    print("Audit completed successfully!")
    print(f"Saved results to: {run_dir}")
    print("============================================================")
    return run_dir


def generate_markdown_report(run_dir: Path, timestamp: str, results: list[dict[str, Any]]) -> None:
    """
    Generates a clear summary markdown report for the audit run.
    """
    lines = [
        f"# CV Diagnostic Audit Report: run_{timestamp}",
        "",
        f"- **Timestamp**: `{timestamp}`",
        f"- **Total Photos Audited**: `{len(results)}`",
        "",
        "## Summary Table",
        "",
        "| Photo Name | Dimensions | Lines | Candidates | Kept | Discarded | Back Aspect | GT Mean Err | Score | Valid |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for r in results:
        gt_err_str = f"{r['gt_mean_error']} px" if r["gt_mean_error"] is not None else "N/A"
        valid_str = "YES" if r["is_valid"] else "NO"
        lines.append(
            f"| {r['photo_name']} | {r['width']}x{r['height']} | {r['lines_count']} | {r['total_candidates']} | "
            f"{r['kept_candidates']} | {r['discarded_candidates']} | {r['back_wall_aspect']:.2f} | {gt_err_str} | "
            f"{r['composite_score']:.2f} | {valid_str} |"
        )

    lines.extend([
        "",
        "## Generated Diagnostic Images",
        "",
    ])

    for r in results:
        out_name = f"audit_{Path(r['photo_name']).stem}.jpg"
        lines.append(f"- [{out_name}]({out_name})")

    lines.append("")

    report_path = run_dir / "report.md"
    with open(report_path, "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DragMeToLabel Photo Library CV Diagnostic Audit Tool")
    parser.add_argument(
        "--library-dir",
        type=Path,
        default=Path("tests/fixtures/bath_photos"),
        help="Path to the directory containing bathroom test photos.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/reports/cv_diagnostics"),
        help="Base directory where dated run reports and audit images will be saved.",
    )
    args = parser.parse_args()
    run_audit(library_dir=args.library_dir, base_output_dir=args.output_dir)
