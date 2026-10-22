"""
DocTR Modern Deep Learning GPU OCR Engine with PDF & Image Support.
Single Responsibility: Performs optical character recognition on document images & PDFs using DocTR (PyTorch CUDA).
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

_cached_predictor = None

def get_doctr_predictor(is_gpu: bool):
    """Initializes and returns cached DocTR OCR predictor on GPU/CPU."""
    global _cached_predictor
    if _cached_predictor is None:
        from doctr.models import ocr_predictor
        det_arch = os.environ.get("DOCTR_DET_ARCH", "db_mobilenet_v3_large")
        reco_arch = os.environ.get("DOCTR_RECO_ARCH", "crnn_vgg16_bn")
        predictor = ocr_predictor(det_arch=det_arch, reco_arch=reco_arch, pretrained=True)
        if is_gpu:
            predictor = predictor.cuda()
        _cached_predictor = predictor
    return _cached_predictor

def get_easyocr_reader(is_gpu: bool):
    """Backwards-compatibility alias pointing to modern DocTR predictor."""
    return get_doctr_predictor(is_gpu)

def extract_text_from_doctr_result(doc_result) -> str:
    """Extracts structured text lines preserving horizontal word spacing and line breaks."""
    lines = []
    for page in doc_result.pages:
        for block in page.blocks:
            for line in block.lines:
                line_words = [w.value for w in line.words if w.value]
                if line_words:
                    lines.append(" ".join(line_words))
    return "\n".join(lines)

def extract_from_pdf(pdf_path: str, is_gpu: bool, device_desc: str):
    """Extracts text from PDF via native digital text stream or DocTR OCR on rasterized pages."""
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

    # 2. Render and OCR scanned PDF pages with DocTR
    try:
        from doctr.io import DocumentFile
        predictor = get_doctr_predictor(is_gpu)
        doc = DocumentFile.from_pdf(pdf_path)
        if doc and len(doc) > 0:
            # Process up to first 2 pages for document classification
            pages_to_process = doc[:2]
            res = predictor(pages_to_process)
            extracted_text = extract_text_from_doctr_result(res)
            return {
                "text": extracted_text,
                "engine": "DocTR-PDF",
                "is_gpu": is_gpu,
                "device": device_desc
            }
    except Exception:
        pass

    return None

def run_ocr(image_path: str):
    """Performs optical character recognition on an image or PDF file using DocTR GPU CUDA."""
    if not os.path.exists(image_path):
        return {"error": f"File not found: {image_path}", "text": "", "device": "N/A"}

    is_gpu, device_desc = detect_device_mode()

    if image_path.lower().endswith(".pdf"):
        pdf_res = extract_from_pdf(image_path, is_gpu, device_desc)
        if pdf_res:
            return pdf_res

    # Strategy 1: Try DocTR (PyTorch GPU CUDA native)
    try:
        from doctr.io import DocumentFile
        predictor = get_doctr_predictor(is_gpu)
        doc = DocumentFile.from_images(image_path)
        res = predictor(doc)
        extracted_text = extract_text_from_doctr_result(res)
        return {
            "text": extracted_text,
            "engine": "DocTR",
            "is_gpu": is_gpu,
            "device": device_desc
        }
    except Exception:
        pass

    # Strategy 2: Try PyTesseract fallback
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
        print(json.dumps({"is_gpu": is_gpu, "device": desc, "engine": "DocTR"}))
        sys.exit(0)

    if sys.argv[1] == "--batch":
        paths = sys.argv[2:]
        results = [run_ocr(p) for p in paths]
        print(json.dumps(results))
        sys.exit(0)

    image_path = sys.argv[1]
    res = run_ocr(image_path)
    print(json.dumps(res))
