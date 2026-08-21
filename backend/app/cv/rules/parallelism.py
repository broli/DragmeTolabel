"""
Rule 1: Back Wall Parallelism & Slant Alignment.
The top edge (P1->P2) and tub rim edge (P5->P6) must share matching tilt angles in perspective.
"""

from __future__ import annotations

import math

from .base_rule import GeometricRule, RuleResult
from .config import DEFAULT_RULE_CONFIG, CVRuleConfig


class BackWallParallelismRule(GeometricRule):
    @property
    def rule_id(self) -> str:
        return "back_wall_parallelism"

    @property
    def description(self) -> str:
        return "Back wall top header (P1->P2) and tub rim (P5->P6) must be parallel within perspective tolerance."

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

        p1, p2 = points[1], points[2]
        p5, p6 = points[5], points[6]

        angle_top = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))
        angle_bot = math.degrees(math.atan2(p6[1] - p5[1], p6[0] - p5[0]))
        angle_diff = abs(angle_top - angle_bot)

        passed = angle_diff <= config.max_back_wall_angle_diff_deg
        hard_pruned = angle_diff > config.hard_prune_back_wall_angle_diff_deg
        score = max(0.0, min(1.0, 1.0 - (angle_diff / max(1.0, config.hard_prune_back_wall_angle_diff_deg))))

        reason = (
            f"Passed: Angle diff is {angle_diff:.1f} deg (<= {config.max_back_wall_angle_diff_deg} deg)"
            if passed
            else f"Back wall top ({angle_top:.1f} deg) and bottom ({angle_bot:.1f} deg) diverge by {angle_diff:.1f} deg"
        )

        return RuleResult(
            rule_id=self.rule_id,
            passed=passed,
            score=round(score, 3),
            is_hard_pruned=hard_pruned,
            reason=reason,
            details={
                "angle_top_deg": round(angle_top, 2),
                "angle_bot_deg": round(angle_bot, 2),
                "angle_diff_deg": round(angle_diff, 2),
                "max_allowed_deg": config.max_back_wall_angle_diff_deg,
            },
        )
