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
        self.cursor_pos = len(default_val)
        self.scroll_offset = 0

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
    cursor_timer: float,
    clip_min_y: float = 0.0,
    clip_max_y: float = 99999.0
) -> tuple[bool, bool]:
    """
    Renders a form field row: label, input box, blinking cursor, and browse button if path.
    Supports point-and-click cursor placement and automatic horizontal scrolling.
    Returns (clicked_row, value_changed_via_dialog).
    """
    is_invalid_path = field.is_path and field.value and not os.path.isfile(field.value)
    is_empty_required = field.is_required and not field.value

    field.rect = rl.Rectangle(inp_x, curr_y, inp_w, inp_h)

    # 1. Label
    label_col = DRACULA_ORANGE if (is_invalid_path or is_empty_required) else DRACULA_FG
    draw_text_clean(font_bold, field.label, lbl_x, curr_y + (inp_h - label_size) / 2, label_size, label_col)

    # 2. Input Box State & Geometry
    clicked_box = False
    val_changed = False
    is_in_clip = (clip_min_y <= mouse_pos.y <= clip_max_y)

    pad_left = int(10 * scale)
    pad_right = int(10 * scale)
    text_start_x = inp_x + pad_left
    avail_w = max(20.0, inp_w - pad_left - pad_right)
    text = field.value or ""

    # Ensure cursor_pos and scroll_offset are valid
    if not hasattr(field, "cursor_pos"):
        field.cursor_pos = len(text)
    field.cursor_pos = max(0, min(len(text), field.cursor_pos))

    if not hasattr(field, "scroll_offset"):
        field.scroll_offset = 0
    field.scroll_offset = max(0, min(len(text), field.scroll_offset))

    # Adjust horizontal scrolling to keep cursor in view
    if field.cursor_pos < field.scroll_offset:
        field.scroll_offset = field.cursor_pos

    while field.scroll_offset < field.cursor_pos:
        sub = text[field.scroll_offset : field.cursor_pos]
        if measure_text_clean(font_regular, sub, input_size) > avail_w - int(14 * scale):
            field.scroll_offset += 1
        else:
            break

    while field.scroll_offset > 0:
        sub = text[field.scroll_offset - 1 : field.cursor_pos]
        if measure_text_clean(font_regular, sub, input_size) <= avail_w - int(14 * scale):
            field.scroll_offset -= 1
        else:
            break

    # Determine visible slice of text that fits within avail_w
    sub_text = text[field.scroll_offset:]
    vis_len = len(sub_text)
    vis_cursor = field.cursor_pos - field.scroll_offset

    while vis_len > vis_cursor and measure_text_clean(font_regular, sub_text[:vis_len], input_size) > avail_w:
        vis_len -= 1
    vis_text = sub_text[:vis_len]

    # Mouse Click Handling inside input box
    if is_mouse_down and is_in_clip and rl.check_collision_point_rec(mouse_pos, field.rect):
        clicked_box = True
        if field.is_path and (is_invalid_path or not field.value):
            picked = open_file_dialog(f"Path not correct. Select {field.label}")
            if picked:
                field.value = picked
                field.cursor_pos = len(picked)
                field.scroll_offset = 0
                val_changed = True
        else:
            # Place cursor at clicked character location
            click_rel_x = mouse_pos.x - text_start_x
            if click_rel_x <= 0:
                field.cursor_pos = field.scroll_offset
            else:
                best_k = len(vis_text)
                min_dist = float('inf')
                for k in range(len(vis_text) + 1):
                    prefix_w = measure_text_clean(font_regular, vis_text[:k], input_size)
                    dist = abs(prefix_w - click_rel_x)
                    if dist < min_dist:
                        min_dist = dist
                        best_k = k
                field.cursor_pos = min(len(text), field.scroll_offset + best_k)

    box_bg = DRACULA_CURRENT_LINE if is_focused else DRACULA_BG
    if is_invalid_path or is_empty_required:
        border_color = DRACULA_RED
    elif is_focused:
        border_color = DRACULA_CYAN
    else:
        border_color = DRACULA_COMMENT

    rl.draw_rectangle_rounded(field.rect, 0.25, 6, box_bg)
    rl.draw_rectangle_rounded_lines(field.rect, 0.25, 6, border_color)

    text_y = curr_y + (inp_h - input_size) / 2
    draw_text_clean(font_regular, vis_text, text_start_x, text_y, input_size, DRACULA_FG)

    # Blinking cursor with precise positioning at cursor_pos
    if is_focused and (int(cursor_timer * 2.5) % 2 == 0):
        c_sub = vis_text[:max(0, min(len(vis_text), field.cursor_pos - field.scroll_offset))]
        tw = measure_text_clean(font_regular, c_sub, input_size)
        cursor_x = text_start_x + tw
        cursor_top = curr_y + int(6 * scale_y)
        cursor_bot = curr_y + inp_h - int(6 * scale_y)
        rl.draw_line_ex(
            rl.Vector2(cursor_x, cursor_top),
            rl.Vector2(cursor_x, cursor_bot),
            2.0,
            DRACULA_CYAN
        )

    # 3. File Browse Button for path fields
    if field.is_path:
        btn_w = int(74 * scale)
        btn_x = inp_x + inp_w + int(10 * scale)
        field.btn_rect = rl.Rectangle(btn_x, curr_y, btn_w, inp_h)

        btn_hover = is_in_clip and rl.check_collision_point_rec(mouse_pos, field.btn_rect)
        btn_bg = DRACULA_PURPLE if btn_hover else (DRACULA_RED if (is_invalid_path or is_empty_required) else DRACULA_CURRENT_LINE)
        btn_fg = DRACULA_BG if btn_hover else DRACULA_FG

        rl.draw_rectangle_rounded(field.btn_rect, 0.25, 6, btn_bg)
        rl.draw_rectangle_rounded_lines(field.btn_rect, 0.25, 6, DRACULA_COMMENT)

        browse_label = "Browse" if not (is_invalid_path or is_empty_required) else "Fix Path"
        draw_text_clean(font_bold, browse_label, btn_x + int(10 * scale), text_y, max(12, int(14 * scale)), btn_fg)

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
    missing_msg: str = "⚠️ Missing\nClick to Browse",
    img_scale: float = 1.0
) -> bool:
    """
    Renders an image preview card (e.g. Passport Photo or Signature).
    Supports dynamic proportional scaling via img_scale.
    Returns True if user clicked the card to browse a new file.
    """
    has_tex = (texture is not None and texture.id > 0)
    border_color = DRACULA_COMMENT if has_tex else DRACULA_RED

    rl.draw_rectangle(int(rect.x), int(rect.y), int(rect.width), int(rect.height), DRACULA_BG)
    rl.draw_rectangle_lines(int(rect.x), int(rect.y), int(rect.width), int(rect.height), border_color)

    if has_tex:
        src_rect = rl.Rectangle(0, 0, texture.width, texture.height)
        # Keep aspect ratio and center inside card, proportionally scaled
        max_inner_w = rect.width - 6
        max_inner_h = rect.height - 6
        base_s = min(max_inner_w / texture.width, max_inner_h / texture.height)
        eff_s = base_s * max(0.4, min(1.8, img_scale))
        dw = texture.width * eff_s
        dh = texture.height * eff_s
        dx = rect.x + (rect.width - dw) / 2
        dy = rect.y + (rect.height - dh) / 2
        dst_rect = rl.Rectangle(dx, dy, dw, dh)
        rl.draw_texture_pro(texture, src_rect, dst_rect, rl.Vector2(0, 0), 0.0, rl.WHITE)
    else:
        draw_text_clean(font_regular, missing_msg, rect.x + int(14 * scale), rect.y + rect.height / 2 - int(14 * scale_y), int(14 * scale), DRACULA_RED)

    # Subtitle under card (+2 pt)
    draw_text_clean(font_bold, title, rect.x + int(12 * scale), rect.y + rect.height + int(6 * scale_y), int(15 * scale), DRACULA_FG)

    clicked = is_mouse_down and rl.check_collision_point_rec(mouse_pos, rect)
    return clicked
