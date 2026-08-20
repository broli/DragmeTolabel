"""
Lighting, Shadow Extraction and Realistic Blending Engine for DragmeTolabel.
Extracts natural ambient shadows, lighting gradients, and specular highlights from the original photo.
"""
from __future__ import annotations

import cv2
import numpy as np


def extract_illumination_map(
    original_bgr: np.ndarray,
    mask: np.ndarray,
    lighting_intensity: float = 0.85,
) -> np.ndarray:
    """
    Extracts relative luminance and ambient occlusion shadow multiplier map from original photo.
    
    Returns:
        shadow_map: (H, W) float32 array where 1.0 is neutral, <1.0 is shadow, >1.0 is highlight.
    """
    # Convert original photo to LAB color space to isolate luminance L
    lab = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2LAB)
    l_channel = lab[:, :, 0].astype(np.float32) / 255.0  # [0.0, 1.0]
    
    # Calculate baseline illumination inside masked surface area
    mask_bool = mask > 0.05
    if np.any(mask_bool):
        # Use robust percentile to determine neutral surface ambient level
        baseline_lum = float(np.percentile(l_channel[mask_bool], 70))
        baseline_lum = max(0.2, min(0.9, baseline_lum))
    else:
        baseline_lum = 0.6
        
    # Relative shadow ratio
    # Smooth slightly to retain organic ambient shadows without photographic noise
    smoothed_l = cv2.bilateralFilter(l_channel, d=7, sigmaColor=0.2, sigmaSpace=15)
    
    # Compute relative lighting ratio
    ratio = smoothed_l / baseline_lum
    
    # Blend with lighting intensity slider
    # 0.0 -> no shadows (flat material), 1.0 -> full natural room lighting & shadows
    shadow_map = 1.0 + (ratio - 1.0) * float(np.clip(lighting_intensity, 0.0, 1.5))
    
    # Soft bounds to prevent extreme clipping
    shadow_map = np.clip(shadow_map, 0.15, 1.6)
    return shadow_map


def blend_material_with_lighting(
    warped_texture: np.ndarray,
    original_bgr: np.ndarray,
    alpha_mask: np.ndarray,
    lighting_intensity: float = 0.85,
) -> np.ndarray:
    """
    Applies lighting preservation and seamlessly blends warped texture onto the original photo.
    """
    # Extract illumination & shadow map
    shadow_map = extract_illumination_map(original_bgr, alpha_mask, lighting_intensity)
    
    # Convert warped texture to float [0, 1]
    tex_float = warped_texture.astype(np.float32) / 255.0
    orig_float = original_bgr.astype(np.float32) / 255.0
    
    # Apply illumination modulation to texture (Multiply / Soft-light hybrid)
    shaded_texture = tex_float * shadow_map[:, :, None]
    shaded_texture = np.clip(shaded_texture, 0.0, 1.0)
    
    # Expand alpha mask to 3 channels
    alpha_3d = np.repeat(alpha_mask[:, :, None], 3, axis=2)
    
    # Alpha blend onto original background
    composite = orig_float * (1.0 - alpha_3d) + shaded_texture * alpha_3d
    composite_bgr = np.clip(composite * 255.0, 0, 255).astype(np.uint8)
    
    return composite_bgr
