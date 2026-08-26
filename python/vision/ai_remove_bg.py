"""
AI Human Silhouette & Background Replacement Module.
Single Responsibility: Removes photo backgrounds and generates clean white background passport photos using RTX 4060 CUDA segmentation.
"""
import sys
import os
import argparse

# Ensure project root in sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PIL import Image
import onnxruntime as ort
from rembg import remove, new_session
from python.config import get_cuda_providers

_cached_session = None

def get_segmentation_session(model_name: str = "u2net_human_seg"):
    global _cached_session
    if _cached_session is None:
        os.environ["ORT_LOGGING_LEVEL"] = "3"
        providers = get_cuda_providers()
        try:
            if "CUDAExecutionProvider" in providers:
                _cached_session = new_session(model_name, providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
            else:
                _cached_session = new_session(model_name, providers=["CPUExecutionProvider"])
        except Exception:
            _cached_session = new_session(model_name, providers=["CPUExecutionProvider"])
    return _cached_session

def process_ai_background(input_path: str, output_path: str, model_name: str = "u2net_human_seg", crisp_edges: bool = False, mask_threshold: int = 128):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    session = get_segmentation_session(model_name)

    with Image.open(input_path) as input_img:
        rgba_result = remove(
            input_img, 
            session=session, 
            alpha_matting=True,
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10,
            alpha_matting_erode_size=10
        )

        if rgba_result.mode == "RGBA":
            r, g, b, alpha = rgba_result.split()

            if crisp_edges:
                alpha = alpha.point(lambda p: 255 if p >= mask_threshold else 0)

            white_bg = Image.new("RGB", rgba_result.size, (255, 255, 255))
            white_bg.paste(Image.merge("RGB", (r, g, b)), mask=alpha)
        else:
            white_bg = Image.new("RGB", rgba_result.size, (255, 255, 255))
            white_bg.paste(rgba_result)

        white_bg.save(output_path, quality=95)

def main():
    parser = argparse.ArgumentParser(description="AI Human & Subject Background Removal")
    parser.add_argument("input", help="Path to input image")
    parser.add_argument("output", help="Path to output image")
    parser.add_argument("--model", default="u2net_human_seg", help="rembg model (default: u2net_human_seg)")
    parser.add_argument("--crisp", action="store_true", help="Enable binarized crisp edge cutoff")
    parser.add_argument("--threshold", type=int, default=128, help="Mask binarization threshold (0-255)")

    args = parser.parse_args()

    try:
        process_ai_background(
            input_path=args.input, 
            output_path=args.output, 
            model_name=args.model, 
            crisp_edges=args.crisp, 
            mask_threshold=args.threshold
        )
    except Exception as e:
        print(f"[AI Engine Error] {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
