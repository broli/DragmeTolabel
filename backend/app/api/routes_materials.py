"""
Materials API Routes for DragmeTolabel.
"""
from typing import List
from fastapi import APIRouter

from ..cv.materials import get_materials_catalog
from ..core.schemas import MaterialInfo

router = APIRouter(prefix="/materials", tags=["Materials"])


@router.get("", response_model=List[MaterialInfo])
async def list_materials() -> List[MaterialInfo]:
    """Returns available textures and finishes (marble, tile, wood, stone)."""
    return get_materials_catalog()
