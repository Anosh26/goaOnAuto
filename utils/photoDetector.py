import sys
import os
import json
import cv2
import numpy as np

# Suppress verbose OpenCV warnings
try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
except:
    pass

MODEL_FILENAME = "face_detection_yunet_2023mar.onnx"

def get_model_path() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(script_dir, MODEL_FILENAME)
    if not os.path.exists(model_path):
        import urllib.request
        model_url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
        urllib.request.urlretrieve(model_url, model_path)
    return model_path

def evaluate_skin_silhouette(img, width: int, height: int, aspect_ratio: float) -> dict:
    """
    Heuristic fallback: Checks for single centered face/head skin-tone silhouette in upper half.
    """
    if not (0.60 <= aspect_ratio <= 1.30):
        return {"is_passport": False, "confidence": 0.0}

    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    # Standard YCrCb skin tone color space range
    skin_mask = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
    
    contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return {"is_passport": False, "confidence": 0.0}

    # Find dominant skin-like region
    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    area_ratio = area / float(width * height)

    if not (0.05 <= area_ratio <= 0.65):
        return {"is_passport": False, "confidence": 0.0}

    x, y, w, h = cv2.boundingRect(largest)
    center_x = x + w / 2.0
    center_y = y + h / 2.0

    horiz_offset = abs(center_x - (width / 2.0)) / float(width)
    vert_pos = center_y / float(height)

    # Face/head region should be roughly centered and in the upper 70% of frame
    if horiz_offset <= 0.25 and 0.15 <= vert_pos <= 0.70:
        return {
            "is_passport": True,
            "confidence": 0.85,
            "face_box": [int(x), int(y), int(w), int(h)],
            "aspect_ratio": round(aspect_ratio, 2),
            "face_area_ratio": round(area_ratio, 2),
            "reason": "Centered portrait silhouette matching passport photo geometry (Color/Geometry Heuristic)"
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
        # Read image
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

        aspect_ratio = width / float(height)
        is_passport_aspect = 0.60 <= aspect_ratio <= 1.30

        # 1. Primary: Deep Learning YuNet Face Detector
        try:
            model_path = get_model_path()
            detector = cv2.FaceDetectorYN.create(model_path, "", (width, height), min_confidence)
            detector.setInputSize((width, height))
            _, faces = detector.detect(img)
        except Exception:
            faces = None

        if faces is not None and len(faces) > 0:
            valid_faces = [f for f in faces if f[-1] >= min_confidence]
            if len(valid_faces) == 1:
                face = valid_faces[0]
                fx, fy, fw, fh = face[:4]
                face_confidence = float(face[-1])

                face_area_ratio = (fw * fh) / float(width * height)
                face_center_x = fx + fw / 2.0
                face_center_y = fy + fh / 2.0

                horiz_offset = abs(face_center_x - (width / 2.0)) / float(width)
                is_centered_horiz = horiz_offset <= 0.25
                vert_pos = face_center_y / float(height)
                is_proper_vert_pos = 0.15 <= vert_pos <= 0.70
                is_valid_face_size = 0.18 <= (fh / float(height)) <= 0.85

                is_passport = (
                    is_passport_aspect and 
                    is_centered_horiz and 
                    is_proper_vert_pos and 
                    is_valid_face_size
                )

                if is_passport:
                    return {
                        "is_passport_photo": True,
                        "confidence": round(face_confidence * 0.95, 2),
                        "num_faces": 1,
                        "face_box": [int(fx), int(fy), int(fw), int(fh)],
                        "aspect_ratio": round(aspect_ratio, 2),
                        "face_height_ratio": round(fh / float(height), 2),
                        "face_area_ratio": round(face_area_ratio, 2),
                        "reason": "Single centered portrait face detected via YuNet DNN"
                    }

        # 2. Secondary: Skin Tone & Portrait Silhouette Heuristic
        silhouette_res = evaluate_skin_silhouette(img, width, height, aspect_ratio)
        if silhouette_res.get("is_passport"):
            return {
                "is_passport_photo": True,
                "confidence": silhouette_res.get("confidence", 0.85),
                "num_faces": 1,
                "face_box": silhouette_res.get("face_box"),
                "aspect_ratio": silhouette_res.get("aspect_ratio"),
                "face_area_ratio": silhouette_res.get("face_area_ratio"),
                "reason": silhouette_res.get("reason")
            }

        return {
            "is_passport_photo": False,
            "confidence": 0.0,
            "num_faces": len(faces) if faces is not None else 0,
            "aspect_ratio": round(aspect_ratio, 2),
            "reason": "No valid portrait face or silhouette matching passport photo geometry"
        }

    except Exception as e:
        return {
            "is_passport_photo": False,
            "confidence": 0.0,
            "error": str(e)
        }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python photoDetector.py <image_path>")
        sys.exit(1)

    image_file = sys.argv[1]
    res = detect_passport_photo(image_file)
    print(json.dumps(res, indent=2))
