"""
Rule 2: Relative Crease Tilt & Keystone Alignment.
Models mutual relative tilt (if camera is crooked) and symmetric keystone convergence (if pitched downward).
"""

from __future__ import annotations

import math

from .base_rule import GeometricRule, RuleResult
from .config import DEFAULT_RULE_CONFIG, CVRuleConfig


class RelativeCreaseTiltAndKeystoneRule(GeometricRule):
    @property
    def rule_id(self) -> str:
        return "crease_relative_tilt"

    @property
    def description(self) -> str:
        return "Left and right vertical creases must share matching camera tilt or symmetric perspective keystone."

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

        p1, p5 = points[1], points[5]
        p2, p6 = points[2], points[6]

        dy_l = max(1.0, p5[1] - p1[1])
        dx_l = p5[0] - p1[0]
        tilt_left = math.degrees(math.atan2(dx_l, dy_l))

        dy_r = max(1.0, p6[1] - p2[1])
        dx_r = p6[0] - p2[0]
        tilt_right = math.degrees(math.atan2(dx_r, dy_r))

        # Check A: Mutual Parallel Tilt (camera rotated around roll axis)
        mutual_tilt_diff = abs(tilt_left - tilt_right)

        # Check B: Symmetric Keystone Convergence (camera pitched down/up)
        keystone_sum = abs(tilt_left + tilt_right)

        # Horizontal shear drift
        shear_drift_ratio = abs(dx_l - dx_r) / max(1.0, float(img_width))

        passed = (
            mutual_tilt_diff <= config.max_crease_mutual_tilt_diff_deg
            or keystone_sum <= config.max_keystone_convergence_deg
        ) and shear_drift_ratio <= config.max_crease_shear_ratio

        hard_pruned = (
            mutual_tilt_diff > config.max_crease_mutual_tilt_diff_deg * 2.0
            and keystone_sum > config.max_keystone_convergence_deg * 1.5
        ) or shear_drift_ratio > config.max_crease_shear_ratio * 1.8

        error_metric = min(mutual_tilt_diff, keystone_sum)
        score = max(0.0, min(1.0, 1.0 - (error_metric / (config.max_crease_mutual_tilt_diff_deg * 2.0))))

        reason = (
            f"Passed: Relative crease tilt difference is {mutual_tilt_diff:.1f} deg (shear={shear_drift_ratio:.3f})"
            if passed
            else f"Creases have conflicting tilt angles (left={tilt_left:.1f} deg, right={tilt_right:.1f} deg, shear={shear_drift_ratio:.3f})"
        )

        return RuleResult(
            rule_id=self.rule_id,
            passed=passed,
            score=round(score, 3),
            is_hard_pruned=hard_pruned,
            reason=reason,
            details={
                "tilt_left_deg": round(tilt_left, 2),
                "tilt_right_deg": round(tilt_right, 2),
                "mutual_tilt_diff_deg": round(mutual_tilt_diff, 2),
                "keystone_sum_deg": round(keystone_sum, 2),
                "shear_drift_ratio": round(shear_drift_ratio, 4),
            },
        )
