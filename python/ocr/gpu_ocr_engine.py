"""
EasyOCR CUDA GPU OCR Engine with PDF & Image Support.
Single Responsibility: Performs optical character recognition on document images & PDFs using GPU CUDA.
"""
import os
import sys
import json
import numpy as np

# Ensure project root in sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from python.config import is_cuda_available

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

_cached_reader = None

def get_easyocr_reader(is_gpu: bool):
    global _cached_reader
    if _cached_reader is None:
        import easyocr
        _cached_reader = easyocr.Reader(['en'], gpu=is_gpu)
    return _cached_reader

def extract_from_pdf(pdf_path: str, is_gpu: bool, device_desc: str):
    # 1. Native text extraction (Fast ~2ms)
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        pdf_text = "\n".join([page.extract_text() or "" for page in reader.pages[:2]])
        if len(pdf_text.strip()) > 30:
            return {
                "text": pdf_text,
                "engine": "PyPDF-Native",
                "is_gpu": is_gpu,
                "device": device_desc
            }
    except Exception:
        pass

    # 2. Render first page to bitmap image
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(pdf_path)
        if len(pdf) > 0:
            pil_image = pdf[0].render(scale=2).to_pil()
            img_np = np.array(pil_image)
            reader = get_easyocr_reader(is_gpu)
            results = reader.readtext(img_np, detail=0)
            return {
                "text": "\n".join(results),
                "engine": "EasyOCR-PDF",
                "is_gpu": is_gpu,
                "device": device_desc
            }
    except Exception:
        pass

    return None

def run_ocr(image_path: str):
    if not os.path.exists(image_path):
        return {"error": f"File not found: {image_path}", "text": "", "device": "N/A"}

    is_gpu, device_desc = detect_device_mode()

    if image_path.lower().endswith(".pdf"):
        pdf_res = extract_from_pdf(image_path, is_gpu, device_desc)
        if pdf_res:
            return pdf_res

    # Strategy 1: Try EasyOCR (Supports GPU CUDA natively)
    try:
        reader = get_easyocr_reader(is_gpu)
        results = reader.readtext(image_path, detail=0)
        extracted_text = "\n".join(results)
        return {
            "text": extracted_text,
            "engine": "EasyOCR",
            "is_gpu": is_gpu,
            "device": device_desc
        }
    except Exception:
        pass

    # Strategy 2: Try PyTesseract
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
    except Exception:
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

    if sys.argv[1] == "--batch":
        paths = sys.argv[2:]
        results = [run_ocr(p) for p in paths]
        print(json.dumps(results))
        sys.exit(0)

    image_path = sys.argv[1]
    res = run_ocr(image_path)
    print(json.dumps(res))
