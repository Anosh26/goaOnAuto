"""
Multipage PDF Document Converter.
Single Responsibility: Combines a sequence of image files into a single multipage PDF document.
"""
import sys
import os
from PIL import Image

def convert_to_pdf(image_paths: list[str], output_pdf_path: str):
    images = []
    for p in image_paths:
        if os.path.exists(p):
            images.append(Image.open(p).convert('RGB'))

    if not images:
        raise ValueError("No valid images provided for PDF conversion")

    images[0].save(output_pdf_path, save_all=True, append_images=images[1:])
    print(f"SUCCESS: Multipage PDF saved to {output_pdf_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python pdf_converter.py <output_pdf_path> <img1> <img2> ...")
        sys.exit(1)
    output_pdf = sys.argv[1]
    img_list = sys.argv[2:]
    convert_to_pdf(img_list, output_pdf)
