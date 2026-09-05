"""
Centralized Python Configuration & GPU Device Detection Module.
Single Responsibility: Path resolution & hardware acceleration discovery.
"""
import os
import sys

# Base project directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Asset & Model directories
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
MODELS_DIR = os.path.join(ASSETS_DIR, "models")
OCR_DATA_DIR = os.path.join(ASSETS_DIR, "ocr")

# Face Detection Model (OpenCV YuNet ONNX)
YUNET_MODEL_PATH = os.path.join(MODELS_DIR, "face_detection_yunet_2023mar.onnx")

# Fallback for backwards-compatibility if not moved
if not os.path.exists(YUNET_MODEL_PATH):
    fallback_model = os.path.join(PROJECT_ROOT, "utils", "face_detection_yunet_2023mar.onnx")
    if os.path.exists(fallback_model):
        YUNET_MODEL_PATH = fallback_model

def _can_load_cuda_provider() -> bool:
    """Verifies that the required CUDA shared libraries are present before invoking CUDAExecutionProvider."""
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        for dll_name in ("cublasLt64_12.dll", "cublasLt64_13.dll", "cublasLt64_11.dll"):
            h = ctypes.windll.kernel32.LoadLibraryW(dll_name)
            if h:
                ctypes.windll.kernel32.FreeLibrary(h)
                return True
        return False
    except Exception:
        return False

def get_cuda_providers():
    """Returns available ONNX Runtime execution providers prioritizing CUDA."""
    try:
        import onnxruntime as ort
        available = ort.get_available_providers()
        providers = []
        if "CUDAExecutionProvider" in available and _can_load_cuda_provider():
            providers.append("CUDAExecutionProvider")
        if "TensorrtExecutionProvider" in available and _can_load_cuda_provider():
            providers.append("TensorrtExecutionProvider")
        providers.append("CPUExecutionProvider")
        return providers
    except Exception:
        return ["CPUExecutionProvider"]

def is_cuda_available() -> bool:
    """Checks if NVIDIA GPU CUDA is available via PyTorch or ONNX Runtime."""
    try:
        import torch
        if torch.cuda.is_available():
            return True
    except Exception:
        pass
    providers = get_cuda_providers()
    return "CUDAExecutionProvider" in providers
