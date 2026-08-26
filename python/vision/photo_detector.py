"""
Passport Photo & Face Geometry Detector Module.
Single Responsibility: Detects passport-size portrait photos using OpenCV YuNet DNN & skin-tone heuristics.
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
from python.config import YUNET_MODEL_PATH

# Suppress verbose OpenCV warnings
try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
except Exception:
    pass

def get_model_path() -> str:
    if not os.path.exists(YUNET_MODEL_PATH):
        os.makedirs(os.path.dirname(YUNET_MODEL_PATH), exist_ok=True)
        import urllib.request
        model_url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
        urllib.request.urlretrieve(model_url, YUNET_MODEL_PATH)
    return YUNET_MODEL_PATH

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

def evaluate_skin_silhouette(img, width: int, height: int, aspect_ratio: float) -> dict:
    """Heuristic fallback: Checks for single centered face/head skin-tone silhouette in upper half."""
    if not (0.55 <= aspect_ratio <= 1.35):
        return {"is_passport": False, "confidence": 0.0}

    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    skin_mask = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
    
    contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return {"is_passport": False, "confidence": 0.0}

    largest = max(contours, key=cv2.contourArea)
    area = float(cv2.contourArea(largest))
    area_ratio = area / float(width * height)

    if not (0.04 <= area_ratio <= 0.70):
        return {"is_passport": False, "confidence": 0.0}

    x, y, w, h = cv2.boundingRect(largest)
    center_x = float(x + w / 2.0)
    center_y = float(y + h / 2.0)

    horiz_offset = abs(center_x - (width / 2.0)) / float(width)
    vert_pos = center_y / float(height)

    if horiz_offset <= 0.28 and 0.12 <= vert_pos <= 0.72:
        return {
            "is_passport": True,
            "confidence": 0.85,
            "face_box": [int(x), int(y), int(w), int(h)],
            "aspect_ratio": round(float(aspect_ratio), 2),
            "face_area_ratio": round(float(area_ratio), 2),
            "reason": "Centered portrait silhouette matching passport photo geometry"
        }

    return {"is_passport": False, "confidence": 0.0}

def detect_passport_photo(image_path: str, min_confidence: float = 0.45) -> dict:
    if not os.path.exists(image_path):
        return {
            "is_passport_photo": False,
            "confidence": 0.0,
            "error": f"File not found: {image_path}"
        }

    try:
        img = cv2.imread(image_path)
        if img is None:
            return {
                "is_passport_photo": False,
                "confidence": 0.0,
                "error": "Failed to decode image"
            }

        height, width = img.shape[:2]
        if height < 50 or width < 50:
            return {
                "is_passport_photo": False,
                "confidence": 0.0,
                "reason": "Image dimensions too small"
            }

        aspect_ratio = float(width) / float(height)
        is_passport_aspect = 0.55 <= aspect_ratio <= 1.35

        # 1. Primary: Deep Learning YuNet Face Detector
        try:
            model_path = get_model_path()
            detector = cv2.FaceDetectorYN.create(model_path, "", (width, height), float(min_confidence))
            detector.setInputSize((width, height))
            _, faces = detector.detect(img)
        except Exception:
            faces = None

        if faces is not None and len(faces) > 0:
            valid_faces = [f for f in faces if float(f[-1]) >= min_confidence]
            if len(valid_faces) == 1:
                face = valid_faces[0]
                fx, fy, fw, fh = float(face[0]), float(face[1]), float(face[2]), float(face[3])
                face_confidence = float(face[-1])

                face_area_ratio = (fw * fh) / float(width * height)
                face_center_x = fx + fw / 2.0
                face_center_y = fy + fh / 2.0

                horiz_offset = abs(face_center_x - (width / 2.0)) / float(width)
                is_centered_horiz = horiz_offset <= 0.28
                vert_pos = face_center_y / float(height)
                is_proper_vert_pos = 0.12 <= vert_pos <= 0.72
                is_valid_face_size = 0.15 <= (fh / float(height)) <= 0.88

                is_passport = (
                    is_passport_aspect and 
                    is_centered_horiz and 
                    is_proper_vert_pos and 
                    is_valid_face_size
                )

                if is_passport:
                    res = {
                        "is_passport_photo": True,
                        "confidence": round(face_confidence * 0.95, 2),
                        "num_faces": 1,
                        "face_box": [int(fx), int(fy), int(fw), int(fh)],
                        "aspect_ratio": round(aspect_ratio, 2),
                        "face_height_ratio": round(fh / float(height), 2),
                        "face_area_ratio": round(face_area_ratio, 2),
                        "reason": "Single centered portrait face detected via YuNet DNN"
                    }
                    return to_native_types(res)

        # 2. Secondary: Skin Tone & Portrait Silhouette Heuristic
        silhouette_res = evaluate_skin_silhouette(img, width, height, aspect_ratio)
        if silhouette_res.get("is_passport"):
            res = {
                "is_passport_photo": True,
                "confidence": float(silhouette_res.get("confidence", 0.85)),
                "num_faces": 1,
                "face_box": silhouette_res.get("face_box"),
                "aspect_ratio": float(silhouette_res.get("aspect_ratio")),
                "face_area_ratio": float(silhouette_res.get("face_area_ratio")),
                "reason": str(silhouette_res.get("reason"))
            }
            return to_native_types(res)

        res = {
            "is_passport_photo": False,
            "confidence": 0.0,
            "num_faces": int(len(faces)) if faces is not None else 0,
            "aspect_ratio": round(aspect_ratio, 2),
            "reason": "No valid portrait face or silhouette matching passport photo geometry"
        }
        return to_native_types(res)

    except Exception as e:
        return {
            "is_passport_photo": False,
            "confidence": 0.0,
            "error": str(e)
        }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python photo_detector.py <image_path>")
        sys.exit(1)

    image_file = sys.argv[1]
    res = detect_passport_photo(image_file)
    print(json.dumps(res, indent=2, default=lambda o: float(o) if isinstance(o, (np.floating, np.float32, np.float64)) else (int(o) if isinstance(o, (np.integer, np.int32, np.int64)) else str(o))))
