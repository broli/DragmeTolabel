"""
Materials API Routes for DragmeTolabel.
"""

from fastapi import APIRouter

from ..core.schemas import MaterialInfo
from ..cv.materials import get_materials_catalog

router = APIRouter(prefix="/materials", tags=["Materials"])


@router.get("", response_model=list[MaterialInfo])
async def list_materials() -> list[MaterialInfo]:
    """Returns available textures and finishes (marble, tile, wood, stone)."""
    return get_materials_catalog()
