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

def process_ai_background(input_path: str, output_path: str, model_name: str = "u2netp"):
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
            print("[AI Engine] CUDA GPU Acceleration active.")
        except Exception as e:
            print(f"[AI Engine] CUDA initialization notice ({e}). Falling back to CPU...")

    if session is None:
        print("[AI Engine] Initializing CPU Execution Engine...")
        session = new_session(model_name, providers=["CPUExecutionProvider"])

    with Image.open(input_path) as input_img:
        # Perform AI background removal with alpha channel
        rgba_result = remove(input_img, session=session)

        # Composite onto solid white background (255, 255, 255)
        white_bg = Image.new("RGB", rgba_result.size, (255, 255, 255))
        if rgba_result.mode == "RGBA":
            white_bg.paste(rgba_result, mask=rgba_result.split()[3])
        else:
            white_bg.paste(rgba_result)

        # Save output image
        white_bg.save(output_path, quality=95)
        print(f"[AI Engine] Successfully processed background -> {output_path}")

def main():
    parser = argparse.ArgumentParser(description="AI Human & Subject Background Removal")
    parser.add_argument("input", help="Path to input image")
    parser.add_argument("output", help="Path to output image")
    parser.add_argument("--model", default="u2netp", help="rembg model (default: u2netp for fast processing)")

    args = parser.parse_args()

    try:
        process_ai_background(args.input, args.output, args.model)
    except Exception as e:
        print(f"[AI Engine Error] {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
