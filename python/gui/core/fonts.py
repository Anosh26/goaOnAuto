"""
Font Loader and High-DPI Bilinear Typography Renderer for Raylib.
Single Responsibility: Manages JetBrainsMono fonts and renders/measures crisp text.
"""
from __future__ import annotations
import os
import sys
import pyray as rl

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def load_custom_font(font_filename: str, base_size: int = 48) -> rl.Font | None:
    """Loads JetBrainsMono / JetBrainsMono Nerd Font with crisp bilinear filtering."""
    home_dir = os.path.expanduser("~")
    candidates = [
        os.path.join(_PROJECT_ROOT, "assets", "fonts", font_filename),
        os.path.join(home_dir, "AppData", "Local", "Microsoft", "Windows", "Fonts", "JetBrainsMonoNerdFont-Regular.ttf"),
        os.path.join(home_dir, "AppData", "Local", "Microsoft", "Windows", "Fonts", "JetBrainsMonoNerdFontMono-Regular.ttf"),
        os.path.join(home_dir, "AppData", "Local", "Microsoft", "Windows", "Fonts", "JetBrainsMono-Regular.ttf"),
        "C:/Windows/Fonts/JetBrainsMonoNerdFont-Regular.ttf",
        "C:/Windows/Fonts/JetBrainsMono-Regular.ttf",
        "C:/Windows/Fonts/cascadiacode.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for fp in candidates:
        if os.path.exists(fp):
            try:
                font = rl.load_font_ex(fp.encode('utf-8'), base_size, None, 0)
                if font and font.baseSize > 0:
                    rl.set_texture_filter(font.texture, rl.TEXTURE_FILTER_BILINEAR)
                    return font
            except Exception:
                continue
    return None

def draw_text_clean(font: rl.Font | None, text: str, x: float, y: float, font_size: int, color: rl.Color) -> None:
    """Renders crisp text using loaded JetBrainsMono TTF font with fallback."""
    try:
        raw_bytes = text.encode('utf-8', 'ignore')
        if font and font.baseSize > 0:
            rl.draw_text_ex(font, raw_bytes, rl.Vector2(float(x), float(y)), float(font_size), 1.0, color)
        else:
            rl.draw_text(raw_bytes, int(x), int(y), font_size, color)
    except Exception:
        pass

def measure_text_clean(font: rl.Font | None, text: str, font_size: int) -> float:
    """Measures exact text width using loaded JetBrainsMono TTF font."""
    try:
        raw_bytes = text.encode('utf-8', 'ignore')
        if font and font.baseSize > 0:
            return float(rl.measure_text_ex(font, raw_bytes, float(font_size), 1.0).x)
        else:
            return float(rl.measure_text(raw_bytes, font_size))
    except Exception:
        return float(len(text) * font_size * 0.6)
