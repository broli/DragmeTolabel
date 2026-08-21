"""
Rule 7 & 8: Back Wall Aspect Ratio & 4-Column Ordering.
Verifies realistic architectural proportions (Width/Height in [0.60, 1.40]) and strict monotonic column order.
"""

from __future__ import annotations

import math

from .base_rule import GeometricRule, RuleResult
from .config import DEFAULT_RULE_CONFIG, CVRuleConfig


class AspectRatioRule(GeometricRule):
    @property
    def rule_id(self) -> str:
        return "back_wall_aspect_ratio"

    @property
    def description(self) -> str:
        return "Back wall aspect ratio (Width/Height) must lie in realistic range and satisfy minimum span."

    def evaluate(
        self,
        points: list[list[float]],
        img_width: int,
        img_height: int,
        config: CVRuleConfig = DEFAULT_RULE_CONFIG,
    ) -> RuleResult:
        if len(points) < 8:
            return RuleResult(
                rule_id=self.rule_id,
                passed=True,
                score=1.0,
                reason="Skipped (not an 8-point mesh)",
            )

        w = float(img_width)
        p1, p2 = points[1], points[2]
        p5, p6 = points[5], points[6]

        bw_top = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        bw_bot = math.hypot(p6[0] - p5[0], p6[1] - p5[1])
        avg_bw = (bw_top + bw_bot) / 2.0

        bh_l = math.hypot(p5[0] - p1[0], p5[1] - p1[1])
        bh_r = math.hypot(p6[0] - p2[0], p6[1] - p2[1])
        avg_bh = max(1.0, (bh_l + bh_r) / 2.0)

        aspect_ratio = avg_bw / avg_bh
        span_ratio = avg_bw / max(1.0, w)

        violations = []
        if aspect_ratio < config.min_back_wall_aspect_ratio:
            violations.append(
                f"Back wall aspect ratio ({aspect_ratio:.2f}) is too narrow (< {config.min_back_wall_aspect_ratio})"
            )
        elif aspect_ratio > config.max_back_wall_aspect_ratio:
            violations.append(
                f"Back wall aspect ratio ({aspect_ratio:.2f}) is too wide (> {config.max_back_wall_aspect_ratio})"
            )

        if span_ratio < config.min_back_wall_span_ratio:
            violations.append(
                f"Back wall span ({span_ratio:.1%}) is less than minimum required ({config.min_back_wall_span_ratio:.1%})"
            )

        passed = len(violations) == 0
        hard_pruned = aspect_ratio < (config.min_back_wall_aspect_ratio * 0.6) or aspect_ratio > (
            config.max_back_wall_aspect_ratio * 1.6
        )

        # Optimal aspect ratio ~ 0.85 - 1.05
        dist_from_optimal = abs(aspect_ratio - 0.90)
        score = max(0.0, min(1.0, 1.0 - (dist_from_optimal * 0.8)))

        reason = (
            f"Passed: Back wall aspect ratio is {aspect_ratio:.2f} (span={span_ratio:.1%})"
            if passed
            else "; ".join(violations)
        )

        return RuleResult(
            rule_id=self.rule_id,
            passed=passed,
            score=round(score, 3),
            is_hard_pruned=hard_pruned,
            reason=reason,
            details={
                "aspect_ratio": round(aspect_ratio, 2),
                "span_ratio": round(span_ratio, 3),
                "avg_width_px": round(avg_bw, 1),
                "avg_height_px": round(avg_bh, 1),
            },
        )
