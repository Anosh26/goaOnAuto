"""
Reusable UI Widgets for Raylib Declaration GUI.
Single Responsibility: Encapsulates input rows, interactive buttons, and media preview cards.
"""
from __future__ import annotations
import os
import pyray as rl
from .colors import (
    DRACULA_BG, DRACULA_CURRENT_LINE, DRACULA_FG,
    DRACULA_COMMENT, DRACULA_CYAN, DRACULA_PURPLE,
    DRACULA_RED, DRACULA_ORANGE
)
from .fonts import draw_text_clean, measure_text_clean
from .dialogs import open_file_dialog

class FormField:
    """Represents a single customizable declaration field."""
    def __init__(self, key: str, label: str, default_val: str = "", is_path: bool = False, is_required: bool = False):
        self.key = key
        self.label = label
        self.value = default_val
        self.is_path = is_path
        self.is_required = is_required
        self.rect = rl.Rectangle(0, 0, 0, 0)
        self.btn_rect = rl.Rectangle(0, 0, 0, 0)

def draw_button(
    text: str,
    rect: rl.Rectangle,
    bg_color: rl.Color,
    fg_color: rl.Color,
    font: rl.Font | None,
    font_size: int,
    mouse_pos: rl.Vector2,
    is_mouse_down: bool,
    border_color: rl.Color = DRACULA_COMMENT,
    roundness: float = 0.3
) -> bool:
    """Renders a rounded button and returns True if clicked."""
    hover = rl.check_collision_point_rec(mouse_pos, rect)
    effective_bg = rl.color_alpha(bg_color, 0.85) if hover else bg_color

    rl.draw_rectangle_rounded(rect, roundness, 6, effective_bg)
    rl.draw_rectangle_rounded_lines(rect, roundness, 6, border_color)

    text_w = measure_text_clean(font, text, font_size)
    text_x = rect.x + (rect.width - text_w) / 2
    text_y = rect.y + (rect.height - font_size) / 2
    draw_text_clean(font, text, text_x, text_y, font_size, fg_color)

    return hover and is_mouse_down

