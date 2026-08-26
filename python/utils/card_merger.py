"""
ID Card Image Vertical Stitcher.
Single Responsibility: Vertically stitches two card images (Front top, Back bottom) into a normalized merged image.
"""
import sys
import os
from PIL import Image

def merge_vertical(front_path: str, back_path: str, output_path: str):
    if not os.path.exists(front_path):
        raise FileNotFoundError(f"Front image not found: {front_path}")
    if not os.path.exists(back_path):
        raise FileNotFoundError(f"Back image not found: {back_path}")

    img_front = Image.open(front_path).convert('RGB')
    img_back = Image.open(back_path).convert('RGB')

    target_width = max(img_front.width, img_back.width)
    
    if img_front.width != target_width:
        h = int(img_front.height * (target_width / img_front.width))
        img_front = img_front.resize((target_width, h), Image.Resampling.LANCZOS)
        
    if img_back.width != target_width:
        h = int(img_back.height * (target_width / img_back.width))
        img_back = img_back.resize((target_width, h), Image.Resampling.LANCZOS)

    canvas = Image.new('RGB', (target_width, img_front.height + img_back.height), (255, 255, 255))
    canvas.paste(img_front, (0, 0))
    canvas.paste(img_back, (0, img_front.height))
    
    canvas.save(output_path, quality=95)
    print(f"SUCCESS: Merged vertically to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python card_merger.py <front_path> <back_path> <output_path>")
        sys.exit(1)
    merge_vertical(sys.argv[1], sys.argv[2], sys.argv[3])
