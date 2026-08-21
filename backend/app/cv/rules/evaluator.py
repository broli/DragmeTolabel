"""
Composite Mesh Rule Evaluator.
Aggregates individual geometric and architectural rules, performs hard-pruning,
and computes a weighted composite quality score for candidate meshes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .aspect_ratio import AspectRatioRule
from .base_rule import GeometricRule, RuleResult
from .config import DEFAULT_RULE_CONFIG, CVRuleConfig
from .elevation import ElevationMonotonicityRule
from .parallelism import BackWallParallelismRule
from .relative_crease import RelativeCreaseTiltAndKeystoneRule
from .vanishing_ray import VanishingRayConvergenceRule


@dataclass
class MeshEvaluationReport:
    """
    Complete audit report from evaluating a candidate polygon mesh against all rules.
    """

    is_valid: bool
    composite_score: float  # [0.0, 1.0]
    rule_results: dict[str, RuleResult] = field(default_factory=dict)
    hard_pruned_reasons: list[str] = field(default_factory=list)
    failed_rules: list[str] = field(default_factory=list)
    passed_rules: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "composite_score": round(self.composite_score, 3),
            "passed_rules_count": len(self.passed_rules),
            "failed_rules_count": len(self.failed_rules),
            "hard_pruned_reasons": self.hard_pruned_reasons,
            "rule_breakdown": {
                k: {
                    "passed": v.passed,
                    "score": v.score,
                    "is_hard_pruned": v.is_hard_pruned,
                    "reason": v.reason,
                    "details": v.details,
                }
                for k, v in self.rule_results.items()
            },
        }


class MeshRuleEvaluator:
    """
    Orchestrates the evaluation of candidate meshes against registered geometric rules.
    """

    def __init__(
        self,
        config: CVRuleConfig = DEFAULT_RULE_CONFIG,
        rules: list[GeometricRule] | None = None,
    ):
        self.config = config
        self.rules: list[GeometricRule] = rules or [
            BackWallParallelismRule(),
            RelativeCreaseTiltAndKeystoneRule(),
            ElevationMonotonicityRule(),
            VanishingRayConvergenceRule(),
            AspectRatioRule(),
        ]

    def evaluate_mesh(
        self,
        points: list[list[float]],
        img_width: int,
        img_height: int,
    ) -> MeshEvaluationReport:
        """
        Evaluate candidate mesh vertices against all registered rules.
        """
        rule_results: dict[str, RuleResult] = {}
        hard_pruned_reasons: list[str] = []
        passed_rules: list[str] = []
        failed_rules: list[str] = []

        total_weight = 0.0
        weighted_score_sum = 0.0

        for rule in self.rules:
            result = rule.evaluate(points, img_width, img_height, self.config)
            rule_results[rule.rule_id] = result

            weight = self.config.weights.get(rule.rule_id, 0.15)
            total_weight += weight
            weighted_score_sum += result.score * weight

            if result.is_hard_pruned:
                hard_pruned_reasons.append(f"[{rule.rule_id}] {result.reason}")

            if result.passed:
                passed_rules.append(rule.rule_id)
            else:
                failed_rules.append(rule.rule_id)

        composite_score = weighted_score_sum / max(1e-5, total_weight)
        is_valid = len(hard_pruned_reasons) == 0

        # If hard pruned, clamp score to low value
        if not is_valid:
            composite_score = min(0.30, composite_score * 0.5)

        return MeshEvaluationReport(
            is_valid=is_valid,
            composite_score=round(composite_score, 3),
            rule_results=rule_results,
            hard_pruned_reasons=hard_pruned_reasons,
            failed_rules=failed_rules,
            passed_rules=passed_rules,
        )
