"""
Base64 and image encoding/decoding utilities for DragMeToLabel CV engine.
"""

from __future__ import annotations

import base64

import cv2
import numpy as np


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
