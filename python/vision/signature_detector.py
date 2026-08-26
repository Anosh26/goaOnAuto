"""
Signature Visual Feature Detector Module.
Single Responsibility: Identifies handwritten signatures via aspect ratio & blue/dark ink stroke detection.
"""
import sys
import os
import json

# Ensure project root in sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import cv2
import numpy as np

# Suppress verbose OpenCV warnings
try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
except Exception:
    pass

def to_native_types(item):
    """Recursively convert NumPy data types to native Python types for JSON serialization."""
    if isinstance(item, dict):
        return {k: to_native_types(v) for k, v in item.items()}
    elif isinstance(item, list):
        return [to_native_types(v) for v in item]
    elif isinstance(item, (np.floating, np.float32, np.float64)):
        return float(item)
    elif isinstance(item, (np.integer, np.int32, np.int64)):
        return int(item)
    elif isinstance(item, (np.bool_, bool)):
        return bool(item)
    elif isinstance(item, np.ndarray):
        return item.tolist()
    return item

def detect_signature(image_path: str) -> dict:
    if not os.path.exists(image_path):
        return {
            "is_signature": False,
            "confidence": 0.0,
            "error": f"File not found: {image_path}"
        }

    try:
        img = cv2.imread(image_path)
        if img is None:
            return {
                "is_signature": False,
                "confidence": 0.0,
                "error": "Failed to decode image"
            }

        height, width = img.shape[:2]
        if height < 30 or width < 30:
            return {
                "is_signature": False,
                "confidence": 0.0,
                "reason": "Image dimensions too small"
            }

        aspect_ratio = float(width) / float(height)
        total_pixels = float(width * height)

        # 1. Aspect Ratio: Signatures are typically wide rectangles (w/h >= 1.20, up to 6.0)
        is_wide_rect = 1.20 <= aspect_ratio <= 6.0

        # 2. Check for light/white background (> 60% of image is light/white)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        light_bg_pixels = cv2.countNonZero(cv2.inRange(gray, 170, 255))
        light_bg_ratio = float(light_bg_pixels) / total_pixels

        # 3. Detect Blue Ink strokes (in HSV)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        blue_mask = cv2.inRange(hsv, (85, 35, 25), (145, 255, 235))
        blue_ink_pixels = cv2.countNonZero(blue_mask)
        blue_ink_ratio = float(blue_ink_pixels) / total_pixels

        # Also detect dark/black ink strokes on light paper as secondary fallback
        dark_mask = cv2.inRange(gray, 0, 130)
        dark_ink_pixels = cv2.countNonZero(dark_mask)
        dark_ink_ratio = float(dark_ink_pixels) / total_pixels

        has_blue_strokes = (0.005 <= blue_ink_ratio <= 0.30)
        has_dark_strokes = (0.005 <= dark_ink_ratio <= 0.30)

        # Measure stroke connected components/contours
        active_mask = blue_mask if blue_ink_ratio > 0.008 else dark_mask
        contours, _ = cv2.findContours(active_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        num_strokes = len(contours)

        is_blue_signature = (
            is_wide_rect and 
            light_bg_ratio >= 0.58 and 
            has_blue_strokes and 
            num_strokes >= 1
        )

        is_dark_signature = (
            is_wide_rect and 
            light_bg_ratio >= 0.65 and 
            has_dark_strokes and 
            num_strokes >= 1
        )

        if is_blue_signature:
            conf = 0.95 if blue_ink_ratio >= 0.015 else 0.85
            res = {
                "is_signature": True,
                "confidence": conf,
                "ink_type": "blue_ink",
                "aspect_ratio": round(aspect_ratio, 2),
                "blue_ink_ratio": round(blue_ink_ratio, 3),
                "light_bg_ratio": round(light_bg_ratio, 2),
                "num_strokes": num_strokes,
                "reason": "Wide rectangular document with blue ink strokes on light background"
            }
            return to_native_types(res)

        if is_dark_signature and not has_blue_strokes:
            conf = 0.80 if dark_ink_ratio >= 0.015 else 0.70
            res = {
                "is_signature": True,
                "confidence": conf,
                "ink_type": "dark_ink",
                "aspect_ratio": round(aspect_ratio, 2),
                "dark_ink_ratio": round(dark_ink_ratio, 3),
                "light_bg_ratio": round(light_bg_ratio, 2),
                "num_strokes": num_strokes,
                "reason": "Wide rectangular document with dark ink strokes on light background"
            }
            return to_native_types(res)

        res = {
            "is_signature": False,
            "confidence": 0.0,
            "aspect_ratio": round(aspect_ratio, 2),
            "blue_ink_ratio": round(blue_ink_ratio, 3),
            "light_bg_ratio": round(light_bg_ratio, 2),
            "reason": "Does not match signature aspect ratio or ink stroke profile"
        }
        return to_native_types(res)

    except Exception as e:
        return {
            "is_signature": False,
            "confidence": 0.0,
            "error": str(e)
        }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python signature_detector.py <image_path>")
        sys.exit(1)

    image_file = sys.argv[1]
    res = detect_signature(image_file)
    print(json.dumps(res, indent=2, default=lambda o: float(o) if isinstance(o, (np.floating, np.float32, np.float64)) else (int(o) if isinstance(o, (np.integer, np.int32, np.int64)) else str(o))))
