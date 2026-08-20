"""
Material & Texture Generator / Manager for DragmeTolabel.
Provides high-res tile, marble, wood, and stone textures.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

TEXTURES_DIR = Path(__file__).parent.parent / "static" / "textures"
TEXTURES_DIR.mkdir(parents=True, exist_ok=True)

MATERIALS_CATALOG = [
    {
        "id": "carrara_marble",
        "name": "Carrara White Marble",
        "category": "marble",
        "thumbnail_url": "/static/textures/carrara_marble.jpg",
        "texture_file": "carrara_marble.jpg",
        "default_tile_scale": 1.0,
        "description": "Luxurious white Italian marble with subtle grey veining.",
    },
    {
        "id": "modern_subway_tile",
        "name": "Glossy White Subway Tile",
        "category": "tile",
        "thumbnail_url": "/static/textures/modern_subway_tile.jpg",
        "texture_file": "modern_subway_tile.jpg",
        "default_tile_scale": 2.5,
        "description": "Crisp 3x6 inch subway tiles with light grey grout lines.",
    },
    {
        "id": "slate_grey_tile",
        "name": "Charcoal Slate Tile",
        "category": "stone",
        "thumbnail_url": "/static/textures/slate_grey_tile.jpg",
        "texture_file": "slate_grey_tile.jpg",
        "default_tile_scale": 2.0,
        "description": "Modern large-format matte slate grey stone tiles.",
    },
    {
        "id": "herringbone_oak",
        "name": "Natural Oak Hardwood",
        "category": "wood",
        "thumbnail_url": "/static/textures/herringbone_oak.jpg",
        "texture_file": "herringbone_oak.jpg",
        "default_tile_scale": 2.0,
        "description": "Warm European oak wood plank flooring.",
    },
    {
        "id": "emerald_hex_tile",
        "name": "Artisan Emerald Hex Tile",
        "category": "tile",
        "thumbnail_url": "/static/textures/emerald_hex_tile.jpg",
        "texture_file": "emerald_hex_tile.jpg",
        "default_tile_scale": 3.0,
        "description": "Deep emerald glazed hexagonal tiles with gold-tint grout.",
    },
    {
        "id": "terrazzo_venetian",
        "name": "Venetian Terrazzo",
        "category": "stone",
        "thumbnail_url": "/static/textures/terrazzo_venetian.jpg",
        "texture_file": "terrazzo_venetian.jpg",
        "default_tile_scale": 1.5,
        "description": "Contemporary terrazzo stone with neutral quartz flecks.",
    },
]


def generate_carrara_marble(width: int = 1024, height: int = 1024) -> np.ndarray:
    """Procedurally generates high quality Carrara marble texture."""
    base = np.full((height, width, 3), 245, dtype=np.uint8)
    
    # Generate multi-octave Perlin-like noise for organic marble veins
    noise1 = np.random.normal(0, 25, (height // 4, width // 4)).astype(np.float32)
    noise1 = cv2.resize(noise1, (width, height), interpolation=cv2.INTER_CUBIC)
    
    noise2 = np.random.normal(0, 15, (height // 16, width // 16)).astype(np.float32)
    noise2 = cv2.resize(noise2, (width, height), interpolation=cv2.INTER_CUBIC)

    combined = (noise1 * 0.7 + noise2 * 0.3)
    
    # Vein turbulence
    x, y = np.meshgrid(np.arange(width), np.arange(height))
    sine_pattern = np.sin((x * 0.01 + y * 0.012) + combined * 0.08)
    
    veins = (np.abs(sine_pattern) ** 8) * 90
    veins = np.clip(veins, 0, 90).astype(np.uint8)
    
    # Apply soft grey-blue tint to veins
    b = np.clip(base[:, :, 0] - veins * 1.1, 80, 255).astype(np.uint8)
    g = np.clip(base[:, :, 1] - veins * 1.05, 80, 255).astype(np.uint8)
    r = np.clip(base[:, :, 2] - veins * 1.0, 80, 255).astype(np.uint8)
    
    marble = cv2.merge([b, g, r])
    marble = cv2.GaussianBlur(marble, (3, 3), 0.8)
    return marble


def generate_subway_tiles(width: int = 1024, height: int = 1024) -> np.ndarray:
    """Procedurally generates subway tile pattern with realistic bevels and grout."""
    img = np.full((height, width, 3), 248, dtype=np.uint8)
    grout_color = (165, 165, 165)
    
    tile_w = 200
    tile_h = 100
    grout = 6
    
    rows = height // tile_h + 2
    cols = width // tile_w + 2
    
    for r in range(rows):
        offset = (tile_w // 2) if (r % 2 == 1) else 0
        y1 = r * tile_h
        y2 = y1 + tile_h - grout
        
        for c in range(-1, cols):
            x1 = c * tile_w + offset
            x2 = x1 + tile_w - grout
            
            # Subtle tile surface gradient for glossy bevel effect
            sub_w = max(1, x2 - x1)
            sub_h = max(1, y2 - y1)
            
            tile_patch = np.full((sub_h, sub_w, 3), 252, dtype=np.uint8)
            cv2.rectangle(tile_patch, (0, 0), (sub_w - 1, sub_h - 1), (220, 220, 220), 2)
            
            # Clip bounds
            px1, px2 = max(0, x1), min(width, x2)
            py1, py2 = max(0, y1), min(height, y2)
            
            if px2 > px1 and py2 > py1:
                tx1, tx2 = px1 - x1, px2 - x1
                ty1, ty2 = py1 - y1, py2 - y1
                img[py1:py2, px1:px2] = tile_patch[ty1:ty2, tx1:tx2]
                
    # Grout lines
    img = cv2.GaussianBlur(img, (3, 3), 0.5)
    return img


def generate_slate_tile(width: int = 1024, height: int = 1024) -> np.ndarray:
    """Procedurally generates charcoal slate stone tiles."""
    base = np.full((height, width, 3), 48, dtype=np.uint8)
    noise = np.random.normal(0, 18, (height, width)).astype(np.float32)
    noise = cv2.GaussianBlur(noise, (5, 5), 1.5)
    
    slate = np.clip(base + noise[:, :, None], 25, 95).astype(np.uint8)
    
    # 2x2 grid grout lines
    grid_size = 256
    grout = 4
    for i in range(0, width, grid_size):
        cv2.line(slate, (i, 0), (i, height), (20, 20, 20), grout)
    for j in range(0, height, grid_size):
        cv2.line(slate, (0, j), (width, j), (20, 20, 20), grout)
        
    return slate


def generate_hardwood(width: int = 1024, height: int = 1024) -> np.ndarray:
    """Procedurally generates warm natural oak plank texture."""
    # Base warm wood tone (BGR)
    base_color = np.array([45, 115, 175], dtype=np.float32)
    
    # Wood grain lines (vertical high frequency)
    y_lines = np.random.normal(0, 15, (height, 1)).astype(np.float32)
    y_lines = cv2.resize(y_lines, (width, height), interpolation=cv2.INTER_LINEAR)
    
    noise = np.random.normal(0, 10, (height // 8, width // 8)).astype(np.float32)
    noise = cv2.resize(noise, (width, height), interpolation=cv2.INTER_CUBIC)
    
    grain = y_lines * 0.6 + noise * 0.4
    wood = np.clip(base_color + grain[:, :, None], 20, 240).astype(np.uint8)
    
    # Plank seams
    plank_h = 128
    for y in range(0, height, plank_h):
        cv2.line(wood, (0, y), (width, y), (25, 60, 95), 3)
        # Random staggered vertical seams
        for x in range(int(np.random.randint(100, 300)), width, 350):
            cv2.line(wood, (x, y), (x, y + plank_h), (25, 60, 95), 2)
            
    return wood


def generate_emerald_hex(width: int = 1024, height: int = 1024) -> np.ndarray:
    """Procedurally generates emerald green glazed tile texture."""
    img = np.full((height, width, 3), (35, 75, 20), dtype=np.uint8)
    # Add subtle tile gloss
    noise = np.random.normal(0, 10, (height // 4, width // 4)).astype(np.float32)
    noise = cv2.resize(noise, (width, height), interpolation=cv2.INTER_CUBIC)
    img = np.clip(img + noise[:, :, None], 10, 220).astype(np.uint8)
    
    # Gold/brass grout lines
    grid = 80
    for y in range(0, height, grid):
        cv2.line(img, (0, y), (width, y), (90, 180, 210), 2)
    for x in range(0, width, grid):
        cv2.line(img, (x, 0), (x, height), (90, 180, 210), 2)
        
    return img


def generate_terrazzo(width: int = 1024, height: int = 1024) -> np.ndarray:
    """Procedurally generates terrazzo stone texture."""
    base = np.full((height, width, 3), (220, 225, 230), dtype=np.uint8)
    
    # Scatter stone flecks of various colors
    colors = [
        (40, 40, 50),     # Dark slate
        (80, 120, 180),   # Terracotta
        (160, 180, 190),  # Light stone
        (60, 100, 120),   # Ochre
    ]
    
    for _ in range(450):
        cx = np.random.randint(0, width)
        cy = np.random.randint(0, height)
        radius = np.random.randint(4, 18)
        color = colors[np.random.randint(0, len(colors))]
        cv2.circle(base, (cx, cy), radius, color, -1)
        
    base = cv2.GaussianBlur(base, (3, 3), 0.8)
    return base


def ensure_material_textures() -> None:
    """Generates texture image files on disk if they don't already exist."""
    generators = {
        "carrara_marble.jpg": generate_carrara_marble,
        "modern_subway_tile.jpg": generate_subway_tiles,
        "slate_grey_tile.jpg": generate_slate_tile,
        "herringbone_oak.jpg": generate_hardwood,
        "emerald_hex_tile.jpg": generate_emerald_hex,
        "terrazzo_venetian.jpg": generate_terrazzo,
    }
    
    for filename, gen_fn in generators.items():
        file_path = TEXTURES_DIR / filename
        if not file_path.exists():
            img = gen_fn(1024, 1024)
            cv2.imwrite(str(file_path), img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])


def get_material_texture(material_id: str) -> np.ndarray:
    """Loads a material texture BGR array by ID."""
    ensure_material_textures()
    
    material = next((m for m in MATERIALS_CATALOG if m["id"] == material_id), MATERIALS_CATALOG[0])
    file_path = TEXTURES_DIR / material["texture_file"]
    
    if not file_path.exists():
        ensure_material_textures()
        
    img = cv2.imread(str(file_path))
    if img is None:
        # Emergency fallback texture
        img = generate_carrara_marble(1024, 1024)
    return img


def get_materials_catalog() -> List[Dict]:
    ensure_material_textures()
    return MATERIALS_CATALOG
