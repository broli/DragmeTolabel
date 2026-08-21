"""
Rule 3 & 4: Elevation Monotonicity & Tub Base Offset.
Enforces strict vertical top-to-bottom layering: Ceiling < Header < Tub Rim < Floor Apron.
"""

from __future__ import annotations

from .base_rule import GeometricRule, RuleResult
from .config import DEFAULT_RULE_CONFIG, CVRuleConfig


class ElevationMonotonicityRule(GeometricRule):
    @property
    def rule_id(self) -> str:
        return "elevation_monotonicity"

    @property
    def description(self) -> str:
        return "Enforces physical vertical hierarchy: Y_ceiling < Y_header < Y_tub_rim < Y_floor_base."

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

        h = float(img_height)
        y0, y1, y2, y3 = points[0][1], points[1][1], points[2][1], points[3][1]
        y4, y5, y6, y7 = points[4][1], points[5][1], points[6][1], points[7][1]

        violations = []

        # Left column sequence: Y0 < Y1 < Y5 < Y4
        if y0 >= y1:
            violations.append(f"Left ceiling (Y0={y0:.1f}) is below or equal to header (Y1={y1:.1f})")
        if y1 >= y5:
            violations.append(f"Left header (Y1={y1:.1f}) is below or equal to tub rim (Y5={y5:.1f})")
        if y5 >= y4:
            violations.append(f"Left tub rim (Y5={y5:.1f}) is below or equal to floor base (Y4={y4:.1f})")

        # Right column sequence: Y3 < Y2 < Y6 < Y7
        if y3 >= y2:
            violations.append(f"Right ceiling (Y3={y3:.1f}) is below or equal to header (Y2={y2:.1f})")
        if y2 >= y6:
            violations.append(f"Right header (Y2={y2:.1f}) is below or equal to tub rim (Y6={y6:.1f})")
        if y6 >= y7:
            violations.append(f"Right tub rim (Y6={y6:.1f}) is below or equal to floor base (Y7={y7:.1f})")

        # Minimum Tub to Floor Apron Drop (Soft penalty for low curb pans, hard prune on true inversion)
        min_drop = config.tub_to_floor_min_offset_ratio * h
        left_drop = y4 - y5
        right_drop = y7 - y6
        if left_drop < min_drop:
            violations.append(f"Left floor apron drop ({left_drop:.1f}px) is less than min ({min_drop:.1f}px)")
        if right_drop < min_drop:
            violations.append(f"Right floor apron drop ({right_drop:.1f}px) is less than min ({min_drop:.1f}px)")

        has_inversion = (y0 >= y1) or (y1 >= y5) or (y5 > y4) or (y3 >= y2) or (y2 >= y6) or (y6 > y7)
        passed = len(violations) == 0
        hard_pruned = has_inversion
        score = 1.0 if passed else max(0.5, 1.0 - (len(violations) * 0.15))

        reason = "Passed: Vertical elevations satisfy physical monotonicity" if passed else "; ".join(violations)

        return RuleResult(
            rule_id=self.rule_id,
            passed=passed,
            score=round(score, 3),
            is_hard_pruned=hard_pruned,
            reason=reason,
            details={
                "left_elevations": [round(y, 1) for y in (y0, y1, y5, y4)],
                "right_elevations": [round(y, 1) for y in (y3, y2, y6, y7)],
                "min_tub_floor_drop_px": round(min_drop, 1),
                "violations_count": len(violations),
            },
        )
