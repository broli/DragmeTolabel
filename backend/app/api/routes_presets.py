"""
Preset API Routes for DragmeTolabel.
"""

from fastapi import APIRouter, HTTPException

from ..core.presets import get_all_presets, get_preset_by_id
from ..core.schemas import PresetDefinition

router = APIRouter(prefix="/presets", tags=["Presets"])


@router.get("", response_model=list[PresetDefinition])
async def list_presets() -> list[PresetDefinition]:
    """Returns all 5 surface preset definitions and topologies."""
    return get_all_presets()


@router.get("/{preset_id}", response_model=PresetDefinition)
async def get_preset(preset_id: str) -> PresetDefinition:
    """Returns topology details for a single preset."""
    preset = get_preset_by_id(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found")
    return preset
