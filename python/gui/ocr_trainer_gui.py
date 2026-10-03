"""
GoaOnAuto OCR Trainer & Field Ground-Truth Verification GUI.
Single Responsibility: Provides an interactive Raylib desktop interface to:
1. Preview scanned document images/PDFs with smooth zoom & pan.
2. Review and rate OCR recognition quality (1-5 Stars).
3. Verify and correct extracted demographic fields (Name, DOB, Aadhaar, Address, Cert No, Years).
4. Teach custom OCR spell-correction word pairs.
5. Emits JSON_RESULT on stdout for dataset persistence and retraining.
"""
from __future__ import annotations
import sys
import os
import argparse
import json
import tempfile
import time
from datetime import datetime
import pyray as rl

# Ensure project root in sys.path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

SUPPORTED_CATEGORIES = [
    ("aadhaar", "Aadhaar Card"),
    ("pan", "PAN Card"),
    ("voter_id", "Voter ID Card"),
    ("residence_cert", "Residence Certificate"),
    ("caste_cert", "Caste Certificate"),
    ("birth_cert", "Birth Certificate"),
    ("marriage_cert", "Marriage Certificate"),
    ("bonafide_cert", "Bonafide Certificate"),
    ("marksheet", "Marksheet / Academic"),
    ("electricity_bill", "Electricity Bill"),
    ("house_tax", "House Tax Receipt"),
    ("ration_card", "Ration Card"),
    ("pcc", "Police Clearance (PCC)"),
    ("passport", "Passport"),
    ("passport_photo", "Passport Size Photo"),
    ("signature", "Scanned Signature"),
    ("driving_license", "Driving License"),
    ("obc_cert", "OBC Certificate"),
    ("samaj_cert", "Samaj Certificate"),
    ("document", "Other / General Document")
]

RATING_LABELS = {
    1: "1/5 - Poor / Unreadable Scan",
    2: "2/5 - Fair / Multiple Errors",
    3: "3/5 - Average / Some Fields Missing",
    4: "4/5 - Good / Minor Typos",
    5: "5/5 - Excellent / Highly Accurate"
}

# Dracula Palette
DRACULA_BG = rl.Color(40, 42, 54, 255)         # #282a36
DRACULA_CURRENT = rl.Color(68, 71, 90, 255)    # #44475a
DRACULA_INPUT_BG = rl.Color(33, 34, 44, 255)   # #21222c
DRACULA_BORDER = rl.Color(98, 114, 164, 255)   # #6272a4
DRACULA_FG = rl.Color(248, 248, 242, 255)      # #f8f8f2
DRACULA_MUTED = rl.Color(140, 153, 190, 255)
DRACULA_CYAN = rl.Color(139, 233, 253, 255)    # #8be9fd
DRACULA_GREEN = rl.Color(80, 250, 123, 255)    # #50fa7b
DRACULA_ORANGE = rl.Color(255, 184, 108, 255)  # #ffb86c
DRACULA_PINK = rl.Color(255, 121, 198, 255)    # #ff79c6
DRACULA_PURPLE = rl.Color(189, 147, 249, 255)  # #bd93f9
DRACULA_RED = rl.Color(255, 85, 85, 255)       # #ff5555
DRACULA_YELLOW = rl.Color(241, 250, 140, 255)  # #f1fa8c


class KeyRepeatTracker:
    """Handles smooth key press and hold-to-repeat timing for text editing."""
    def __init__(self, initial_delay: float = 0.38, repeat_rate: float = 0.035):
        self.initial_delay = initial_delay
        self.repeat_rate = repeat_rate
        self.timer = 0.0

    def update(self, is_pressed: bool, is_down: bool, dt: float) -> bool:
        if is_pressed:
            self.timer = 0.0
            return True
        if is_down:
            self.timer += dt
            if self.timer >= self.initial_delay:
                self.timer -= self.repeat_rate
                return True
        else:
            self.timer = 0.0
        return False


def find_prev_word_boundary(text: str, pos: int) -> int:
    if pos <= 0:
        return 0
    i = pos - 1
    while i > 0 and text[i].isspace():
        i -= 1
    while i > 0 and not text[i - 1].isspace():
        i -= 1
    return i


def find_next_word_boundary(text: str, pos: int) -> int:
    length = len(text)
    if pos >= length:
        return length
    i = pos
    while i < length and not text[i].isspace():
        i += 1
    while i < length and text[i].isspace():
        i += 1
    return i


def render_pdf_first_page_to_png(pdf_path: str) -> str:
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(pdf_path)
        page = pdf[0]
        image = page.render(scale=2.2).to_pil()
        temp_dir = tempfile.gettempdir()
        file_hash = abs(hash(pdf_path)) % 10000000
        temp_png = os.path.join(temp_dir, f"goa_ocr_train_{file_hash}.png")
        image.save(temp_png)
        return temp_png
    except Exception as e:
        print(f"PDF Preview render error: {e}", file=sys.stderr)
        return ""


