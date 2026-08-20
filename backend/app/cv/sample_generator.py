"""
Sample Photo Generator for DragmeTolabel.
Generates photorealistic room and bathroom scenes for instant sales rep testing.
"""
from pathlib import Path
import cv2
import numpy as np

SAMPLES_DIR = Path(__file__).parent.parent.parent.parent / "frontend" / "assets" / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)


def generate_sample_alcove_bath(w: int = 1200, h: int = 800) -> np.ndarray:
    """Generates a realistic bathroom interior with an alcove bathtub area."""
    img = np.full((h, w, 3), 235, dtype=np.uint8)
    
    # Walls gradient (warm neutral off-white)
    for y in range(h):
        grad = int(15 * (y / h))
        img[y, :] = (230 - grad, 235 - grad, 240 - grad)
        
    # Wall corners / perspective lines for alcove
    # Left front corner
    cv2.line(img, (int(w * 0.14), int(h * 0.10)), (int(w * 0.14), int(h * 0.75)), (180, 185, 190), 2)
    # Back-left corner
    cv2.line(img, (int(w * 0.34), int(h * 0.18)), (int(w * 0.34), int(h * 0.68)), (160, 165, 170), 3)
    # Back-right corner
    cv2.line(img, (int(w * 0.66), int(h * 0.18)), (int(w * 0.66), int(h * 0.68)), (160, 165, 170), 3)
    # Right front corner
    cv2.line(img, (int(w * 0.86), int(h * 0.10)), (int(w * 0.86), int(h * 0.75)), (180, 185, 190), 2)
    
    # Ceiling trim
    cv2.line(img, (int(w * 0.14), int(h * 0.10)), (int(w * 0.34), int(h * 0.18)), (180, 185, 190), 2)
    cv2.line(img, (int(w * 0.34), int(h * 0.18)), (int(w * 0.66), int(h * 0.18)), (180, 185, 190), 2)
    cv2.line(img, (int(w * 0.66), int(h * 0.18)), (int(w * 0.86), int(h * 0.10)), (180, 185, 190), 2)
    
    # Existing tub fixture outline
    tub_pts = np.array([
        [int(w * 0.14), int(h * 0.72)],
        [int(w * 0.34), int(h * 0.66)],
        [int(w * 0.66), int(h * 0.66)],
        [int(w * 0.86), int(h * 0.72)],
        [int(w * 0.86), int(h * 0.92)],
        [int(w * 0.14), int(h * 0.92)],
    ], dtype=np.int32)
    cv2.fillPoly(img, [tub_pts], (245, 245, 248))
    cv2.polylines(img, [tub_pts], True, (170, 175, 180), 2)
    
    # Soft shadow under tub & alcove corners
    shadow = np.zeros((h, w), dtype=np.uint8)
    cv2.rectangle(shadow, (int(w * 0.14), int(h * 0.90)), (int(w * 0.86), int(h * 0.98)), 80, -1)
    shadow_blur = cv2.GaussianBlur(shadow, (45, 45), 20)
    for c in range(3):
        img[:, :, c] = np.clip(img[:, :, c] - shadow_blur, 0, 255)
        
    # Add modern chrome shower head & faucet on back wall
    cv2.circle(img, (int(w * 0.50), int(h * 0.30)), 16, (200, 210, 220), -1)
    cv2.circle(img, (int(w * 0.50), int(h * 0.30)), 16, (120, 130, 140), 2)
    cv2.rectangle(img, (int(w * 0.49), int(h * 0.22)), (int(w * 0.51), int(h * 0.30)), (150, 160, 170), -1)
    # Faucet handle
    cv2.circle(img, (int(w * 0.50), int(h * 0.52)), 12, (180, 190, 200), -1)
    
    # Ambient lighting gradient
    return cv2.GaussianBlur(img, (3, 3), 0.5)