def draw_input_row(
    field: FormField,
    is_focused: bool,
    lbl_x: float,
    lbl_w: float,
    inp_x: float,
    inp_w: float,
    curr_y: float,
    inp_h: float,
    scale: float,
    scale_y: float,
    label_size: int,
    input_size: int,
    font_bold: rl.Font | None,
    font_regular: rl.Font | None,
    mouse_pos: rl.Vector2,
    is_mouse_down: bool,
    cursor_timer: float
) -> tuple[bool, bool]:
    """
    Renders a form field row: label, input box, blinking cursor, and browse button if path.
    Returns (clicked_row, value_changed_via_dialog).
    """
    is_invalid_path = field.is_path and field.value and not os.path.isfile(field.value)
    is_empty_required = field.is_required and not field.value

    field.rect = rl.Rectangle(inp_x, curr_y, inp_w, inp_h)

    # 1. Label
    label_col = DRACULA_ORANGE if (is_invalid_path or is_empty_required) else DRACULA_FG
    draw_text_clean(font_bold, field.label, lbl_x, curr_y + (inp_h - label_size) / 2, label_size, label_col)

    # 2. Input Box
    clicked_box = False
    val_changed = False

    if is_mouse_down and rl.check_collision_point_rec(mouse_pos, field.rect):
        clicked_box = True
        if field.is_path and (is_invalid_path or not field.value):
            picked = open_file_dialog(f"Path not correct. Select {field.label}")
            if picked:
                field.value = picked
                val_changed = True

    box_bg = DRACULA_CURRENT_LINE if is_focused else DRACULA_BG
    if is_invalid_path or is_empty_required:
        border_color = DRACULA_RED
    elif is_focused:
        border_color = DRACULA_CYAN
    else:
        border_color = DRACULA_COMMENT

    rl.draw_rectangle_rounded(field.rect, 0.25, 6, box_bg)
    rl.draw_rectangle_rounded_lines(field.rect, 0.25, 6, border_color)

    # Text rendering with left overflow clipping if value is too wide
    display_val = field.value
    char_w = max(6.0, measure_text_clean(font_regular, "W", input_size))
    max_char_len = max(10, int((inp_w - 20) / (char_w * 0.75)))
    if len(display_val) > max_char_len:
        display_val = "..." + display_val[-(max_char_len - 3):]

    text_y = curr_y + (inp_h - input_size) / 2
    draw_text_clean(font_regular, display_val, inp_x + int(10 * scale), text_y, input_size, DRACULA_FG)

    # Blinking cursor
    if is_focused and (int(cursor_timer * 2.5) % 2 == 0):
        tw = measure_text_clean(font_regular, display_val, input_size)
        cursor_x = inp_x + int(10 * scale) + tw + 2
        cursor_top = curr_y + int(4 * scale_y)
        cursor_bot = curr_y + inp_h - int(4 * scale_y)
        rl.draw_line(int(cursor_x), int(cursor_top), int(cursor_x), int(cursor_bot), DRACULA_CYAN)

    # 3. File Browse Button for path fields
    if field.is_path:
        btn_w = int(74 * scale)
        btn_x = inp_x + inp_w + int(10 * scale)
        field.btn_rect = rl.Rectangle(btn_x, curr_y, btn_w, inp_h)

        btn_hover = rl.check_collision_point_rec(mouse_pos, field.btn_rect)
        btn_bg = DRACULA_PURPLE if btn_hover else (DRACULA_RED if (is_invalid_path or is_empty_required) else DRACULA_CURRENT_LINE)
        btn_fg = DRACULA_BG if btn_hover else DRACULA_FG

        rl.draw_rectangle_rounded(field.btn_rect, 0.25, 6, btn_bg)
        rl.draw_rectangle_rounded_lines(field.btn_rect, 0.25, 6, DRACULA_COMMENT)

        browse_label = "Browse" if not (is_invalid_path or is_empty_required) else "Fix Path"
        draw_text_clean(font_bold, browse_label, btn_x + int(10 * scale), text_y, max(10, int(12 * scale)), btn_fg)

        if is_mouse_down and btn_hover:
            prompt = f"Select {field.label}" if not is_invalid_path else f"File not found. Please select {field.label}"
            picked = open_file_dialog(prompt)
            if picked:
                field.value = picked
                val_changed = True

    return clicked_box, val_changed

def draw_image_preview_card(
    title: str,
    texture: rl.Texture | None,
    rect: rl.Rectangle,
    scale: float,
    scale_y: float,
    font_bold: rl.Font | None,
    font_regular: rl.Font | None,
    mouse_pos: rl.Vector2,
    is_mouse_down: bool,
    missing_msg: str = "⚠️ Missing\nClick to Browse"
) -> bool:
    """
    Renders an image preview card (e.g. Passport Photo or Signature).
    Returns True if user clicked the card to browse a new file.
    """
    has_tex = (texture is not None and texture.id > 0)
    border_color = DRACULA_COMMENT if has_tex else DRACULA_RED

    rl.draw_rectangle(int(rect.x), int(rect.y), int(rect.width), int(rect.height), DRACULA_BG)
    rl.draw_rectangle_lines(int(rect.x), int(rect.y), int(rect.width), int(rect.height), border_color)

    if has_tex:
        src_rect = rl.Rectangle(0, 0, texture.width, texture.height)
        dst_rect = rl.Rectangle(rect.x + 2, rect.y + 2, rect.width - 4, rect.height - 4)
        rl.draw_texture_pro(texture, src_rect, dst_rect, rl.Vector2(0, 0), 0.0, rl.WHITE)
    else:
        draw_text_clean(font_regular, missing_msg, rect.x + int(14 * scale), rect.y + rect.height / 2 - int(14 * scale_y), int(12 * scale), DRACULA_RED)

    # Subtitle under card
    draw_text_clean(font_bold, title, rect.x + int(12 * scale), rect.y + rect.height + int(6 * scale_y), int(13 * scale), DRACULA_FG)

    clicked = is_mouse_down and rl.check_collision_point_rec(mouse_pos, rect)
    return clicked
