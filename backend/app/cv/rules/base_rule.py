"""
Abstract Base Class for modular geometric and architectural rules.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .config import DEFAULT_RULE_CONFIG, CVRuleConfig


@dataclass
class RuleResult:
    """
    Result of evaluating a geometric or architectural rule on a candidate mesh.
    """

    rule_id: str
    passed: bool
    score: float  # [0.0, 1.0] (1.0 = perfect adherence)
    is_hard_pruned: bool = False
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class GeometricRule(ABC):
    """
    Abstract Base Class for all geometric and physical room rules.
    """

    @property
    @abstractmethod
    def rule_id(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def evaluate(
        self,
        points: list[list[float]],
        img_width: int,
        img_height: int,
        config: CVRuleConfig = DEFAULT_RULE_CONFIG,
    ) -> RuleResult:
        """
        Evaluate candidate mesh vertices [P0..Pn] against the rule.
        """
        pass
