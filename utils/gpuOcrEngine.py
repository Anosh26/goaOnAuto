import sys
import os
import json

def detect_device_mode():
    """Detect if NVIDIA GPU (CUDA) is available for OCR"""
    try:
        import torch
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            return True, f"GPU CUDA ({device_name})"
    except ImportError:
        pass

    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        if 'CUDAExecutionProvider' in providers:
            return True, "GPU ONNX CUDA"
    except ImportError:
        pass

    return False, "CPU Fallback"

def run_ocr(image_path: str):
    if not os.path.exists(image_path):
        return {"error": f"File not found: {image_path}", "text": "", "device": "N/A"}

    is_gpu, device_desc = detect_device_mode()
    extracted_text = ""

    # Strategy 1: Try EasyOCR (Supports GPU CUDA natively)
    try:
        import easyocr
        reader = easyocr.Reader(['en'], gpu=is_gpu)
        results = reader.readtext(image_path, detail=0)
        extracted_text = "\n".join(results)
        return {
            "text": extracted_text,
            "engine": "EasyOCR",
            "is_gpu": is_gpu,
            "device": device_desc
        }
    except Exception as e:
        pass

    # Strategy 2: Try PyTesseract / Tesseract
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(image_path)
        extracted_text = pytesseract.image_to_string(img)
        return {
            "text": extracted_text,
            "engine": "PyTesseract",
            "is_gpu": False,
            "device": f"{device_desc} (Tesseract)"
        }
    except Exception as e:
        pass

    return {
        "text": "",
        "engine": "None",
        "is_gpu": is_gpu,
        "device": device_desc,
        "fallback_to_wasm": True
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        is_gpu, desc = detect_device_mode()
        print(json.dumps({"is_gpu": is_gpu, "device": desc}))
        sys.exit(0)

    image_path = sys.argv[1]
    res = run_ocr(image_path)
    print(json.dumps(res))