def generate_sample_corner_bath(w: int = 1200, h: int = 800) -> np.ndarray:
    """Generates a realistic bathroom interior with a corner bathtub setup."""
    img = np.full((h, w, 3), 230, dtype=np.uint8)
    
    # Two walls meeting at center corner
    center_x = int(w * 0.50)
    corner_top = int(h * 0.12)
    corner_bottom = int(h * 0.65)
    
    # Left wall (slightly lighter)
    left_wall_pts = np.array([
        [int(w * 0.12), int(h * 0.18)],
        [center_x, corner_top],
        [center_x, corner_bottom],
        [int(w * 0.12), int(h * 0.70)],
    ], dtype=np.int32)
    cv2.fillPoly(img, [left_wall_pts], (238, 240, 242))
    
    # Right wall (slightly darker for 3D depth)
    right_wall_pts = np.array([
        [center_x, corner_top],
        [int(w * 0.88), int(h * 0.18)],
        [int(w * 0.88), int(h * 0.70)],
        [center_x, corner_bottom],
    ], dtype=np.int32)
    cv2.fillPoly(img, [right_wall_pts], (215, 218, 222))
    
    # Corner seam line
    cv2.line(img, (center_x, corner_top), (center_x, corner_bottom), (140, 145, 150), 3)
    cv2.line(img, (int(w * 0.12), int(h * 0.18)), (center_x, corner_top), (160, 165, 170), 2)
    cv2.line(img, (center_x, corner_top), (int(w * 0.88), int(h * 0.18)), (160, 165, 170), 2)
    
    # Tub ledge
    cv2.line(img, (int(w * 0.12), int(h * 0.70)), (center_x, corner_bottom), (150, 155, 160), 3)
    cv2.line(img, (center_x, corner_bottom), (int(w * 0.88), int(h * 0.70)), (150, 155, 160), 3)
    
    # Tub body
    tub_pts = np.array([
        [int(w * 0.12), int(h * 0.70)],
        [center_x, corner_bottom],
        [int(w * 0.88), int(h * 0.70)],
        [int(w * 0.88), int(h * 0.94)],
        [int(w * 0.12), int(h * 0.94)],
    ], dtype=np.int32)
    cv2.fillPoly(img, [tub_pts], (246, 248, 250))
    cv2.polylines(img, [tub_pts], True, (160, 165, 170), 2)
    
    # Corner chrome shower fixture
    cv2.circle(img, (center_x, int(h * 0.28)), 18, (190, 200, 210), -1)
    cv2.circle(img, (center_x, int(h * 0.28)), 18, (120, 130, 140), 2)
    
    return cv2.GaussianBlur(img, (3, 3), 0.5)


def generate_sample_room_floor(w: int = 1200, h: int = 800) -> np.ndarray:
    """Generates a modern living space with prominent floor surface."""
    img = np.full((h, w, 3), 240, dtype=np.uint8)
    
    # Back wall
    back_wall = np.array([
        [0, 0],
        [w, 0],
        [w, int(h * 0.55)],
        [0, int(h * 0.55)],
    ], dtype=np.int32)
    cv2.fillPoly(img, [back_wall], (230, 235, 238))
    
    # Baseboard line
    cv2.line(img, (0, int(h * 0.55)), (w, int(h * 0.55)), (180, 185, 190), 4)
    
    # Old floor (muted plain surface)
    floor_pts = np.array([
        [0, int(h * 0.55)],
        [w, int(h * 0.55)],
        [w, h],
        [0, h],
    ], dtype=np.int32)
    cv2.fillPoly(img, [floor_pts], (190, 195, 200))
    
    # Perspective depth lines on floor
    for x in range(int(w * 0.1), int(w * 0.95), int(w * 0.2)):
        cv2.line(img, (x, int(h * 0.55)), (int(x * 1.4 - w * 0.2), h), (175, 180, 185), 1)
        
    # Add a window on back wall casting natural sunlight
    win_pts = np.array([
        [int(w * 0.35), int(h * 0.12)],
        [int(w * 0.65), int(h * 0.12)],
        [int(w * 0.65), int(h * 0.45)],
        [int(w * 0.35), int(h * 0.45)],
    ], dtype=np.int32)
    cv2.fillPoly(img, [win_pts], (255, 252, 245))
    cv2.polylines(img, [win_pts], True, (160, 165, 170), 3)
    # Window panes
    cv2.line(img, (int(w * 0.50), int(h * 0.12)), (int(w * 0.50), int(h * 0.45)), (160, 165, 170), 2)
    cv2.line(img, (int(w * 0.35), int(h * 0.28)), (int(w * 0.65), int(h * 0.28)), (160, 165, 170), 2)
    
    # Natural sunlight cast on floor
    sun_cast = np.zeros((h, w), dtype=np.uint8)
    sun_pts = np.array([
        [int(w * 0.38), int(h * 0.55)],
        [int(w * 0.62), int(h * 0.55)],
        [int(w * 0.85), h],
        [int(w * 0.45), h],
    ], dtype=np.int32)
    cv2.fillPoly(sun_cast, [sun_pts], 45)
    sun_blur = cv2.GaussianBlur(sun_cast, (55, 55), 25)
    for c in range(3):
        img[:, :, c] = np.clip(img[:, :, c] + sun_blur, 0, 255)
        
    return img


def generate_all_samples() -> None:
    samples = {
        "sample_alcove_bath.jpg": generate_sample_alcove_bath,
        "sample_corner_bath.jpg": generate_sample_corner_bath,
        "sample_room_floor.jpg": generate_sample_room_floor,
    }
    
    for filename, fn in samples.items():
        path = SAMPLES_DIR / filename
        img = fn(1200, 800)
        cv2.imwrite(str(path), img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])


if __name__ == "__main__":
    generate_all_samples()
