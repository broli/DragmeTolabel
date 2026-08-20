"""
Master OpenCV Rendering Engine for DragmeTolabel.
Processes base64 / BGR images, iterates through preset planar geometries,
applies homography warping, shadow extraction, and composite blending.
"""
from __future__ import annotations

import base64
import time
from typing import List, Tuple
import cv2
import numpy as np

from ..core.presets import get_preset_by_id
from ..core.schemas import PreviewRequest, PreviewResponse
from .homography import warp_plane_texture
from .lighting import blend_material_with_lighting
from .materials import get_material_texture


def decode_base64_image(base64_str: str) -> np.ndarray:
    """Decodes a base64 encoded image string into an OpenCV BGR image."""
    if "," in base64_str:
        base64_str = base64_str.split(",", 1)[1]
    img_data = base64.b64decode(base64_str)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image from base64 string")
    return img


def encode_image_base64(img_bgr: np.ndarray, format: str = "jpeg", quality: int = 90) -> str:
    """Encodes an OpenCV BGR image into a base64 string."""
    ext = f".{format.lower()}"
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality] if format.lower() in ("jpg", "jpeg") else []
    success, buffer = cv2.imencode(ext, img_bgr, encode_params)
    if not success:
        raise ValueError("Failed to encode image to base64")
    b64_str = base64.b64encode(buffer).decode("utf-8")
    mime = "image/jpeg" if format.lower() in ("jpg", "jpeg") else "image/png"
    return f"data:{mime};base64,{b64_str}"


def render_preview(request: PreviewRequest) -> PreviewResponse:
    """
    Executes the OpenCV rendering pipeline:
    1. Decodes original image
    2. Loads selected material texture
    3. Iterates over all planar quads in the preset
    4. Computes homography and perspective warping for each plane
    5. Extracts shadows and lighting from original photo
    6. Blends warped textures onto the photo
    7. Encodes and returns processed preview image
    """
    start_time = time.perf_counter()
    
    # 1. Decode original image
    original_img = decode_base64_image(request.image_base64)
    img_h, img_w = original_img.shape[:2]
    
    # 2. Get preset definition
    preset = get_preset_by_id(request.preset_id)
    if not preset or not preset.enabled:
        raise ValueError(f"Preset '{request.preset_id}' is not valid or currently disabled.")
        
    # 3. Load material texture
    texture = get_material_texture(request.material_id)
    
    # Copy original image to build composite
    current_composite = original_img.copy()
    total_planes_rendered = 0
    
    # 4. Render each plane
    for plane in preset.planes:
        # Check that point indices are within bounds
        quad_points = [request.points[idx] for idx in plane.point_indices if idx < len(request.points)]
        if len(quad_points) != 4:
            continue
            
        # Homography & perspective warp for this plane
        warped_tex, alpha_mask = warp_plane_texture(
            texture=texture,
            dst_quad_points=quad_points,
            output_shape=(img_h, img_w),
            tile_scale=request.tile_scale,
        )
        
        # Shadow / lighting extraction & composite
        current_composite = blend_material_with_lighting(
            warped_texture=warped_tex,
            original_bgr=current_composite,
            alpha_mask=alpha_mask,
            lighting_intensity=request.lighting_intensity,
        )
        total_planes_rendered += 1
        
    # 5. Encode result
    result_b64 = encode_image_base64(current_composite, format="jpeg", quality=92)
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    
    return PreviewResponse(
        success=True,
        processed_image_base64=result_b64,
        preset_id=request.preset_id,
        planes_rendered=total_planes_rendered,
        processing_time_ms=round(elapsed_ms, 2),
        message="Preview rendered successfully.",
    )
