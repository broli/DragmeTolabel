"""
Geometric and architectural rule engine for DragMeToLabel.
"""

from .aspect_ratio import AspectRatioRule
from .base_rule import GeometricRule, RuleResult
from .config import DEFAULT_RULE_CONFIG, CVRuleConfig
from .elevation import ElevationMonotonicityRule
from .evaluator import MeshEvaluationReport, MeshRuleEvaluator
from .parallelism import BackWallParallelismRule
from .relative_crease import RelativeCreaseTiltAndKeystoneRule
from .vanishing_ray import VanishingRayConvergenceRule

__all__ = [
    "CVRuleConfig",
    "DEFAULT_RULE_CONFIG",
    "GeometricRule",
    "RuleResult",
    "MeshEvaluationReport",
    "MeshRuleEvaluator",
    "BackWallParallelismRule",
    "RelativeCreaseTiltAndKeystoneRule",
    "ElevationMonotonicityRule",
    "VanishingRayConvergenceRule",
    "AspectRatioRule",
]