def draw_text_clean(font: rl.Font | None, text: str, x: float, y: float, size: float, color: rl.Color) -> None:
    try:
        raw_bytes = text.encode('utf-8', 'ignore')
        if font and hasattr(font, 'baseSize') and font.baseSize > 0:
            rl.draw_text_ex(font, raw_bytes, rl.Vector2(float(x), float(y)), float(size), 1.0, color)
        else:
            rl.draw_text(raw_bytes, int(x), int(y), int(size), color)
    except Exception:
        pass


def measure_text_clean(font: rl.Font | None, text: str, size: float) -> float:
    try:
        raw_bytes = text.encode('utf-8', 'ignore')
        if font and hasattr(font, 'baseSize') and font.baseSize > 0:
            return float(rl.measure_text_ex(font, raw_bytes, float(size), 1.0).x)
        else:
            return float(rl.measure_text(raw_bytes, int(size)))
    except Exception:
        return float(len(text) * size * 0.6)


class TrainerField:
    def __init__(self, key: str, label: str, val: str = ""):
        self.key = key
        self.label = label
        self.value = str(val or "")
        self.cursor_pos = len(self.value)
        self.scroll_offset = 0
        self.rect = rl.Rectangle(0, 0, 0, 0)


def run_ocr_trainer(
    file_path: str,
    doc_type: str,
    doc_type_name: str,
    confidence: float,
    extracted_fields: dict,
    raw_ocr_lines: list[str]
) -> dict:
    if not os.path.exists(file_path):
        return {"action": "error", "message": f"File not found: {file_path}"}

    # Initialize Pyray Window
    rl.set_config_flags(rl.FLAG_WINDOW_RESIZABLE | rl.FLAG_MSAA_4X_HINT)
    rl.init_window(1440, 880, "GoaOnAuto - OCR Quality Trainer & Field Evaluator".encode('utf-8'))
    rl.set_target_fps(60)

    # Maximize or center
    try:
        mon = rl.get_current_monitor()
        mon_w, mon_h = rl.get_monitor_width(mon), rl.get_monitor_height(mon)
        if mon_w > 1200 and mon_h > 800:
            target_w = min(1500, mon_w - 60)
            target_h = min(920, mon_h - 80)
            rl.set_window_size(target_w, target_h)
            rl.set_window_position((mon_w - target_w) // 2, max(20, (mon_h - target_h) // 2 - 20))
    except Exception:
        pass

    # Load custom font
    font = None
    font_candidates = [
        os.path.join(_PROJECT_ROOT, "assets", "fonts", "JetBrainsMono-Regular.ttf"),
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf"
    ]
    for fp in font_candidates:
        if os.path.exists(fp):
            try:
                font = rl.load_font_ex(fp.encode('utf-8'), 44, None, 0)
                if font and font.baseSize > 0:
                    rl.set_texture_filter(font.texture, rl.TEXTURE_FILTER_BILINEAR)
                    break
            except Exception:
                font = None

    # Load preview texture
    preview_img_path = file_path
    if file_path.lower().endswith(".pdf"):
        rendered_png = render_pdf_first_page_to_png(file_path)
        if rendered_png and os.path.exists(rendered_png):
            preview_img_path = rendered_png

    texture: rl.Texture | None = None
    if os.path.exists(preview_img_path):
        try:
            texture = rl.load_texture(preview_img_path.encode('utf-8'))
            if texture and texture.id > 0:
                rl.set_texture_filter(texture, rl.TEXTURE_FILTER_BILINEAR)
        except Exception as e:
            print(f"Texture error: {e}", file=sys.stderr)

    # State variables
    current_doc_type = doc_type
    current_doc_name = doc_type_name
    rating = 5  # 1 to 5 stars default
    hovered_star = 0
    show_cat_modal = False
    show_ocr_raw_modal = False

    # Review Fields
    fields: list[TrainerField] = [
        TrainerField("name", "Applicant Name", extracted_fields.get("name", "")),
        TrainerField("dob", "Date of Birth (DD/MM/YYYY)", extracted_fields.get("dob", "")),
        TrainerField("age", "Age (Years)", extracted_fields.get("age", "")),
        TrainerField("aadhaar", "Aadhaar Card No (12 Digits)", extracted_fields.get("aadhaar", "")),
        TrainerField("address", "Residential Address", extracted_fields.get("address", "")),
        TrainerField("prev_cert_no", "Prev Cert No / File No", extracted_fields.get("prev_cert_no", "")),
        TrainerField("years_in_goa", "Years in Goa / Residing Since", str(extracted_fields.get("years_in_goa", ""))),
    ]
    active_field_idx = 0

    # Learned Spell Replacement inputs
    misread_field = TrainerField("misread", "Misread Word (OCR)", "")
    correction_field = TrainerField("correction", "Corrected Word (Teach)", "")
    active_spell_idx = -1  # 0 for misread, 1 for correction, -1 for none

    # Pan & Zoom state for image preview
    preview_zoom = 1.0
    preview_offset_x = 0.0
    preview_offset_y = 0.0
    is_dragging_image = False
    drag_start_mouse = rl.Vector2(0, 0)
    drag_start_offset = rl.Vector2(0, 0)

    # Repeat Key Trackers
    repeat_backspace = KeyRepeatTracker(0.38, 0.035)
    repeat_delete = KeyRepeatTracker(0.38, 0.035)
    repeat_left = KeyRepeatTracker(0.38, 0.030)
    repeat_right = KeyRepeatTracker(0.38, 0.030)
    cursor_timer = 0.0

    right_scroll_y = 0.0
    target_right_scroll = 0.0

    action_result: dict | None = None

    while not rl.window_should_close() and action_result is None:
        dt = rl.get_frame_time()
        cursor_timer += dt
        w = rl.get_screen_width()
        h = rl.get_screen_height()
        mouse_pos = rl.get_mouse_position()
        is_mouse_down = rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT)
        ctrl_down = rl.is_key_down(rl.KEY_LEFT_CONTROL) or rl.is_key_down(rl.KEY_RIGHT_CONTROL)

        # Responsive scaling
        scale = max(0.9, min(1.3, w / 1440.0))
        scale_y = max(0.9, min(1.25, h / 880.0))

        header_h = int(58 * scale_y)
        footer_h = int(58 * scale_y)
        content_y = header_h
        content_h = h - header_h - footer_h

        left_w = int(w * 0.48)
        right_x = left_w + 8
        right_w = w - right_x - 16

        # Top-level shortkeys
        if rl.is_key_pressed(rl.KEY_ESCAPE):
            if show_cat_modal:
                show_cat_modal = False
            elif show_ocr_raw_modal:
                show_ocr_raw_modal = False
            else:
                action_result = {"action": "skipped", "filePath": file_path}
                break

        # Submit Shortcut
        if not show_cat_modal and not show_ocr_raw_modal:
            if ctrl_down and (rl.is_key_pressed(rl.KEY_ENTER) or rl.is_key_pressed(rl.KEY_KP_ENTER)):
                action_result = {
                    "action": "confirmed",
                    "rating": rating,
                    "docType": current_doc_type,
                    "docTypeName": current_doc_name,
                    "fields": {f.key: f.value for f in fields},
                    "spellCorrection": {
                        "original": misread_field.value.strip(),
                        "corrected": correction_field.value.strip()
                    } if misread_field.value.strip() and correction_field.value.strip() else None
                }
                break

        # -------------------------------------------------------------
        # Left Panel (Image Preview with Pan & Zoom)
        # -------------------------------------------------------------
        preview_rect = rl.Rectangle(12, content_y + 8, left_w - 16, content_h - 16)
        is_hover_preview = rl.check_collision_point_rec(mouse_pos, preview_rect)

        # Mouse Wheel Zoom
        if is_hover_preview:
            wheel = rl.get_mouse_wheel_move()
            if wheel != 0:
                old_zoom = preview_zoom
                preview_zoom = max(0.3, min(5.0, preview_zoom + wheel * 0.15))
                # Zoom centered around cursor
                preview_offset_x -= (mouse_pos.x - preview_rect.x) * (preview_zoom - old_zoom) / preview_zoom
                preview_offset_y -= (mouse_pos.y - preview_rect.y) * (preview_zoom - old_zoom) / preview_zoom

        # Mouse Drag Pan
        if is_hover_preview and rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT):
            is_dragging_image = True
            drag_start_mouse = mouse_pos
            drag_start_offset = rl.Vector2(preview_offset_x, preview_offset_y)

        if is_dragging_image:
            if rl.is_mouse_button_down(rl.MOUSE_BUTTON_LEFT):
                preview_offset_x = drag_start_offset.x + (mouse_pos.x - drag_start_mouse.x)
                preview_offset_y = drag_start_offset.y + (mouse_pos.y - drag_start_mouse.y)
            else:
                is_dragging_image = False

        # -------------------------------------------------------------
        # Keyboard Navigation for Fields & Text Input
        # -------------------------------------------------------------
        # Active target field (either review fields or spell correction fields)
        target_f: TrainerField | None = None
        if active_spell_idx == 0:
            target_f = misread_field
        elif active_spell_idx == 1:
            target_f = correction_field
        elif 0 <= active_field_idx < len(fields):
            target_f = fields[active_field_idx]

        if not show_cat_modal and not show_ocr_raw_modal:
            # Tab / Shift+Tab cycling
            if rl.is_key_pressed(rl.KEY_TAB):
                if active_spell_idx >= 0:
                    if rl.is_key_down(rl.KEY_LEFT_SHIFT) or rl.is_key_down(rl.KEY_RIGHT_SHIFT):
                        active_spell_idx -= 1
                        if active_spell_idx < 0:
                            active_field_idx = len(fields) - 1
                    else:
                        active_spell_idx += 1
                        if active_spell_idx > 1:
                            active_spell_idx = -1
                            active_field_idx = 0
                else:
                    if rl.is_key_down(rl.KEY_LEFT_SHIFT) or rl.is_key_down(rl.KEY_RIGHT_SHIFT):
                        active_field_idx -= 1
                        if active_field_idx < 0:
                            active_spell_idx = 1
                    else:
                        active_field_idx += 1
                        if active_field_idx >= len(fields):
                            active_spell_idx = 0
                cursor_timer = 0.0

            # Target field text editing
            if target_f:
                target_f.cursor_pos = max(0, min(len(target_f.value), target_f.cursor_pos))

                # Left Arrow
                if repeat_left.update(rl.is_key_pressed(rl.KEY_LEFT), rl.is_key_down(rl.KEY_LEFT), dt):
                    if ctrl_down:
                        target_f.cursor_pos = find_prev_word_boundary(target_f.value, target_f.cursor_pos)
                    else:
                        target_f.cursor_pos = max(0, target_f.cursor_pos - 1)
                    cursor_timer = 0.0

                # Right Arrow
                if repeat_right.update(rl.is_key_pressed(rl.KEY_RIGHT), rl.is_key_down(rl.KEY_RIGHT), dt):
                    if ctrl_down:
                        target_f.cursor_pos = find_next_word_boundary(target_f.value, target_f.cursor_pos)
                    else:
                        target_f.cursor_pos = min(len(target_f.value), target_f.cursor_pos + 1)
                    cursor_timer = 0.0

                # Home / End
                if rl.is_key_pressed(rl.KEY_HOME):
                    target_f.cursor_pos = 0
                    cursor_timer = 0.0
                if rl.is_key_pressed(rl.KEY_END):
                    target_f.cursor_pos = len(target_f.value)
                    cursor_timer = 0.0

                # Backspace
                if repeat_backspace.update(rl.is_key_pressed(rl.KEY_BACKSPACE), rl.is_key_down(rl.KEY_BACKSPACE), dt):
                    if target_f.cursor_pos > 0:
                        pos = target_f.cursor_pos
                        if ctrl_down:
                            new_pos = find_prev_word_boundary(target_f.value, pos)
                            target_f.value = target_f.value[:new_pos] + target_f.value[pos:]
                            target_f.cursor_pos = new_pos
                        else:
                            target_f.value = target_f.value[:pos - 1] + target_f.value[pos:]
                            target_f.cursor_pos = pos - 1
                        cursor_timer = 0.0

                # Delete
                if repeat_delete.update(rl.is_key_pressed(rl.KEY_DELETE), rl.is_key_down(rl.KEY_DELETE), dt):
                    if target_f.cursor_pos < len(target_f.value):
                        pos = target_f.cursor_pos
                        if ctrl_down:
                            next_pos = find_next_word_boundary(target_f.value, pos)
                            target_f.value = target_f.value[:pos] + target_f.value[next_pos:]
                        else:
                            target_f.value = target_f.value[:pos] + target_f.value[pos + 1:]
                        cursor_timer = 0.0

                # Paste (Ctrl+V)
                if ctrl_down and rl.is_key_pressed(rl.KEY_V):
                    try:
                        import tkinter as tk
                        root = tk.Tk()
                        root.withdraw()
                        clipboard = root.clipboard_get()
                        root.destroy()
                        if clipboard:
                            clean_clip = clipboard.replace("\n", " ").replace("\r", "")
                            pos = target_f.cursor_pos
                            target_f.value = target_f.value[:pos] + clean_clip + target_f.value[pos:]
                            target_f.cursor_pos = pos + len(clean_clip)
                            cursor_timer = 0.0
                    except Exception:
                        pass

                # Printable Character Typing
                char_code = rl.get_char_pressed()
                while char_code > 0:
                    if 32 <= char_code <= 126:
                        pos = target_f.cursor_pos
                        ch = chr(char_code)
                        target_f.value = target_f.value[:pos] + ch + target_f.value[pos:]
                        target_f.cursor_pos = pos + 1
                        cursor_timer = 0.0
                    char_code = rl.get_char_pressed()

        # -------------------------------------------------------------
        # DRAWING
        # -------------------------------------------------------------
        rl.begin_drawing()
        rl.clear_background(DRACULA_BG)

        # 1. Header Bar
        rl.draw_rectangle(0, 0, w, header_h, DRACULA_CURRENT)
        rl.draw_line(0, header_h, w, header_h, DRACULA_BORDER)

        draw_text_clean(font, "🔍 OCR Quality Trainer & Field Evaluator", 20, 16 * scale_y, int(20 * scale), DRACULA_CYAN)

        # Document Badge
        base_name = os.path.basename(file_path)
        badge_text = f"📄 {base_name} ({current_doc_name})"
        badge_w = measure_text_clean(font, badge_text, int(15 * scale)) + 24
        badge_rect = rl.Rectangle(w - badge_w - 220, int(12 * scale_y), badge_w, int(32 * scale_y))
        rl.draw_rectangle_rounded(badge_rect, 0.3, 6, DRACULA_INPUT_BG)
        rl.draw_rectangle_rounded_lines(badge_rect, 0.3, 6, DRACULA_PURPLE)
        draw_text_clean(font, badge_text, badge_rect.x + 12, badge_rect.y + 7, int(14 * scale), DRACULA_FG)

        # Category Change Button
        cat_btn_rect = rl.Rectangle(w - 200, int(12 * scale_y), 180, int(32 * scale_y))
        cat_hover = rl.check_collision_point_rec(mouse_pos, cat_btn_rect)
        rl.draw_rectangle_rounded(cat_btn_rect, 0.3, 6, DRACULA_PURPLE if cat_hover else DRACULA_CURRENT)
        draw_text_clean(font, "Change Category ▾", cat_btn_rect.x + 16, cat_btn_rect.y + 7, int(14 * scale), DRACULA_BG if cat_hover else DRACULA_FG)
        if is_mouse_down and cat_hover:
            show_cat_modal = not show_cat_modal

        # -------------------------------------------------------------
        # 2. Left Preview Panel (Image with Scissor Clipping)
        # -------------------------------------------------------------
        rl.draw_rectangle_rounded(preview_rect, 0.02, 6, DRACULA_INPUT_BG)
        rl.draw_rectangle_rounded_lines(preview_rect, 0.02, 6, DRACULA_BORDER)

        rl.begin_scissor_mode(int(preview_rect.x), int(preview_rect.y), int(preview_rect.width), int(preview_rect.height))
        if texture and texture.id > 0:
            fit_scale = min(preview_rect.width / texture.width, preview_rect.height / texture.height) * 0.95
            total_scale = fit_scale * preview_zoom
            disp_w = texture.width * total_scale
            disp_h = texture.height * total_scale

            base_x = preview_rect.x + (preview_rect.width - disp_w) / 2 + preview_offset_x
            base_y = preview_rect.y + (preview_rect.height - disp_h) / 2 + preview_offset_y

            src_r = rl.Rectangle(0, 0, texture.width, texture.height)
            dst_r = rl.Rectangle(base_x, base_y, disp_w, disp_h)
            rl.draw_texture_pro(texture, src_r, dst_r, rl.Vector2(0, 0), 0.0, rl.WHITE)
        else:
            draw_text_clean(font, "⚠️ No Image Preview Available", preview_rect.x + 40, preview_rect.y + preview_rect.height / 2, int(16 * scale), DRACULA_RED)
        rl.end_scissor_mode()

        # Preview Overlay Info & Reset Button
        reset_btn = rl.Rectangle(preview_rect.x + 12, preview_rect.y + 12, 110, 28)
        reset_hover = rl.check_collision_point_rec(mouse_pos, reset_btn)
        rl.draw_rectangle_rounded(reset_btn, 0.3, 4, DRACULA_CURRENT if reset_hover else rl.color_alpha(DRACULA_INPUT_BG, 0.85))
        draw_text_clean(font, "Reset Zoom", reset_btn.x + 12, reset_btn.y + 6, 12, DRACULA_CYAN)
        if is_mouse_down and reset_hover:
            preview_zoom = 1.0
            preview_offset_x = 0.0
            preview_offset_y = 0.0

        # Zoom level pill
        draw_text_clean(font, f"Zoom: {int(preview_zoom * 100)}%", preview_rect.x + 130, preview_rect.y + 18, 12, DRACULA_MUTED)

        # -------------------------------------------------------------
        # 3. Right Review & Evaluation Panel
        # -------------------------------------------------------------
        form_box = rl.Rectangle(right_x, content_y + 8, right_w, content_h - 16)
        rl.draw_rectangle_rounded(form_box, 0.02, 6, DRACULA_CURRENT)
        rl.draw_rectangle_rounded_lines(form_box, 0.02, 6, DRACULA_BORDER)

        curr_y = form_box.y + 16

        # --- A. Star Rating Section ---
        draw_text_clean(font, "⭐ OCR Quality Rating:", form_box.x + 20, curr_y, int(15 * scale), DRACULA_YELLOW)
        star_start_x = form_box.x + 220
        hovered_star = 0

        for star_idx in range(1, 6):
            star_x = star_start_x + (star_idx - 1) * 34
            star_rect = rl.Rectangle(star_x, curr_y - 4, 30, 30)
            if rl.check_collision_point_rec(mouse_pos, star_rect):
                hovered_star = star_idx
                if is_mouse_down:
                    rating = star_idx

            is_filled = star_idx <= (hovered_star if hovered_star > 0 else rating)
            star_col = DRACULA_YELLOW if is_filled else DRACULA_BORDER
            draw_text_clean(font, "★", star_x, curr_y - 6, int(26 * scale), star_col)

        # Rating meaning label
        curr_rating_display = hovered_star if hovered_star > 0 else rating
        rating_desc = RATING_LABELS.get(curr_rating_display, "")
        draw_text_clean(font, rating_desc, star_start_x + 180, curr_y + 2, int(13 * scale), DRACULA_FG)

        curr_y += 38
        rl.draw_line(int(form_box.x + 20), int(curr_y), int(form_box.x + form_box.width - 20), int(curr_y), DRACULA_BORDER)
        curr_y += 14

        # --- B. Demographic Extraction Review Fields ---
        draw_text_clean(font, "📝 Extracted Demographic Fields (Click or Tab to Edit):", form_box.x + 20, curr_y, int(14 * scale), DRACULA_CYAN)
        curr_y += 24

        inp_h = 36
        lbl_w = int(form_box.width * 0.35)
        field_inp_w = int(form_box.width - lbl_w - 55)

        for i, fld in enumerate(fields):
            is_active = (active_field_idx == i and active_spell_idx == -1)
            lbl_x = form_box.x + 20
            inp_x = lbl_x + lbl_w + 10
            fld.rect = rl.Rectangle(inp_x, curr_y, field_inp_w, inp_h)

            # Draw Label
            draw_text_clean(font, fld.label, lbl_x, curr_y + 8, int(13 * scale), DRACULA_FG)

            # Click to focus & set cursor
            if is_mouse_down and rl.check_collision_point_rec(mouse_pos, fld.rect):
                active_field_idx = i
                active_spell_idx = -1
                click_rel = mouse_pos.x - (inp_x + 10)
                if click_rel <= 0:
                    fld.cursor_pos = fld.scroll_offset
                else:
                    best_k = len(fld.value)
                    min_dist = float('inf')
                    for k in range(len(fld.value) + 1):
                        dist = abs(measure_text_clean(font, fld.value[:k], int(14 * scale)) - click_rel)
                        if dist < min_dist:
                            min_dist = dist
                            best_k = k
                    fld.cursor_pos = best_k
                cursor_timer = 0.0

            # Draw Box
            box_bg = DRACULA_INPUT_BG if is_active else DRACULA_BG
            border_col = DRACULA_CYAN if is_active else DRACULA_BORDER
            rl.draw_rectangle_rounded(fld.rect, 0.25, 4, box_bg)
            rl.draw_rectangle_rounded_lines(fld.rect, 0.25, 4, border_col)

            # Draw Text
            draw_text_clean(font, fld.value, inp_x + 10, curr_y + 9, int(14 * scale), DRACULA_FG)

            # Draw Blinking Cursor
            if is_active and (int(cursor_timer * 2.5) % 2 == 0):
                c_w = measure_text_clean(font, fld.value[:fld.cursor_pos], int(14 * scale))
                cur_x = inp_x + 10 + c_w
                rl.draw_line_ex(
                    rl.Vector2(cur_x, curr_y + 6),
                    rl.Vector2(cur_x, curr_y + inp_h - 6),
                    2.0,
                    DRACULA_CYAN
                )

            curr_y += inp_h + 10

        curr_y += 6
        rl.draw_line(int(form_box.x + 20), int(curr_y), int(form_box.x + form_box.width - 20), int(curr_y), DRACULA_BORDER)
        curr_y += 14

        # --- C. Teach OCR Spell-Correction Pair ---
        draw_text_clean(font, "🔤 Teach OCR Spell-Correction (Auto-persists to dictionary):", form_box.x + 20, curr_y, int(14 * scale), DRACULA_PINK)
        curr_y += 24

        spell_box_w = (form_box.width - 70) / 2
        misread_field.rect = rl.Rectangle(form_box.x + 20, curr_y, spell_box_w, 34)
        correction_field.rect = rl.Rectangle(form_box.x + 20 + spell_box_w + 30, curr_y, spell_box_w, 34)

        # Misread Box
        is_misread_active = (active_spell_idx == 0)
        if is_mouse_down and rl.check_collision_point_rec(mouse_pos, misread_field.rect):
            active_spell_idx = 0
            cursor_timer = 0.0

        rl.draw_rectangle_rounded(misread_field.rect, 0.25, 4, DRACULA_INPUT_BG if is_misread_active else DRACULA_BG)
        rl.draw_rectangle_rounded_lines(misread_field.rect, 0.25, 4, DRACULA_PINK if is_misread_active else DRACULA_BORDER)
        disp_mis = misread_field.value if misread_field.value else "e.g. Mamltdar"
        draw_text_clean(font, disp_mis, misread_field.rect.x + 10, misread_field.rect.y + 8, int(13 * scale), DRACULA_FG if misread_field.value else DRACULA_MUTED)

        if is_misread_active and (int(cursor_timer * 2.5) % 2 == 0):
            c_w = measure_text_clean(font, misread_field.value[:misread_field.cursor_pos], int(13 * scale))
            rl.draw_line_ex(
                rl.Vector2(misread_field.rect.x + 10 + c_w, misread_field.rect.y + 6),
                rl.Vector2(misread_field.rect.x + 10 + c_w, misread_field.rect.y + 28),
                2.0,
                DRACULA_PINK
            )

        # Arrow icon
        draw_text_clean(font, "➔", form_box.x + 20 + spell_box_w + 8, curr_y + 8, int(16 * scale), DRACULA_MUTED)

        # Correction Box
        is_corr_active = (active_spell_idx == 1)
        if is_mouse_down and rl.check_collision_point_rec(mouse_pos, correction_field.rect):
            active_spell_idx = 1
            cursor_timer = 0.0

        rl.draw_rectangle_rounded(correction_field.rect, 0.25, 4, DRACULA_INPUT_BG if is_corr_active else DRACULA_BG)
        rl.draw_rectangle_rounded_lines(correction_field.rect, 0.25, 4, DRACULA_GREEN if is_corr_active else DRACULA_BORDER)
        disp_cor = correction_field.value if correction_field.value else "e.g. Mamlatdar"
        draw_text_clean(font, disp_cor, correction_field.rect.x + 10, correction_field.rect.y + 8, int(13 * scale), DRACULA_FG if correction_field.value else DRACULA_MUTED)

        if is_corr_active and (int(cursor_timer * 2.5) % 2 == 0):
            c_w = measure_text_clean(font, correction_field.value[:correction_field.cursor_pos], int(13 * scale))
            rl.draw_line_ex(
                rl.Vector2(correction_field.rect.x + 10 + c_w, correction_field.rect.y + 6),
                rl.Vector2(correction_field.rect.x + 10 + c_w, correction_field.rect.y + 28),
                2.0,
                DRACULA_GREEN
            )

        curr_y += 48

        # --- D. Raw OCR Lines Button ---
        raw_btn_rect = rl.Rectangle(form_box.x + 20, curr_y, 200, 30)
        raw_hover = rl.check_collision_point_rec(mouse_pos, raw_btn_rect)
        rl.draw_rectangle_rounded(raw_btn_rect, 0.25, 4, DRACULA_INPUT_BG if raw_hover else DRACULA_BG)
        rl.draw_rectangle_rounded_lines(raw_btn_rect, 0.25, 4, DRACULA_PURPLE)
        draw_text_clean(font, f"📄 Inspect Raw OCR ({len(raw_ocr_lines)} lines)", raw_btn_rect.x + 12, raw_btn_rect.y + 6, 12, DRACULA_PURPLE)
        if is_mouse_down and raw_hover:
            show_ocr_raw_modal = True

        # -------------------------------------------------------------
        # 4. Bottom Footer Bar (Action Buttons)
        # -------------------------------------------------------------
        rl.draw_rectangle(0, h - footer_h, w, footer_h, DRACULA_CURRENT)
        rl.draw_line(0, h - footer_h, w, h - footer_h, DRACULA_BORDER)

        btn_y = h - footer_h + 12
        btn_h = int(36 * scale_y)

        # Submit & Save Button
        submit_btn = rl.Rectangle(w - 240, btn_y, 220, btn_h)
        sub_hover = rl.check_collision_point_rec(mouse_pos, submit_btn)
        rl.draw_rectangle_rounded(submit_btn, 0.3, 6, DRACULA_GREEN if sub_hover else rl.Color(60, 200, 100, 255))
        draw_text_clean(font, "★ Save & Retrain (Ctrl+Enter)", submit_btn.x + 16, submit_btn.y + 9, int(13 * scale), DRACULA_BG)

        if (is_mouse_down and sub_hover):
            action_result = {
                "action": "confirmed",
                "rating": rating,
                "docType": current_doc_type,
                "docTypeName": current_doc_name,
                "fields": {f.key: f.value for f in fields},
                "spellCorrection": {
                    "original": misread_field.value.strip(),
                    "corrected": correction_field.value.strip()
                } if misread_field.value.strip() and correction_field.value.strip() else None
            }

        # Skip Button
        skip_btn = rl.Rectangle(w - 380, btn_y, 120, btn_h)
        skip_hover = rl.check_collision_point_rec(mouse_pos, skip_btn)
        rl.draw_rectangle_rounded(skip_btn, 0.3, 6, DRACULA_INPUT_BG if skip_hover else DRACULA_BG)
        rl.draw_rectangle_rounded_lines(skip_btn, 0.3, 6, DRACULA_BORDER)
        draw_text_clean(font, "Skip (Esc)", skip_btn.x + 24, skip_btn.y + 9, int(13 * scale), DRACULA_FG)

        if (is_mouse_down and skip_hover):
            action_result = {"action": "skipped", "filePath": file_path}

        # -------------------------------------------------------------
        # 5. Modals (Category Switcher & Raw OCR Inspector)
        # -------------------------------------------------------------
        if show_cat_modal:
            # Modal Overlay
            rl.draw_rectangle(0, 0, w, h, rl.Color(0, 0, 0, 180))
            modal_w = 680
            modal_h = 480
            modal_x = (w - modal_w) // 2
            modal_y = (h - modal_h) // 2
            modal_rect = rl.Rectangle(modal_x, modal_y, modal_w, modal_h)
            rl.draw_rectangle_rounded(modal_rect, 0.04, 8, DRACULA_BG)
            rl.draw_rectangle_rounded_lines(modal_rect, 0.04, 8, DRACULA_PURPLE)

            draw_text_clean(font, "Select Document Category", modal_x + 24, modal_y + 20, 18, DRACULA_CYAN)

            grid_x = modal_x + 24
            grid_y = modal_y + 60
            btn_w = 300
            btn_item_h = 34

            for idx, (cat_id, cat_name) in enumerate(SUPPORTED_CATEGORIES):
                col = idx % 2
                row = idx // 2
                bx = grid_x + col * (btn_w + 20)
                by = grid_y + row * (btn_item_h + 6)
                brect = rl.Rectangle(bx, by, btn_w, btn_item_h)
                bhover = rl.check_collision_point_rec(mouse_pos, brect)
                is_selected = (cat_id == current_doc_type)

                bg_col = DRACULA_PURPLE if is_selected else (DRACULA_CURRENT if bhover else DRACULA_INPUT_BG)
                fg_col = DRACULA_BG if is_selected else DRACULA_FG
                rl.draw_rectangle_rounded(brect, 0.25, 4, bg_col)
                draw_text_clean(font, cat_name, bx + 12, by + 8, 13, fg_col)

                if is_mouse_down and bhover:
                    current_doc_type = cat_id
                    current_doc_name = cat_name
                    show_cat_modal = False

        elif show_ocr_raw_modal:
            rl.draw_rectangle(0, 0, w, h, rl.Color(0, 0, 0, 180))
            modal_w = 760
            modal_h = 560
            modal_x = (w - modal_w) // 2
            modal_y = (h - modal_h) // 2
            modal_rect = rl.Rectangle(modal_x, modal_y, modal_w, modal_h)
            rl.draw_rectangle_rounded(modal_rect, 0.04, 8, DRACULA_BG)
            rl.draw_rectangle_rounded_lines(modal_rect, 0.04, 8, DRACULA_CYAN)

            draw_text_clean(font, f"📄 Raw OCR Lines ({len(raw_ocr_lines)} lines)", modal_x + 24, modal_y + 20, 18, DRACULA_CYAN)
            close_btn = rl.Rectangle(modal_x + modal_w - 90, modal_y + 16, 70, 28)
            rl.draw_rectangle_rounded(close_btn, 0.3, 4, DRACULA_CURRENT)
            draw_text_clean(font, "Close", close_btn.x + 16, close_btn.y + 6, 12, DRACULA_FG)
            if is_mouse_down and rl.check_collision_point_rec(mouse_pos, close_btn):
                show_ocr_raw_modal = False

            # Draw lines
            box_y = modal_y + 60
            rl.begin_scissor_mode(int(modal_x + 20), int(box_y), int(modal_w - 40), int(modal_h - 80))
            for line_idx, line_txt in enumerate(raw_ocr_lines[:25]):
                line_y = box_y + line_idx * 20
                draw_text_clean(font, f"{line_idx + 1:2d} | {line_txt}", modal_x + 30, line_y, 12, DRACULA_FG)
            rl.end_scissor_mode()

        rl.end_drawing()

    # Unload texture and close window
    if texture and texture.id > 0:
        rl.unload_texture(texture)
    if font and hasattr(font, 'baseSize') and font.baseSize > 0:
        rl.unload_font(font)
    rl.close_window()

    return action_result or {"action": "skipped", "filePath": file_path}


def main():
    parser = argparse.ArgumentParser(description="GoaOnAuto OCR Quality Trainer GUI")
    parser.add_argument("--file", required=True, help="Path to document image or PDF")
    parser.add_argument("--type", default="document", help="Detected document category")
    parser.add_argument("--name", default="Unknown Document", help="Human-readable category name")
    parser.add_argument("--confidence", type=float, default=0.9, help="Detection confidence")
    parser.add_argument("--fields", default="{}", help="JSON string of extracted fields")
    parser.add_argument("--ocr-lines", default="[]", help="JSON string array of raw OCR lines")

    args = parser.parse_args()

    try:
        extracted = json.loads(args.fields)
    except Exception:
        extracted = {}

    try:
        raw_lines = json.loads(args.ocr_lines)
    except Exception:
        raw_lines = []

    res = run_ocr_trainer(
        file_path=args.file,
        doc_type=args.type,
        doc_type_name=args.name,
        confidence=args.confidence,
        extracted_fields=extracted,
        raw_ocr_lines=raw_lines
    )

    print(f"\nJSON_RESULT:{json.dumps(res)}")


if __name__ == "__main__":
    main()
