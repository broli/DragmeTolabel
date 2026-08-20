"""
Plugin registry for DragMeToLabel modular geometry solvers and preset definitions.
Enables plug-and-play addition of new room/bath geometries with zero coupling.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...core.schemas import PresetDefinition
    from .base import BasePresetSolver

logger = logging.getLogger(__name__)

_SOLVER_REGISTRY: dict[str, type[BasePresetSolver]] = {}
_SOLVER_INSTANCES: dict[str, BasePresetSolver] = {}


def register_solver(preset_id: str) -> Callable[[type[BasePresetSolver]], type[BasePresetSolver]]:
    """
    Decorator to register a geometry solver class with the global SolverRegistry.
    """

    def decorator(cls: type[BasePresetSolver]) -> type[BasePresetSolver]:
        if preset_id in _SOLVER_REGISTRY:
            logger.warning("Overwriting existing solver for preset_id '%s'", preset_id)
        _SOLVER_REGISTRY[preset_id] = cls
        # Clear cached instance
        _SOLVER_INSTANCES.pop(preset_id, None)
        return cls

    return decorator


class SolverRegistry:
    """
    Central registry managing modular geometric solvers and their preset definitions.
    """

    @classmethod
    def get_solver(cls, preset_id: str) -> BasePresetSolver | None:
        """
        Get or instantiate the solver instance for a given preset_id.
        """
        if preset_id in _SOLVER_INSTANCES:
            return _SOLVER_INSTANCES[preset_id]

        solver_cls = _SOLVER_REGISTRY.get(preset_id)
        if solver_cls is None:
            return None

        instance = solver_cls()
        _SOLVER_INSTANCES[preset_id] = instance
        return instance

    @classmethod
    def list_preset_ids(cls) -> list[str]:
        """
        Return list of all registered preset IDs.
        """
        return list(_SOLVER_REGISTRY.keys())

    @classmethod
    def get_all_presets(cls) -> list[PresetDefinition]:
        """
        Collect PresetDefinition objects from all registered modular solvers.
        """
        presets: list[PresetDefinition] = []
        for preset_id in _SOLVER_REGISTRY:
            solver = cls.get_solver(preset_id)
            if solver is not None:
                presets.append(solver.preset_definition)
        return presets

    @classmethod
    def get_preset_by_id(cls, preset_id: str) -> PresetDefinition | None:
        """
        Lookup a PresetDefinition by ID from registered solvers.
        """
        solver = cls.get_solver(preset_id)
        return solver.preset_definition if solver else None
