"""
Preview & Export API Routes for DragmeTolabel.
"""

from fastapi import APIRouter, HTTPException

from ..core.labelme_bridge import export_to_labelme_json
from ..core.schemas import PreviewRequest, PreviewResponse
from ..cv.renderer import decode_base64_image, render_preview

router = APIRouter(prefix="", tags=["Preview & Export"])


@router.post("/preview", response_model=PreviewResponse)
async def generate_preview(request: PreviewRequest) -> PreviewResponse:
    """
    Renders photo with warped perspective textures and realistic shadow preservation using OpenCV.
    """
    try:
        response = render_preview(request)
        return response
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rendering error: {str(e)}")


@router.post("/export")
@router.post("/export-labelme")
async def export_labelme_annotation(request: PreviewRequest) -> dict:
    """
    Exports the current image and polygon annotation into standard Labelme 5.x JSON format.
    """
    try:
        img = decode_base64_image(request.image_base64)
        h, w = img.shape[:2]
        labelme_json = export_to_labelme_json(
            preset_id=request.preset_id,
            points=request.points,
            image_width=w,
            image_height=h,
            image_path=f"{request.preset_id}_annotation.jpg",
            image_data_base64=request.image_base64 if len(request.image_base64) < 1000000 else None,
        )
        return labelme_json
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")
