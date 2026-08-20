"""
Preset geometry definitions for DragmeTolabel.
Defines normalized topologies for:
1) Floor (4 dots, 4 lines)
2) Ceiling (4 dots, 4 lines)
3) Corner Bath (6 dots, 7 lines)
4) Alcove Bath (8 dots, 10 lines)
5) Cali Bath (Disabled / Coming Soon)
"""
from typing import Dict, List
from .schemas import PresetDefinition, PolygonPlane


PRESETS: Dict[str, PresetDefinition] = {
    "floor": PresetDefinition(
        id="floor",
        name="Floor Surface",
        description="Standard 4-point quadrilateral floor plane with ground perspective.",
        point_count=4,
        line_count=4,
        enabled=True,
        default_normalized_points=[
            [0.15, 0.58],  # 0: Top-left
            [0.85, 0.58],  # 1: Top-right
            [0.95, 0.94],  # 2: Bottom-right
            [0.05, 0.94],  # 3: Bottom-left
        ],
        lines=[
            [0, 1],
            [1, 2],
            [2, 3],
            [3, 0],
        ],
        planes=[
            PolygonPlane(
                id="floor_plane",
                name="Floor Plane",
                point_indices=[0, 1, 2, 3],
            )
        ],
    ),
    "ceiling": PresetDefinition(
        id="ceiling",
        name="Ceiling Surface",
        description="Standard 4-point quadrilateral ceiling plane with overhead perspective.",
        point_count=4,
        line_count=4,
        enabled=True,
        default_normalized_points=[
            [0.05, 0.06],  # 0: Top-left
            [0.95, 0.06],  # 1: Top-right
            [0.85, 0.42],  # 2: Bottom-right
            [0.15, 0.42],  # 3: Bottom-left
        ],
        lines=[
            [0, 1],
            [1, 2],
            [2, 3],
            [3, 0],
        ],
        planes=[
            PolygonPlane(
                id="ceiling_plane",
                name="Ceiling Plane",
                point_indices=[0, 1, 2, 3],
            )
        ],
    ),
    "corner_bath": PresetDefinition(
        id="corner_bath",
        name="Corner Bath",
        description="Corner bathtub surround with 6 vertices and 7 connecting lines defining Left and Right walls.",
        point_count=6,
        line_count=7,
        enabled=True,
        default_normalized_points=[
            [0.15, 0.18],  # 0: Left Wall Top
            [0.50, 0.12],  # 1: Corner Top
            [0.85, 0.18],  # 2: Right Wall Top
            [0.15, 0.68],  # 3: Left Wall Tub Rim
            [0.50, 0.62],  # 4: Corner Bottom / Tub Apex
            [0.85, 0.68],  # 5: Right Wall Tub Rim
        ],
        lines=[
            [0, 1],  # 1. Left top
            [1, 2],  # 2. Right top
            [0, 3],  # 3. Left outer vertical
            [1, 4],  # 4. Center corner seam
            [2, 5],  # 5. Right outer vertical
            [3, 4],  # 6. Left tub ledge
            [4, 5],  # 7. Right tub ledge
        ],
        planes=[
            PolygonPlane(
                id="left_wall",
                name="Left Wall Surround",
                point_indices=[0, 1, 4, 3],
            ),
            PolygonPlane(
                id="right_wall",
                name="Right Wall Surround",
                point_indices=[1, 2, 5, 4],
            ),
        ],
    ),
    "alcove_bath": PresetDefinition(
        id="alcove_bath",
        name="Alcove Bath",
        description="3-wall recessed alcove bathtub with 8 vertices and 10 connecting lines (Left Wall, Back Wall, Right Wall).",
        point_count=8,
        line_count=10,
        enabled=True,
        default_normalized_points=[
            [0.14, 0.16],  # 0: Left-Front Top
            [0.34, 0.22],  # 1: Back-Left Top
            [0.66, 0.22],  # 2: Back-Right Top
            [0.86, 0.16],  # 3: Right-Front Top
            [0.14, 0.72],  # 4: Left-Front Bottom
            [0.34, 0.66],  # 5: Back-Left Tub Rim
            [0.66, 0.66],  # 6: Back-Right Tub Rim
            [0.86, 0.72],  # 7: Right-Front Bottom
        ],
        lines=[
            [0, 1],  # 1. Left wall top
            [1, 2],  # 2. Back wall top
            [2, 3],  # 3. Right wall top
            [0, 4],  # 4. Left front vertical
            [1, 5],  # 5. Back left corner seam
            [2, 6],  # 6. Back right corner seam
            [3, 7],  # 7. Right front vertical
            [4, 5],  # 8. Left bottom ledge
            [5, 6],  # 9. Back tub rim
            [6, 7],  # 10. Right bottom ledge
        ],
        planes=[
            PolygonPlane(
                id="left_wall",
                name="Left Alcove Wall",
                point_indices=[0, 1, 5, 4],
            ),
            PolygonPlane(
                id="back_wall",
                name="Back Alcove Wall",
                point_indices=[1, 2, 6, 5],
            ),
            PolygonPlane(
                id="right_wall",
                name="Right Alcove Wall",
                point_indices=[2, 3, 7, 6],
            ),
        ],
    ),
    "cali_bath": PresetDefinition(
        id="cali_bath",
        name="Cali Bath",
        description="California walk-in shower configuration (In Development).",
        point_count=0,
        line_count=0,
        enabled=False,
        default_normalized_points=[],
        lines=[],
        planes=[],
    ),
}


def get_all_presets() -> List[PresetDefinition]:
    return list(PRESETS.values())


def get_preset_by_id(preset_id: str) -> PresetDefinition | None:
    return PRESETS.get(preset_id)
