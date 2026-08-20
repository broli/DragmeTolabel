"""
Homography and Perspective Transformation Engine for DragmeTolabel.
Calculates perspective warp matrices and projects textures onto planar quads.
"""

from __future__ import annotations

import cv2
import numpy as np


def compute_quad_homography(
    dst_points: list[list[float]],
    texture_shape: tuple[int, int],
    tile_scale: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Computes 3x3 homography matrix mapping texture coordinates to destination quad vertices.

    dst_points: 4 [x, y] points defining the destination quad in counter-clockwise / clockwise order
                [Top-Left, Top-Right, Bottom-Right, Bottom-Left].
    texture_shape: (height, width) of the source texture.
    tile_scale: Tiling multiplier (higher = more repetitions across the surface).
    """
    tex_h, tex_w = texture_shape

    # Source texture corners
    # Scale coordinates to repeat/tile the texture naturally across the quadrilateral
    src_w = float(tex_w) * max(0.2, tile_scale)
    src_h = float(tex_h) * max(0.2, tile_scale)

    src_pts = np.array(
        [
            [0.0, 0.0],
            [src_w, 0.0],
            [src_w, src_h],
            [0.0, src_h],
        ],
        dtype=np.float32,
    )

    dst_pts = np.array(dst_points, dtype=np.float32)

    # Compute perspective transform matrix
    H = cv2.getPerspectiveTransform(src_pts, dst_pts)
    return H, dst_pts


def create_tiled_texture(texture: np.ndarray, tile_scale: float = 1.0) -> np.ndarray:
    """Tiles texture seamlessly if tile_scale > 1."""
    if tile_scale <= 1.0:
        return texture

    repeats = int(np.ceil(tile_scale))
    tiled = np.tile(texture, (repeats, repeats, 1))
    return tiled


def warp_plane_texture(
    texture: np.ndarray,
    dst_quad_points: list[list[float]],
    output_shape: tuple[int, int],
    tile_scale: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Warps a texture onto a destination quadrilateral with soft anti-aliased edge alpha mask.

    Returns:
        warped_texture: (H, W, 3) BGR image with texture warped into quad coordinates.
        alpha_mask: (H, W) float32 [0.0, 1.0] soft edge mask for smooth blending.
    """
    out_h, out_w = output_shape
    tex_h, tex_w = texture.shape[:2]

    # Create tiled texture buffer if needed
    tiled_tex = create_tiled_texture(texture, tile_scale)
    th, tw = tiled_tex.shape[:2]

    src_pts = np.array(
        [
            [0.0, 0.0],
            [float(tw), 0.0],
            [float(tw), float(th)],
            [0.0, float(th)],
        ],
        dtype=np.float32,
    )

    dst_pts = np.array(dst_quad_points, dtype=np.float32)

    # Calculate homography matrix H
    H = cv2.getPerspectiveTransform(src_pts, dst_pts)

    # Warp texture to full canvas dimensions
    warped_texture = cv2.warpPerspective(
        tiled_tex,
        H,
        (out_w, out_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )

    # Generate binary mask of polygon
    mask = np.zeros((out_h, out_w), dtype=np.uint8)
    int_pts = np.int32([dst_quad_points])
    cv2.fillPoly(mask, int_pts, 255)

    # Apply soft Gaussian feathering (anti-aliasing) to the mask edges
    mask_float = mask.astype(np.float32) / 255.0
    feathered_mask = cv2.GaussianBlur(mask_float, (5, 5), 1.0)

    # Ensure fully inside the polygon remains 1.0 while edges smoothly taper off
    alpha_mask = np.clip(feathered_mask * 1.05, 0.0, 1.0)

    return warped_texture, alpha_mask
