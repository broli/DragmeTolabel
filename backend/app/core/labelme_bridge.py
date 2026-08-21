"""
Labelme Bridge: Headless serialization & export in standard Labelme format.
Decoupled from PySide / Qt GUI components.
"""

from __future__ import annotations

from typing import Any

from .presets import get_preset_by_id


def export_to_labelme_json(
    preset_id: str,
    points: list[list[float]],
    image_width: int,
    image_height: int,
    image_path: str = "capture.jpg",
    image_data_base64: str | None = None,
) -> dict[str, Any]:
    """
    Constructs a valid Labelme 5.x JSON object representing the annotated surface polygons.
    """
    preset = get_preset_by_id(preset_id)
    shapes: list[dict[str, Any]] = []

    if preset and preset.planes:
        for idx, plane in enumerate(preset.planes):
            # Extract planar quad polygon points in order
            plane_points = [points[p_idx] for p_idx in plane.point_indices if p_idx < len(points)]
            shapes.append(
                {
                    "label": f"{preset_id}_{plane.id}",
                    "points": plane_points,
                    "group_id": idx + 1,
                    "description": f"DragmeTolabel: {preset.name} - {plane.name}",
                    "shape_type": "polygon",
                    "flags": {},
                    "mask": None,
                }
            )
    else:
        # Fallback to single polygon with all points
        shapes.append(
            {
                "label": preset_id,
                "points": points,
                "group_id": 1,
                "description": f"DragmeTolabel: {preset_id}",
                "shape_type": "polygon",
                "flags": {},
                "mask": None,
            }
        )

    labelme_dict = {
        "version": "5.5.0",
        "flags": {},
        "shapes": shapes,
        "imagePath": image_path,
        "imageData": image_data_base64,
        "imageHeight": image_height,
        "imageWidth": image_width,
        "preset_id": preset_id,
        "points": points,
    }

    return labelme_dict
