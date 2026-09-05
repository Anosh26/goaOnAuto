"""
Persistent GPU Batch Worker Daemon.
Single Responsibility: Manages long-running JSON-RPC worker keeping OCR & vision models loaded in GPU VRAM.
"""
import sys
import os
import json

# Ensure unbuffered standard streams
sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure(line_buffering=True)

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from python.vision.photo_detector import detect_passport_photo
from python.vision.signature_detector import detect_signature
from python.vision.aadhaar_qr import detect_and_decode_qr
from python.ocr.gpu_ocr_engine import detect_device_mode, run_ocr
import psutil
try:
    import torch
    if torch.cuda.is_available():
        # Enforce GPU Limit: Cap VRAM usage at 90% max to preserve headroom for OS & Display
        torch.cuda.set_per_process_memory_fraction(0.90, 0)
except Exception:
    pass

class GpuWorkerService:
    def __init__(self):
        self.is_gpu, self.device_desc = detect_device_mode()
        self.engine_name = "EasyOCR (GPU CUDA)" if self.is_gpu else "EasyOCR (CPU)"

    def get_system_metrics(self) -> dict:
        mem = psutil.virtual_memory()
        cpu_pct = psutil.cpu_percent(interval=None)
        free_ram_gb = round(mem.available / (1024 ** 3), 2)
        total_ram_gb = round(mem.total / (1024 ** 3), 2)
        
        gpu_vram_mb = 0
        try:
            if torch.cuda.is_available():
                gpu_vram_mb = round(torch.cuda.memory_allocated(0) / (1024 ** 2), 1)
        except Exception:
            pass

        return {
            "free_ram_gb": free_ram_gb,
            "total_ram_gb": total_ram_gb,
            "cpu_usage_percent": cpu_pct,
            "cpu_free_percent": round(100.0 - cpu_pct, 1),
            "gpu_vram_used_mb": gpu_vram_mb,
            "gpu_vram_limit_percent": 90.0
        }

    def process_single_ocr(self, image_path: str) -> dict:

        return run_ocr(image_path)

    def process_single_full(self, image_path: str) -> dict:
        """Runs OCR + visual fallbacks (passport photo & signature detection)."""
        ocr_res = self.process_single_ocr(image_path)
        text = ocr_res.get("text", "")

        is_photo = False
        photo_confidence = 0.0
        photo_reason = ""

        is_signature = False
        sig_confidence = 0.0
        sig_ink = None
        sig_reason = ""

        # Visual check heuristics if text is small or minimal
        if len(text.strip()) < 35 and not image_path.lower().endswith(".pdf"):
            p_res = detect_passport_photo(image_path)
            if p_res.get("is_passport_photo"):
                is_photo = True
                photo_confidence = float(p_res.get("confidence", 0.9))
                photo_reason = p_res.get("reason", "")

            if not is_photo:
                s_res = detect_signature(image_path)
                if s_res.get("is_signature"):
                    is_signature = True
                    sig_confidence = float(s_res.get("confidence", 0.85))
                    sig_ink = s_res.get("ink_type", "blue_ink")
                    sig_reason = s_res.get("reason", "")

        return {
            "path": image_path,
            "text": text,
            "engine": ocr_res.get("engine", "EasyOCR"),
            "is_gpu": ocr_res.get("is_gpu", self.is_gpu),
            "device": ocr_res.get("device", self.device_desc),
            "is_photo": is_photo,
            "photo_confidence": photo_confidence,
            "photo_reason": photo_reason,
            "is_signature": is_signature,
            "signature_confidence": sig_confidence,
            "signature_ink": sig_ink,
            "signature_reason": sig_reason
        }

    def process_batch(self, image_paths: list) -> list:
        results = []
        for img_path in image_paths:
            results.append(self.process_single_full(img_path))
        return results

def run_daemon():
    worker = GpuWorkerService()
    
    ready_msg = {
        "status": "ready",
        "is_gpu": worker.is_gpu,
        "device": worker.device_desc,
        "engine": worker.engine_name
    }
    sys.stdout.write(json.dumps(ready_msg) + "\n")
    sys.stdout.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
        except Exception as e:
            err_resp = {"error": f"Invalid JSON input: {str(e)}"}
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()
            continue

        req_id = req.get("id")
        action = req.get("action", "batch_process")

        if action == "ping":
            resp = {
                "id": req_id,
                "status": "pong",
                "is_gpu": worker.is_gpu,
                "device": worker.device_desc
            }
        elif action == "exit":
            resp = {"id": req_id, "status": "exiting"}
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
            break
        elif action == "batch_process":
            paths = req.get("paths", [])
            batch_res = worker.process_batch(paths)
            resp = {
                "id": req_id,
                "success": True,
                "is_gpu": worker.is_gpu,
                "device": worker.device_desc,
                "results": batch_res
            }
        elif action == "ocr":
            path = req.get("path", "")
            res = worker.process_single_full(path)
            resp = {
                "id": req_id,
                "success": True,
                "is_gpu": worker.is_gpu,
                "device": worker.device_desc,
                "result": res
            }
        elif action == "aadhaar_qr":
            path = req.get("path", "")
            res = detect_and_decode_qr(path)
            resp = {
                "id": req_id,
                "success": True,
                "result": res
            }
        else:
            resp = {"id": req_id, "error": f"Unknown action: {action}"}

        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    run_daemon()
