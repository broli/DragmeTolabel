"""
Preset geometry definitions for DragMeToLabel.
Dynamically delegates to the modular cv.solvers.SolverRegistry
while maintaining 100% backward-compatible schemas and dictionary lookups.
"""

from __future__ import annotations

from ..cv.solvers import SolverRegistry
from .schemas import PresetDefinition


def get_all_presets() -> list[PresetDefinition]:
    """
    Retrieve all registered preset definitions from modular geometry solvers.
    """
    return SolverRegistry.get_all_presets()


def get_preset_by_id(preset_id: str) -> PresetDefinition | None:
    """
    Retrieve a specific preset definition by its identifier.
    """
    return SolverRegistry.get_preset_by_id(preset_id)


# Backward-compatible dictionary view
class _PresetsDict(dict):
    def __getitem__(self, key: str) -> PresetDefinition:
        preset = get_preset_by_id(key)
        if preset is None:
            raise KeyError(key)
        return preset

    def get(self, key: str, default: PresetDefinition | None = None) -> PresetDefinition | None:
        preset = get_preset_by_id(key)
        return preset if preset is not None else default

    def values(self):
        return get_all_presets()

    def items(self):
        return [(p.id, p) for p in get_all_presets()]

    def keys(self):
        return [p.id for p in get_all_presets()]

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        return len(get_all_presets())

    def __contains__(self, key: object) -> bool:
        if isinstance(key, str):
            return get_preset_by_id(key) is not None
        return False


PRESETS: dict[str, PresetDefinition] = _PresetsDict()
