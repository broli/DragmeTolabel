"""
Rule 6: Sidewall Vanishing Ray Convergence (Anti-Warp).
Verifies that receding sidewall seams converge inward toward the central vanishing region.
"""

from __future__ import annotations

import math

from .base_rule import GeometricRule, RuleResult
from .config import DEFAULT_RULE_CONFIG, CVRuleConfig


class VanishingRayConvergenceRule(GeometricRule):
    @property
    def rule_id(self) -> str:
        return "vanishing_convergence"

    @property
    def description(self) -> str:
        return "Left and right sidewall top and bottom seams must converge inward toward the vanishing perspective."

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

        p0, p1 = points[0], points[1]
        p4, p5 = points[4], points[5]
        p3, p2 = points[3], points[2]
        p7, p6 = points[7], points[6]

        violations = []

        # Left sidewall rays: must move rightward (X1 > X0, X5 > X4)
        if p1[0] <= p0[0]:
            violations.append(f"Left top seam flares outward (X1={p1[0]:.1f} <= X0={p0[0]:.1f})")
        if p5[0] <= p4[0]:
            violations.append(f"Left bottom seam flares outward (X5={p5[0]:.1f} <= X4={p4[0]:.1f})")

        # Right sidewall rays: must move leftward (X2 < X3, X6 < X7)
        if p2[0] >= p3[0]:
            violations.append(f"Right top seam flares outward (X2={p2[0]:.1f} >= X3={p3[0]:.1f})")
        if p6[0] >= p7[0]:
            violations.append(f"Right bottom seam flares outward (X6={p6[0]:.1f} >= X7={p7[0]:.1f})")

        # Slant angle bounds
        angle_l_top = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
        angle_r_top = math.degrees(math.atan2(p2[1] - p3[1], p2[0] - p3[0]))

        passed = len(violations) == 0
        hard_pruned = len(violations) >= 2
        score = 1.0 if passed else max(0.0, 1.0 - (len(violations) * 0.35))

        reason = "Passed: Sidewall perspective rays converge inward" if passed else "; ".join(violations)

        return RuleResult(
            rule_id=self.rule_id,
            passed=passed,
            score=round(score, 3),
            is_hard_pruned=hard_pruned,
            reason=reason,
            details={
                "angle_left_top_deg": round(angle_l_top, 2),
                "angle_right_top_deg": round(angle_r_top, 2),
                "violations": violations,
            },
        )
