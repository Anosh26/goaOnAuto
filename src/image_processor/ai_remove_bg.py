import sys
import os
import argparse
from PIL import Image
import onnxruntime as ort
from rembg import remove, new_session

def get_best_providers():
    available = ort.get_available_providers()
    providers = []
    if "CUDAExecutionProvider" in available:
        providers.append("CUDAExecutionProvider")
        print("[AI Engine] CUDA GPU Acceleration detected (RTX / NVIDIA GPU).")
    if "TensorrtExecutionProvider" in available:
        providers.append("TensorrtExecutionProvider")
    providers.append("CPUExecutionProvider")
    if len(providers) == 1:
        print("[AI Engine] Running on CPU (No CUDA GPU detected or available).")
    return providers

def process_ai_background(input_path: str, output_path: str, model_name: str = "u2net_human_seg", crisp_edges: bool = False, mask_threshold: int = 128):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Set ONNX log level to ERROR to suppress EP warnings
    os.environ["ORT_LOGGING_LEVEL"] = "3"

    session = None
    available = ort.get_available_providers()
    
    if "CUDAExecutionProvider" in available:
        try:
            print("[AI Engine] Attempting CUDA GPU Acceleration (NVIDIA RTX 4060)...")
            session = new_session(model_name, providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
            print(f"[AI Engine] CUDA GPU Acceleration active (Human Seg Model: {model_name}).")
        except Exception as e:
            print(f"[AI Engine] CUDA initialization notice ({e}). Falling back to CPU...")

    if session is None:
        print(f"[AI Engine] Initializing CPU Execution Engine (Human Seg Model: {model_name})...")
        session = new_session(model_name, providers=["CPUExecutionProvider"])

    with Image.open(input_path) as input_img:
        # Perform AI human body, traps, chest, & clothing segmentation
        print("[AI Engine] Extracting full human silhouette (Face, Hair, Traps, Chest, Clothing)...")
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
                print(f"[AI Engine] Applying binarized edge cutoff (Threshold: {mask_threshold})...")
                alpha = alpha.point(lambda p: 255 if p >= mask_threshold else 0)

            white_bg = Image.new("RGB", rgba_result.size, (255, 255, 255))
            white_bg.paste(Image.merge("RGB", (r, g, b)), mask=alpha)
        else:
            white_bg = Image.new("RGB", rgba_result.size, (255, 255, 255))
            white_bg.paste(rgba_result)

        # Save output image
        white_bg.save(output_path, quality=95)
        print(f"[AI Engine] Successfully processed human silhouette -> {output_path}")

def main():
    parser = argparse.ArgumentParser(description="AI Human & Subject Background Removal")
    parser.add_argument("input", help="Path to input image")
    parser.add_argument("output", help="Path to output image")
    parser.add_argument("--model", default="u2net_human_seg", help="rembg model (default: u2net_human_seg for human silhouette)")
    parser.add_argument("--crisp", action="store_true", help="Enable binarized crisp edge cutoff")
    parser.add_argument("--threshold", type=int, default=128, help="Mask binarization threshold (0-255, default: 128)")

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
