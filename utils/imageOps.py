import sys
import os
from PIL import Image

def merge_vertical(front_path: str, back_path: str, output_path: str):
    """
    Stitches two card images vertically:
    - Front Side on top
    - Back Side on bottom
    """
    img_front = Image.open(front_path).convert('RGB')
    img_back = Image.open(back_path).convert('RGB')

    # Normalize widths to match front image width
    target_width = max(img_front.width, img_back.width)
    
    if img_front.width != target_width:
        h = int(img_front.height * (target_width / img_front.width))
        img_front = img_front.resize((target_width, h), Image.Resampling.LANCZOS)
        
    if img_back.width != target_width:
        h = int(img_back.height * (target_width / img_back.width))
        img_back = img_back.resize((target_width, h), Image.Resampling.LANCZOS)

    # Combine vertically
    canvas = Image.new('RGB', (target_width, img_front.height + img_back.height), (255, 255, 255))
    canvas.paste(img_front, (0, 0))
    canvas.paste(img_back, (0, img_front.height))
    
    canvas.save(output_path, quality=95)
    print(f"SUCCESS: Merged vertically to {output_path}")

def convert_to_pdf(image_paths: list[str], output_pdf_path: str):
    """
    Combines multiple image pages into a single multi-page PDF document.
    """
    images = []
    for p in image_paths:
        if os.path.exists(p):
            images.append(Image.open(p).convert('RGB'))

    if not images:
        raise ValueError("No valid images provided for PDF conversion")

    images[0].save(output_pdf_path, save_all=True, append_images=images[1:])
    print(f"SUCCESS: Multipage PDF saved to {output_pdf_path}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage:")
        print("  python imageOps.py merge_vertical <front_path> <back_path> <output_path>")
        print("  python imageOps.py convert_to_pdf <output_pdf_path> <img1> <img2> ...")
        sys.exit(1)

    cmd = sys.argv[1]
    
    if cmd == "merge_vertical":
        merge_vertical(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "convert_to_pdf":
        output_pdf = sys.argv[2]
        img_list = sys.argv[3:]
        convert_to_pdf(img_list, output_pdf)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
