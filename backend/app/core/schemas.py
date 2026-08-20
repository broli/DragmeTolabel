"""
Pydantic schemas for DragmeTolabel.
Defines polygon geometries, presets, preview requests, and Labelme interoperability models.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Point2D(BaseModel):
    x: float = Field(..., description="X coordinate in pixels or normalized [0, 1]")
    y: float = Field(..., description="Y coordinate in pixels or normalized [0, 1]")


class PolygonPlane(BaseModel):
    id: str = Field(..., description="Unique plane identifier (e.g. 'left_wall', 'back_wall', 'floor')")
    name: str = Field(..., description="Human readable name")
    point_indices: list[int] = Field(..., description="Indices into the parent points list forming this quadrilateral")
    material_id: str | None = Field(default=None, description="Optional custom material override for this plane")


class PresetDefinition(BaseModel):
    id: str = Field(..., description="Preset ID (floor, ceiling, corner_bath, alcove_bath, cali_bath)")
    name: str = Field(..., description="Preset display name")
    description: str = Field(..., description="Preset description")
    point_count: int
    line_count: int
    enabled: bool = True
    default_normalized_points: list[list[float]] = Field(
        ..., description="Default normalized [x, y] coordinates in [0, 1]"
    )
    lines: list[list[int]] = Field(..., description="List of [start_idx, end_idx] pairs for visual wireframe")
    planes: list[PolygonPlane] = Field(..., description="List of planar quads for homography warping")


class MaterialInfo(BaseModel):
    id: str
    name: str
    category: str  # 'tile', 'wood', 'stone', 'marble', 'wall_panel'
    thumbnail_url: str
    texture_file: str
    default_tile_scale: float = 1.0  # repeats/scaling
    description: str


class PreviewRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded original photo (JPEG/PNG)")
    preset_id: str = Field(..., description="Selected preset ID")
    points: list[list[float]] = Field(..., description="Current polygon points in pixel coordinates [[x, y], ...]")
    material_id: str = Field(default="carrara_marble", description="Selected material ID")
    lighting_intensity: float = Field(default=0.85, description="Shadow/lighting preservation factor (0.0 - 1.5)")
    tile_scale: float = Field(default=1.0, description="Texture tiling scale factor")


class PreviewResponse(BaseModel):
    success: bool
    processed_image_base64: str
    preset_id: str
    planes_rendered: int
    processing_time_ms: float
    message: str | None = None


class SnapPoint(BaseModel):
    x: float = Field(..., description="X coordinate in pixels")
    y: float = Field(..., description="Y coordinate in pixels")
    score: float = Field(..., description="Confidence score [0.0, 1.0]")
    landmark_type: str = Field(
        default="junction", description="Semantic landmark type (corner_crease, tub_rim, baseboard, junction)"
    )


class AutoFitRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded room photo (JPEG/PNG)")
    preset_id: str = Field(..., description="Preset ID to fit (e.g. 'corner_bath', 'alcove_bath', 'floor', 'ceiling')")


class AutoFitResponse(BaseModel):
    success: bool
    preset_id: str
    points: list[list[float]] = Field(..., description="Fitted mesh coordinates in image pixel space [[x, y], ...]")
    confidence: float = Field(..., description="Overall fit confidence score [0.0, 1.0]")
    execution_time_ms: float = Field(..., description="Inference execution time in milliseconds")
    landmarks: dict[str, Any] = Field(default_factory=dict, description="Detected key architectural landmarks")
    message: str | None = None


class LabelmeShapeDict(BaseModel):
    label: str
    points: list[list[float]]
    group_id: int | None = None
    description: str = ""
    shape_type: str = "polygon"
    flags: dict[str, Any] = Field(default_factory=dict)
    mask: str | None = None


class LabelmeExportResponse(BaseModel):
    version: str = "5.5.0"
    flags: dict[str, Any] = Field(default_factory=dict)
    shapes: list[LabelmeShapeDict]
    imagePath: str
    imageData: str | None = None
    imageHeight: int
    imageWidth: int
