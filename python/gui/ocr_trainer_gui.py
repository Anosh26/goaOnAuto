"""
GoaOnAuto OCR Trainer & Field Ground-Truth Verification GUI.
Single Responsibility: Provides an interactive Raylib desktop interface to:
1. Preview scanned document images/PDFs with smooth zoom & pan in a dedicated Sub-Window.
2. Review and rate OCR recognition quality (1-5 Stars).
3. Verify and correct extracted demographic fields (Name, DOB, Aadhaar, Address, Cert No, Years).
4. Teach custom OCR spell-correction word pairs.
5. Emits JSON_RESULT on stdout for dataset persistence and retraining.
6. Window-in-Window architecture with 3 modular docked panes, proper button constraints,
   zero text overflow, and tactile pointing hand cursor feedback.
"""
from __future__ import annotations
import sys
import os
import argparse
import json
import tempfile
import time
import threading
import queue
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


def set_clipboard_text(text: str) -> bool:
    if not text:
        return False
    if sys.platform == 'win32':
        try:
            import subprocess
            p = subprocess.Popen(['clip'], stdin=subprocess.PIPE, shell=True)
            p.communicate(input=text.encode('utf-16le'))
            return True
        except Exception:
            pass
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True
    except Exception:
        pass
    return False


def draw_button(
    rect: rl.Rectangle,
    text: str,
    font: rl.Font | None,
    font_size: int = 15,
    bg_color: rl.Color = DRACULA_CURRENT,
    hover_color: rl.Color = DRACULA_PURPLE,
    text_color: rl.Color = DRACULA_FG,
    border_color: rl.Color | None = None,
    roundness: float = 0.25,
    mouse_pos: rl.Vector2 | None = None,
    is_mouse_pressed: bool = False,
    is_mouse_down: bool = False
) -> tuple[bool, bool]:
    """
    Renders a button with proper constraints, automatic text centering,
    zero overflow, tactile hover/pressed states, and pointing hand cursor.
    """
    if mouse_pos is None:
        mouse_pos = rl.get_mouse_position()

    hover = rl.check_collision_point_rec(mouse_pos, rect)
    pressed = hover and is_mouse_down
    clicked = hover and is_mouse_pressed

    # Hover / Pressed Visual State
    if pressed:
        fill_col = rl.Color(
            max(0, hover_color.r - 30),
            max(0, hover_color.g - 30),
            max(0, hover_color.b - 30),
            255
        )
    elif hover:
        fill_col = hover_color
    else:
        fill_col = bg_color

    rl.draw_rectangle_rounded(rect, roundness, 6, fill_col)

    if border_color:
        b_col = DRACULA_CYAN if hover else border_color
        rl.draw_rectangle_rounded_lines(rect, roundness, 6, b_col)

    # Constraint protection: calculate text width and center
    cur_size = font_size
    txt_w = measure_text_clean(font, text, cur_size)
    txt_h = float(cur_size)

    # Dynamically scale font size down if button constraint is too tight
    while txt_w > (rect.width - 12) and cur_size > 10:
        cur_size -= 1
        txt_w = measure_text_clean(font, text, cur_size)
        txt_h = float(cur_size)

    txt_x = rect.x + (rect.width - txt_w) / 2.0
    txt_y = rect.y + (rect.height - txt_h) / 2.0 + (1.0 if pressed else 0.0)

    # Scissor clipping guarantees zero text overflow
    rl.begin_scissor_mode(int(rect.x), int(rect.y), int(rect.width), int(rect.height))
    draw_text_clean(font, text, txt_x, txt_y, cur_size, text_color)
    rl.end_scissor_mode()

    return clicked, hover


def draw_subwindow(
    rect: rl.Rectangle,
    title: str,
    icon: str = "",
    font: rl.Font | None = None,
    scale: float = 1.0,
    titlebar_h: int = 42,
    badge_text: str = ""
) -> rl.Rectangle:
    """
    Renders a modern Window-in-Window card container with a dark slate titlebar,
    colored window dots (● ● ●), title, and an inner recessed workspace area.
    """
    # Outer drop shadow & frame
    shadow_rect = rl.Rectangle(rect.x + 2, rect.y + 2, rect.width, rect.height)
    rl.draw_rectangle_rounded(shadow_rect, 0.02, 6, rl.Color(20, 21, 30, 160))

    # Main window body
    rl.draw_rectangle_rounded(rect, 0.02, 6, DRACULA_BG)
    rl.draw_rectangle_rounded_lines(rect, 0.02, 6, DRACULA_BORDER)

    # Titlebar
    titlebar_rect = rl.Rectangle(rect.x, rect.y, rect.width, titlebar_h)
    rl.draw_rectangle_rounded(titlebar_rect, 0.02, 6, DRACULA_CURRENT)
    rl.draw_line(
        int(rect.x),
        int(rect.y + titlebar_h),
        int(rect.x + rect.width),
        int(rect.y + titlebar_h),
        DRACULA_BORDER
    )

    # Decorative Mac/Desktop Window Dots
    dot_y = rect.y + titlebar_h / 2.0
    rl.draw_circle(int(rect.x + 16), int(dot_y), 4.5, rl.Color(255, 95, 86, 255))
    rl.draw_circle(int(rect.x + 28), int(dot_y), 4.5, rl.Color(255, 189, 46, 255))
    rl.draw_circle(int(rect.x + 40), int(dot_y), 4.5, rl.Color(39, 201, 63, 255))

    # Window Title
    full_title = f"{icon}  {title}" if icon else title
    title_size = int(16 * scale)
    title_x = rect.x + 54
    title_y = rect.y + (titlebar_h - title_size) / 2.0
    draw_text_clean(font, full_title, title_x, title_y, title_size, DRACULA_CYAN)

    # Optional Pill Badge
    if badge_text:
        badge_font_size = int(13 * scale)
        badge_txt_w = measure_text_clean(font, badge_text, badge_font_size)
        badge_w = badge_txt_w + 16
        badge_h = 24
        badge_x = title_x + measure_text_clean(font, full_title, title_size) + 12
        badge_y = rect.y + (titlebar_h - badge_h) / 2.0
        badge_rect = rl.Rectangle(badge_x, badge_y, badge_w, badge_h)
        rl.draw_rectangle_rounded(badge_rect, 0.4, 4, DRACULA_PURPLE)
        draw_text_clean(font, badge_text, badge_x + 8, badge_y + (badge_h - badge_font_size) / 2.0, badge_font_size, DRACULA_BG)

    # Inner Workspace bounds
    return rl.Rectangle(
        rect.x + 2,
        rect.y + titlebar_h + 2,
        rect.width - 4,
        rect.height - titlebar_h - 4
    )


class TrainerField:
    def __init__(self, key: str, label: str, val: str = ""):
        self.key = key
        self.label = label
        self.value = str(val or "")
        self.cursor_pos = len(self.value)
        self.scroll_offset = 0
        self.rect = rl.Rectangle(0, 0, 0, 0)


def run_ocr_trainer(
    file_path: str = "",
    doc_type: str = "document",
    doc_type_name: str = "Document",
    confidence: float = 0.9,
    extracted_fields: dict | None = None,
    raw_ocr_lines: list[str] | None = None,
    session_mode: bool = False
) -> dict:
    if extracted_fields is None:
        extracted_fields = {}
    if raw_ocr_lines is None:
        raw_ocr_lines = []

    # 1. Enable Windows DPI-Awareness & Query Physical Desktop Work Area
    init_w = 1920
    init_h = 1080
    work_x = 0
    work_y = 0
    if sys.platform == 'win32':
        try:
            import ctypes
            user32 = ctypes.windll.user32
            try:
                user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # Per-Monitor V2
            except Exception:
                user32.SetProcessDPIAware()

            rect = (ctypes.c_long * 4)()
            user32.SystemParametersInfoW(0x0030, 0, rect, 0)
            work_x = rect[0]
            work_y = rect[1]
            work_w = rect[2] - rect[0]
            work_h = rect[3] - rect[1]
            if work_w > 800 and work_h > 600:
                init_w = work_w
                init_h = work_h
        except Exception:
            pass

    # Initialize Window with exact native work area dimensions so OpenGL framebuffer matches 1:1
    rl.set_config_flags(rl.FLAG_WINDOW_RESIZABLE | rl.FLAG_MSAA_4X_HINT | rl.FLAG_WINDOW_ALWAYS_RUN)
    window_title = "GoaOnAuto - OCR Quality Trainer & Field Evaluator"
    rl.init_window(init_w, init_h, window_title.encode('utf-8'))
    rl.set_window_position(work_x, work_y)
    rl.set_window_size(init_w, init_h)
    rl.set_target_fps(60)

    # Windows Foreground Activation (SW_SHOW)
    if sys.platform == 'win32':
        try:
            import ctypes
            user32 = ctypes.windll.user32
            target_hwnd = user32.FindWindowW(None, window_title)
            if target_hwnd:
                SW_SHOW = 5
                user32.ShowWindow(target_hwnd, SW_SHOW)
                user32.SetForegroundWindow(target_hwnd)
                user32.SetActiveWindow(target_hwnd)
                user32.BringWindowToTop(target_hwnd)
        except Exception:
            pass

    # 2. Load custom font (48pt base atlas for crisp rendering of larger fonts)
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
                font = rl.load_font_ex(fp.encode('utf-8'), 48, None, 0)
                if font and font.baseSize > 0:
                    rl.set_texture_filter(font.texture, rl.TEXTURE_FILTER_BILINEAR)
                    break
            except Exception:
                font = None

    # 3. Background Thread for Stdin (Non-blocking IPC)
    cmd_queue: queue.Queue[str] = queue.Queue()

    def stdin_reader():
        for line in sys.stdin:
            line_str = line.strip()
            if line_str:
                cmd_queue.put(line_str)

    reader_thread = threading.Thread(target=stdin_reader, daemon=True)
    reader_thread.start()

    # 4. State variables
    state = "REVIEWING" if (not session_mode and file_path and os.path.exists(file_path)) else "WAITING"
    current_doc_type = doc_type
    current_doc_name = doc_type_name
    doc_index = 1
    total_docs = 1
    rating = 5  # 1 to 5 stars default
    hovered_star = 0
    show_cat_modal = False
    texture: rl.Texture | None = None

    # Review Fields
    fields: list[TrainerField] = [
        TrainerField("name", "Applicant Name", extracted_fields.get("name", "")),
        TrainerField("dob", "Date of Birth (DD/MM/YYYY)", extracted_fields.get("dob", "")),
        TrainerField("age", "Age (Years)", extracted_fields.get("age", "")),
        TrainerField("aadhaar", "Aadhaar Card No (12 Digits)", extracted_fields.get("aadhaar", "")),
        TrainerField("address", "Residential Address", extracted_fields.get("address", "")),
        TrainerField("prev_cert_no", "Prev Cert No / File No", extracted_fields.get("prev_cert_no", "")),
        TrainerField("years_in_goa", "Years in Goa / Residing Since", str(extracted_fields.get("years_in_goa", "15"))),
    ]
    active_field_idx = 0

    # Learned Spell Replacement inputs
    misread_field = TrainerField("misread", "Misread Word (OCR)", "")
    correction_field = TrainerField("correction", "Corrected Word (Teach)", "")
    active_spell_idx = -1

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
    ocr_scroll_y = 0.0
    copied_timer = 0.0

    # Initial texture load if file_path is already provided
    if file_path and os.path.exists(file_path):
        preview_img_path = file_path
        if file_path.lower().endswith(".pdf"):
            rendered_png = render_pdf_first_page_to_png(file_path)
            if rendered_png and os.path.exists(rendered_png):
                preview_img_path = rendered_png
        if os.path.exists(preview_img_path):
            try:
                texture = rl.load_texture(preview_img_path.encode('utf-8'))
                if texture and texture.id > 0:
                    rl.set_texture_filter(texture, rl.TEXTURE_FILTER_BILINEAR)
            except Exception as e:
                print(f"Texture error: {e}", file=sys.stderr)

    action_result: dict | None = None

    # 5. Main Interactive Session Loop
    while not rl.window_should_close() and action_result is None:
        dt = rl.get_frame_time()
        cursor_timer += dt
        w = rl.get_screen_width()
        h = rl.get_screen_height()
        mouse_pos = rl.get_mouse_position()
        is_mouse_pressed = rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT)
        is_mouse_down = rl.is_mouse_button_down(rl.MOUSE_BUTTON_LEFT)
        ctrl_down = rl.is_key_down(rl.KEY_LEFT_CONTROL) or rl.is_key_down(rl.KEY_RIGHT_CONTROL)

        # Fullscreen Toggle via F11
        if rl.is_key_pressed(rl.KEY_F11):
            rl.toggle_fullscreen()

        # Responsive scaling
        scale = max(0.9, min(1.3, w / 1600.0))
        scale_y = max(0.9, min(1.25, h / 900.0))

        header_h = 56
        footer_h = 40
        content_y = header_h + 8
        content_h = h - header_h - footer_h - 16

        # 3-SubWindow Proportions
        margin_x = 12
        gap = 12
        total_usable_w = w - 2 * margin_x - 2 * gap

        win1_w = int(total_usable_w * 0.35)
        win2_w = int(total_usable_w * 0.31)
        win3_w = total_usable_w - win1_w - win2_w

        win1_x = margin_x
        win2_x = win1_x + win1_w + gap
        win3_x = win2_x + win2_w + gap

        win1_rect = rl.Rectangle(win1_x, content_y, win1_w, content_h)
        win2_rect = rl.Rectangle(win2_x, content_y, win2_w, content_h)
        win3_rect = rl.Rectangle(win3_x, content_y, win3_w, content_h)

        # Track interactive hover to isolate mouse dragging
        any_button_hovered = False

        # Check for IPC commands from TypeScript
        try:
            while not cmd_queue.empty():
                raw_cmd = cmd_queue.get_nowait()
                msg = json.loads(raw_cmd)
                cmd_type = msg.get("command")
                if cmd_type == "load_doc":
                    file_path = msg.get("filePath", "")
                    current_doc_type = msg.get("docType", "document")
                    current_doc_name = msg.get("docTypeName", "Document")
                    confidence = msg.get("confidence", 0.9)
                    doc_index = msg.get("docIndex", 1)
                    total_docs = msg.get("totalDocs", 1)
                    raw_ocr_lines = msg.get("rawOcrLines", [])
                    extracted = msg.get("extractedFields", {})

                    # Unload previous texture
                    if texture and texture.id > 0:
                        rl.unload_texture(texture)
                        texture = None

                    # Load new texture
                    preview_img_path = file_path
                    if file_path.lower().endswith(".pdf"):
                        rendered_png = render_pdf_first_page_to_png(file_path)
                        if rendered_png and os.path.exists(rendered_png):
                            preview_img_path = rendered_png

                    if os.path.exists(preview_img_path):
                        try:
                            texture = rl.load_texture(preview_img_path.encode('utf-8'))
                            if texture and texture.id > 0:
                                rl.set_texture_filter(texture, rl.TEXTURE_FILTER_BILINEAR)
                        except Exception as e:
                            print(f"Texture error: {e}", file=sys.stderr)

                    # Update demographic fields
                    for f in fields:
                        f.value = str(extracted.get(f.key, ""))
                        f.cursor_pos = len(f.value)
                        f.scroll_offset = 0

                    active_field_idx = 0
                    active_spell_idx = -1
                    misread_field.value = ""
                    misread_field.cursor_pos = 0
                    correction_field.value = ""
                    correction_field.cursor_pos = 0

                    # Reset view & scroll
                    preview_zoom = 1.0
                    preview_offset_x = 0.0
                    preview_offset_y = 0.0
                    ocr_scroll_y = 0.0
                    right_scroll_y = 0.0
                    rating = 5
                    hovered_star = 0
                    show_cat_modal = False
                    state = "REVIEWING"

                elif cmd_type == "close":
                    action_result = {"action": "exit_session"}
                    break
        except Exception:
            pass

        # -------------------------------------------------------------
        # STATE A: WAITING FOR NEXT DOCUMENT (60 FPS Animated Screen)
        # -------------------------------------------------------------
        if state == "WAITING":
            if rl.is_key_pressed(rl.KEY_ESCAPE):
                print(f"\nJSON_RESULT:{json.dumps({'action': 'exit_session'})}", flush=True)
                action_result = {"action": "exit_session"}
                break

            rl.begin_drawing()
            rl.clear_background(DRACULA_BG)

            # Header
            rl.draw_rectangle(0, 0, w, header_h, DRACULA_CURRENT)
            rl.draw_line(0, header_h, w, header_h, DRACULA_BORDER)
            draw_text_clean(font, "⚡ GoaOnAuto • OCR Quality Trainer & Field Evaluator", 20, 16, int(22 * scale), DRACULA_CYAN)

            # Waiting Card
            card_w = min(680, int(w * 0.6))
            card_h = 240
            card_x = (w - card_w) // 2
            card_y = (h - card_h) // 2
            card_rect = rl.Rectangle(card_x, card_y, card_w, card_h)
            rl.draw_rectangle_rounded(card_rect, 0.05, 8, DRACULA_CURRENT)
            rl.draw_rectangle_rounded_lines(card_rect, 0.05, 8, DRACULA_PURPLE)

            dots = "." * (int(cursor_timer * 3.5) % 4)
            draw_text_clean(font, f"⚡ Processing Next Document{dots}", card_x + 36, card_y + 36, int(22 * scale), DRACULA_YELLOW)
            draw_text_clean(font, "Local GPU Daemon (RTX 4060 CUDA) is running DocTR extraction", card_x + 36, card_y + 80, int(15 * scale), DRACULA_FG)
            draw_text_clean(font, "Extracting text lines, verifying entities, and preparing live preview...", card_x + 36, card_y + 110, int(15 * scale), DRACULA_MUTED)

            rl.draw_line(card_x + 36, card_y + 155, card_x + card_w - 36, card_y + 155, DRACULA_BORDER)
            draw_text_clean(font, "Press Esc or close window to end the training session.", card_x + 36, card_y + 175, int(14 * scale), DRACULA_CYAN)

            rl.end_drawing()
            continue

        # -------------------------------------------------------------
        # STATE B: REVIEWING CURRENT DOCUMENT (3 Sub-Windows)
        # -------------------------------------------------------------
        # Keyboard Shortcuts
        if rl.is_key_pressed(rl.KEY_ESCAPE):
            if show_cat_modal:
                show_cat_modal = False
            else:
                res = {"action": "skipped", "filePath": file_path}
                print(f"\nJSON_RESULT:{json.dumps(res)}", flush=True)
                if session_mode:
                    state = "WAITING"
                else:
                    action_result = res
                    break

        if not show_cat_modal:
            if ctrl_down and (rl.is_key_pressed(rl.KEY_ENTER) or rl.is_key_pressed(rl.KEY_KP_ENTER)):
                res = {
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
                print(f"\nJSON_RESULT:{json.dumps(res)}", flush=True)
                if session_mode:
                    state = "WAITING"
                else:
                    action_result = res
                    break

        # Sub-Window Viewport Rectangles
        titlebar_h = 42
        win1_content = rl.Rectangle(win1_rect.x + 2, win1_rect.y + titlebar_h + 2, win1_rect.width - 4, win1_rect.height - titlebar_h - 4)
        win2_content = rl.Rectangle(win2_rect.x + 2, win2_rect.y + titlebar_h + 2, win2_rect.width - 4, win2_rect.height - titlebar_h - 4)
        win3_content = rl.Rectangle(win3_rect.x + 2, win3_rect.y + titlebar_h + 2, win3_rect.width - 4, win3_rect.height - titlebar_h - 4)

        is_hover_win1 = rl.check_collision_point_rec(mouse_pos, win1_content)
        is_hover_win2 = rl.check_collision_point_rec(mouse_pos, win2_content)
        is_hover_win3 = rl.check_collision_point_rec(mouse_pos, win3_content)

        # Mouse Wheel Scrolling & Zooming
        wheel = rl.get_mouse_wheel_move()
        if wheel != 0 and not show_cat_modal:
            if is_hover_win1:
                old_zoom = preview_zoom
                preview_zoom = max(0.3, min(5.0, preview_zoom + wheel * 0.15))
                preview_offset_x -= (mouse_pos.x - win1_content.x) * (preview_zoom - old_zoom) / preview_zoom
                preview_offset_y -= (mouse_pos.y - win1_content.y) * (preview_zoom - old_zoom) / preview_zoom
            elif is_hover_win2:
                line_h = max(24, int(26 * scale))
                total_ocr_h = len(raw_ocr_lines) * line_h
                max_ocr_scroll = max(0.0, float(total_ocr_h - win2_content.height + 24))
                ocr_scroll_y = max(0.0, min(max_ocr_scroll, ocr_scroll_y - wheel * 50.0))
            elif is_hover_win3:
                right_scroll_y = max(0.0, min(350.0, right_scroll_y - wheel * 32.0))

        if copied_timer > 0:
            copied_timer = max(0.0, copied_timer - dt)

        # Pan dragging for Sub-Window 1 (isolated from buttons)
        if is_hover_win1 and is_mouse_pressed and not any_button_hovered:
            is_dragging_image = True
            drag_start_mouse = mouse_pos
            drag_start_offset = rl.Vector2(preview_offset_x, preview_offset_y)

        if is_dragging_image:
            if is_mouse_down:
                preview_offset_x = drag_start_offset.x + (mouse_pos.x - drag_start_mouse.x)
                preview_offset_y = drag_start_offset.y + (mouse_pos.y - drag_start_mouse.y)
            else:
                is_dragging_image = False

        # Text input & tab navigation
        target_f: TrainerField | None = None
        if active_spell_idx == 0:
            target_f = misread_field
        elif active_spell_idx == 1:
            target_f = correction_field
        elif 0 <= active_field_idx < len(fields):
            target_f = fields[active_field_idx]

        if not show_cat_modal:
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
                            active_field_idx = -1
                            active_spell_idx = 0
                cursor_timer = 0.0

            # Editing active field
            if target_f is not None:
                # Paste from Clipboard (Ctrl+V)
                if ctrl_down and rl.is_key_pressed(rl.KEY_V):
                    clip_text = rl.get_clipboard_text()
                    if clip_text:
                        pos = target_f.cursor_pos
                        target_f.value = target_f.value[:pos] + clip_text + target_f.value[pos:]
                        target_f.cursor_pos = pos + len(clip_text)
                        cursor_timer = 0.0

                # Backspace / Delete
                is_bk_pressed = rl.is_key_pressed(rl.KEY_BACKSPACE)
                is_bk_down = rl.is_key_down(rl.KEY_BACKSPACE)
                if repeat_backspace.update(is_bk_pressed, is_bk_down, dt):
                    pos = target_f.cursor_pos
                    if pos > 0:
                        if ctrl_down:
                            new_pos = find_prev_word_boundary(target_f.value, pos)
                            target_f.value = target_f.value[:new_pos] + target_f.value[pos:]
                            target_f.cursor_pos = new_pos
                        else:
                            target_f.value = target_f.value[:pos - 1] + target_f.value[pos:]
                            target_f.cursor_pos = pos - 1
                        cursor_timer = 0.0

                is_del_pressed = rl.is_key_pressed(rl.KEY_DELETE)
                is_del_down = rl.is_key_down(rl.KEY_DELETE)
                if repeat_delete.update(is_del_pressed, is_del_down, dt):
                    pos = target_f.cursor_pos
                    if pos < len(target_f.value):
                        if ctrl_down:
                            new_pos = find_next_word_boundary(target_f.value, pos)
                            target_f.value = target_f.value[:pos] + target_f.value[new_pos:]
                        else:
                            target_f.value = target_f.value[:pos] + target_f.value[pos + 1:]
                        cursor_timer = 0.0

                # Cursor movement
                is_left_pressed = rl.is_key_pressed(rl.KEY_LEFT)
                is_left_down = rl.is_key_down(rl.KEY_LEFT)
                if repeat_left.update(is_left_pressed, is_left_down, dt):
                    if ctrl_down:
                        target_f.cursor_pos = find_prev_word_boundary(target_f.value, target_f.cursor_pos)
                    elif target_f.cursor_pos > 0:
                        target_f.cursor_pos -= 1
                    cursor_timer = 0.0

                is_right_pressed = rl.is_key_pressed(rl.KEY_RIGHT)
                is_right_down = rl.is_key_down(rl.KEY_RIGHT)
                if repeat_right.update(is_right_pressed, is_right_down, dt):
                    if ctrl_down:
                        target_f.cursor_pos = find_next_word_boundary(target_f.value, target_f.cursor_pos)
                    elif target_f.cursor_pos < len(target_f.value):
                        target_f.cursor_pos += 1
                    cursor_timer = 0.0

                if rl.is_key_pressed(rl.KEY_HOME):
                    target_f.cursor_pos = 0
                    cursor_timer = 0.0
                if rl.is_key_pressed(rl.KEY_END):
                    target_f.cursor_pos = len(target_f.value)
                    cursor_timer = 0.0

                # Text input characters
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

        # 1. Global Header Bar
        rl.draw_rectangle(0, 0, w, header_h, DRACULA_CURRENT)
        rl.draw_line(0, header_h, w, header_h, DRACULA_BORDER)

        draw_text_clean(font, "⚡ GoaOnAuto • OCR Quality Trainer & Field Evaluator", 18, 16, int(22 * scale), DRACULA_CYAN)

        # Document Progress Pill Badge
        base_name = os.path.basename(file_path) if file_path else "No Document"
        badge_text = f"📄 [{doc_index}/{total_docs}] {base_name}"
        badge_font_size = int(15 * scale)
        badge_w = measure_text_clean(font, badge_text, badge_font_size) + 24
        badge_rect = rl.Rectangle(w - badge_w - 240, 11, badge_w, 34)
        rl.draw_rectangle_rounded(badge_rect, 0.35, 6, DRACULA_INPUT_BG)
        rl.draw_rectangle_rounded_lines(badge_rect, 0.35, 6, DRACULA_PURPLE)
        draw_text_clean(font, badge_text, badge_rect.x + 12, badge_rect.y + 7, badge_font_size, DRACULA_FG)

        # Fullscreen Toggle Button in Global Header
        fs_btn_rect = rl.Rectangle(w - 225, 11, 140, 34)
        fs_clicked, fs_hover = draw_button(
            fs_btn_rect, "⛶ Fullscreen (F11)", font, int(14 * scale),
            bg_color=DRACULA_INPUT_BG, hover_color=DRACULA_PURPLE,
            text_color=DRACULA_FG, border_color=DRACULA_BORDER,
            mouse_pos=mouse_pos, is_mouse_pressed=is_mouse_pressed, is_mouse_down=is_mouse_down
        )
        if fs_hover:
            any_button_hovered = True
        if fs_clicked:
            rl.toggle_fullscreen()

        # Exit Session Button in Global Header
        exit_btn_rect = rl.Rectangle(w - 75, 11, 60, 34)
        exit_clicked, exit_hover = draw_button(
            exit_btn_rect, "✕ Exit", font, int(14 * scale),
            bg_color=DRACULA_INPUT_BG, hover_color=DRACULA_RED,
            text_color=DRACULA_FG, border_color=DRACULA_BORDER,
            mouse_pos=mouse_pos, is_mouse_pressed=is_mouse_pressed, is_mouse_down=is_mouse_down
        )
        if exit_hover:
            any_button_hovered = True
        if exit_clicked:
            action_result = {"action": "exit_session"}
            print(f"\nJSON_RESULT:{json.dumps(action_result)}", flush=True)
            break

        # -------------------------------------------------------------
        # SUB-WINDOW 1: 🖼️ Document Viewport Window
        # -------------------------------------------------------------
        draw_subwindow(win1_rect, "Document Inspector", "🖼️", font, scale, titlebar_h=titlebar_h)

        # Titlebar Viewport Controls (Reset, Zoom-, Zoom+, Fit)
        ctrl_y = win1_rect.y + 7
        ctrl_h = 28

        btn_fit = rl.Rectangle(win1_rect.x + win1_rect.width - 64, ctrl_y, 56, ctrl_h)
        fit_c, fit_h = draw_button(
            btn_fit, "⛶ Fit", font, 13,
            bg_color=DRACULA_INPUT_BG, hover_color=DRACULA_PURPLE,
            text_color=DRACULA_CYAN, border_color=DRACULA_BORDER,
            mouse_pos=mouse_pos, is_mouse_pressed=is_mouse_pressed, is_mouse_down=is_mouse_down
        )
        if fit_h:
            any_button_hovered = True
        if fit_c and texture and texture.id > 0:
            preview_zoom = min(win1_content.width / texture.width, win1_content.height / texture.height)
            preview_offset_x = 0.0
            preview_offset_y = 0.0

        btn_zin = rl.Rectangle(btn_fit.x - 48, ctrl_y, 42, ctrl_h)
        zin_c, zin_h = draw_button(
            btn_zin, "🔍+", font, 13,
            bg_color=DRACULA_INPUT_BG, hover_color=DRACULA_PURPLE,
            text_color=DRACULA_FG, border_color=DRACULA_BORDER,
            mouse_pos=mouse_pos, is_mouse_pressed=is_mouse_pressed, is_mouse_down=is_mouse_down
        )
        if zin_h:
            any_button_hovered = True
        if zin_c:
            preview_zoom = min(5.0, preview_zoom * 1.2)

        btn_zout = rl.Rectangle(btn_zin.x - 48, ctrl_y, 42, ctrl_h)
        zout_c, zout_h = draw_button(
            btn_zout, "🔍-", font, 13,
            bg_color=DRACULA_INPUT_BG, hover_color=DRACULA_PURPLE,
            text_color=DRACULA_FG, border_color=DRACULA_BORDER,
            mouse_pos=mouse_pos, is_mouse_pressed=is_mouse_pressed, is_mouse_down=is_mouse_down
        )
        if zout_h:
            any_button_hovered = True
        if zout_c:
            preview_zoom = max(0.3, preview_zoom / 1.2)

        btn_reset = rl.Rectangle(btn_zout.x - 76, ctrl_y, 70, ctrl_h)
        reset_c, reset_h = draw_button(
            btn_reset, "⟲ 100%", font, 13,
            bg_color=DRACULA_INPUT_BG, hover_color=DRACULA_PURPLE,
            text_color=DRACULA_CYAN, border_color=DRACULA_BORDER,
            mouse_pos=mouse_pos, is_mouse_pressed=is_mouse_pressed, is_mouse_down=is_mouse_down
        )
        if reset_h:
            any_button_hovered = True
        if reset_c:
            preview_zoom = 1.0
            preview_offset_x = 0.0
            preview_offset_y = 0.0

        # Sub-Window 1 Content: Document Image Preview
        rl.draw_rectangle_rec(win1_content, DRACULA_INPUT_BG)
        rl.begin_scissor_mode(int(win1_content.x), int(win1_content.y), int(win1_content.width), int(win1_content.height))

        if texture and texture.id > 0:
            fit_scale = min(win1_content.width / texture.width, win1_content.height / texture.height) * 0.95
            total_scale = fit_scale * preview_zoom
            disp_w = texture.width * total_scale
            disp_h = texture.height * total_scale

            base_x = win1_content.x + (win1_content.width - disp_w) / 2.0 + preview_offset_x
            base_y = win1_content.y + (win1_content.height - disp_h) / 2.0 + preview_offset_y

            src_r = rl.Rectangle(0, 0, texture.width, texture.height)
            dst_r = rl.Rectangle(base_x, base_y, disp_w, disp_h)
            rl.draw_texture_pro(texture, src_r, dst_r, rl.Vector2(0, 0), 0.0, rl.WHITE)
        else:
            draw_text_clean(font, "⚠️ No Image Preview Available", win1_content.x + 30, win1_content.y + win1_content.height / 2, int(17 * scale), DRACULA_RED)

        rl.end_scissor_mode()

        # Floating Bottom Viewport Badge
        tex_info = f"🔍 {int(preview_zoom * 100)}%"
        if texture and texture.id > 0:
            tex_info += f"  •  {texture.width}×{texture.height} px"
        tex_info_w = measure_text_clean(font, tex_info, 13) + 20
        tex_badge_rect = rl.Rectangle(win1_content.x + 10, win1_content.y + win1_content.height - 32, tex_info_w, 24)
        rl.draw_rectangle_rounded(tex_badge_rect, 0.4, 4, rl.Color(20, 21, 30, 200))
        draw_text_clean(font, tex_info, tex_badge_rect.x + 10, tex_badge_rect.y + 5, 13, DRACULA_MUTED)

        # -------------------------------------------------------------
        # SUB-WINDOW 2: 📜 Live OCR Stream Inspector Window
        # -------------------------------------------------------------
        badge_count = f"{len(raw_ocr_lines)} Lines"
        draw_subwindow(win2_rect, "Live OCR Stream", "📜", font, scale, titlebar_h=titlebar_h, badge_text=badge_count)

        # Titlebar Copy All Button
        copy_text = "✓ Copied!" if copied_timer > 0 else "📋 Copy All"
        copy_w = 110
        btn_copy = rl.Rectangle(win2_rect.x + win2_rect.width - copy_w - 8, win2_rect.y + 7, copy_w, ctrl_h)
        copy_c, copy_h = draw_button(
            btn_copy, copy_text, font, 13,
            bg_color=DRACULA_GREEN if copied_timer > 0 else DRACULA_INPUT_BG,
            hover_color=DRACULA_CYAN,
            text_color=DRACULA_BG if copied_timer > 0 else DRACULA_FG,
            border_color=DRACULA_BORDER,
            mouse_pos=mouse_pos, is_mouse_pressed=is_mouse_pressed, is_mouse_down=is_mouse_down
        )
        if copy_h:
            any_button_hovered = True
        if copy_c and len(raw_ocr_lines) > 0:
            all_text = "\n".join(raw_ocr_lines)
            if set_clipboard_text(all_text):
                copied_timer = 2.0

        # Sub-Window 2 Content: Monospace Code Canvas with Line Numbers
        rl.draw_rectangle_rec(win2_content, DRACULA_INPUT_BG)
        rl.begin_scissor_mode(int(win2_content.x), int(win2_content.y), int(win2_content.width), int(win2_content.height))

        line_h = max(24, int(26 * scale))
        line_font_size = int(15 * scale)

        if len(raw_ocr_lines) == 0:
            draw_text_clean(font, "⚠️ No Raw OCR Text Detected", win2_content.x + 24, win2_content.y + 40, int(17 * scale), DRACULA_ORANGE)
            draw_text_clean(font, "The scanner did not find legible characters in this document.", win2_content.x + 24, win2_content.y + 68, int(14 * scale), DRACULA_MUTED)
        else:
            for idx, line_text in enumerate(raw_ocr_lines):
                line_y = win2_content.y + 8 + idx * line_h - ocr_scroll_y
                if line_y + line_h < win2_content.y or line_y > win2_content.y + win2_content.height:
                    continue

                line_rect = rl.Rectangle(win2_content.x, line_y, win2_content.width - 12, line_h)
                line_hover = rl.check_collision_point_rec(mouse_pos, line_rect)

                # Click line to populate misread word
                if line_hover and is_hover_win2:
                    rl.draw_rectangle_rec(line_rect, rl.Color(68, 71, 90, 120))
                    if is_mouse_pressed and not misread_field.value.strip():
                        misread_field.value = line_text.strip()
                        misread_field.cursor_pos = len(misread_field.value)
                        active_spell_idx = 1
                        cursor_timer = 0.0

                gutter_text = f"{idx + 1:2d} │ "
                draw_text_clean(font, gutter_text, win2_content.x + 8, line_y + 3, line_font_size, DRACULA_MUTED)
                draw_text_clean(font, line_text, win2_content.x + 46, line_y + 3, line_font_size, DRACULA_FG)

        rl.end_scissor_mode()

        # Custom Sleek Scrollbar for Sub-Window 2
        total_ocr_h = len(raw_ocr_lines) * line_h
        max_ocr_scroll = max(0.0, float(total_ocr_h - win2_content.height + 24))
        if max_ocr_scroll > 0:
            track_w = 6
            track_x = win2_content.x + win2_content.width - 8
            track_y = win2_content.y + 4
            track_h = win2_content.height - 8
            rl.draw_rectangle_rounded(rl.Rectangle(track_x, track_y, track_w, track_h), 0.5, 4, DRACULA_BG)

            thumb_h = max(24, int(track_h * (win2_content.height / float(total_ocr_h))))
            thumb_y = track_y + (ocr_scroll_y / max_ocr_scroll) * (track_h - thumb_h)
            rl.draw_rectangle_rounded(rl.Rectangle(track_x, thumb_y, track_w, thumb_h), 0.5, 4, DRACULA_PURPLE)

        # -------------------------------------------------------------
        # SUB-WINDOW 3: 🎯 Ground-Truth Evaluation & Dataset Retraining Form
        # -------------------------------------------------------------
        draw_subwindow(win3_rect, "Ground-Truth & Retraining", "🎯", font, scale, titlebar_h=titlebar_h)

        # Titlebar Category Selector Button
        cat_btn_label = f"🏷️ {current_doc_name} ▾"
        cat_btn_w = max(180, int(measure_text_clean(font, cat_btn_label, 14) + 28))
        btn_cat = rl.Rectangle(win3_rect.x + win3_rect.width - cat_btn_w - 8, win3_rect.y + 7, cat_btn_w, ctrl_h)
        cat_c, cat_h = draw_button(
            btn_cat, cat_btn_label, font, 13,
            bg_color=DRACULA_INPUT_BG, hover_color=DRACULA_PURPLE,
            text_color=DRACULA_FG, border_color=DRACULA_BORDER,
            mouse_pos=mouse_pos, is_mouse_pressed=is_mouse_pressed, is_mouse_down=is_mouse_down
        )
        if cat_h:
            any_button_hovered = True
        if cat_c:
            show_cat_modal = not show_cat_modal

        # Sub-Window 3 Content: Structured Form Cards
        rl.draw_rectangle_rec(win3_content, DRACULA_CURRENT)
        rl.begin_scissor_mode(int(win3_content.x), int(win3_content.y), int(win3_content.width), int(win3_content.height))

        curr_y = win3_content.y + 14 - right_scroll_y

        # CARD A: ⭐ OCR Extraction Quality Rating
        card_a_rect = rl.Rectangle(win3_content.x + 12, curr_y, win3_content.width - 24, 76)
        rl.draw_rectangle_rounded(card_a_rect, 0.08, 6, DRACULA_BG)
        rl.draw_rectangle_rounded_lines(card_a_rect, 0.08, 6, DRACULA_BORDER)

        draw_text_clean(font, "⭐ OCR Quality Rating:", card_a_rect.x + 14, card_a_rect.y + 10, int(15 * scale), DRACULA_YELLOW)

        star_start_x = card_a_rect.x + 14
        hovered_star = 0
        for star_idx in range(1, 6):
            star_x = star_start_x + (star_idx - 1) * 36
            star_rect = rl.Rectangle(star_x, card_a_rect.y + 34, 32, 32)
            star_hover = rl.check_collision_point_rec(mouse_pos, star_rect)
            if star_hover:
                hovered_star = star_idx
                any_button_hovered = True
                if is_mouse_pressed:
                    rating = star_idx

            is_filled = star_idx <= (hovered_star if hovered_star > 0 else rating)
            star_col = DRACULA_YELLOW if is_filled else DRACULA_BORDER
            draw_text_clean(font, "★", star_x + 2, card_a_rect.y + 30, int(26 * scale), star_col)

        curr_rating_display = hovered_star if hovered_star > 0 else rating
        rating_desc = RATING_LABELS.get(curr_rating_display, "")
        draw_text_clean(font, rating_desc, star_start_x + 195, card_a_rect.y + 38, int(14 * scale), DRACULA_FG)

        curr_y += 88

        # CARD B: 📝 Verified Demographic Fields
        draw_text_clean(font, "📝 Demographic Fields (Ground-Truth):", win3_content.x + 14, curr_y, int(16 * scale), DRACULA_CYAN)
        curr_y += 24

        inp_h = 36
        lbl_w = int((win3_content.width - 28) * 0.38)
        field_inp_w = int((win3_content.width - 28) - lbl_w - 12)

        for i, fld in enumerate(fields):
            is_active = (active_field_idx == i and active_spell_idx == -1)
            lbl_x = win3_content.x + 14
            inp_x = lbl_x + lbl_w + 8
            fld.rect = rl.Rectangle(inp_x, curr_y, field_inp_w, inp_h)

            draw_text_clean(font, fld.label, lbl_x, curr_y + 8, int(14 * scale), DRACULA_FG)

            # Click focus & set cursor
            if is_mouse_pressed and rl.check_collision_point_rec(mouse_pos, fld.rect):
                active_field_idx = i
                active_spell_idx = -1
                click_rel = mouse_pos.x - (inp_x + 8)
                if click_rel <= 0:
                    fld.cursor_pos = fld.scroll_offset
                else:
                    best_k = len(fld.value)
                    min_dist = float('inf')
                    for k in range(len(fld.value) + 1):
                        dist = abs(measure_text_clean(font, fld.value[:k], int(15 * scale)) - click_rel)
                        if dist < min_dist:
                            min_dist = dist
                            best_k = k
                    fld.cursor_pos = best_k
                cursor_timer = 0.0

            box_bg = DRACULA_INPUT_BG if is_active else DRACULA_BG
            border_col = DRACULA_CYAN if is_active else DRACULA_BORDER
            rl.draw_rectangle_rounded(fld.rect, 0.25, 4, box_bg)
            rl.draw_rectangle_rounded_lines(fld.rect, 0.25, 4, border_col)

            # Auto-scroll text in input field
            avail_w = fld.rect.width - 16
            while fld.cursor_pos < fld.scroll_offset:
                fld.scroll_offset = max(0, fld.scroll_offset - 3)
            while True:
                sub_w = measure_text_clean(font, fld.value[fld.scroll_offset:fld.cursor_pos], int(15 * scale))
                if sub_w > avail_w - 20 and fld.scroll_offset < fld.cursor_pos:
                    fld.scroll_offset += 2
                else:
                    break

            rl.begin_scissor_mode(int(fld.rect.x + 2), int(fld.rect.y + 2), int(fld.rect.width - 4), int(fld.rect.height - 4))
            draw_text_clean(font, fld.value[fld.scroll_offset:], inp_x + 8, curr_y + 8, int(15 * scale), DRACULA_FG)

            # Blinking Cursor
            if is_active and (int(cursor_timer * 2.5) % 2 == 0):
                c_w = measure_text_clean(font, fld.value[fld.scroll_offset:fld.cursor_pos], int(15 * scale))
                rl.draw_line_ex(
                    rl.Vector2(inp_x + 8 + c_w, curr_y + 6),
                    rl.Vector2(inp_x + 8 + c_w, curr_y + 30),
                    2.0,
                    DRACULA_CYAN
                )
            rl.end_scissor_mode()

            curr_y += inp_h + 8

        curr_y += 8

        # CARD C: 🔤 Teach OCR Spell-Correction Pair
        draw_text_clean(font, "🔤 Teach OCR Spell-Correction (Auto-learns pair):", win3_content.x + 14, curr_y, int(16 * scale), DRACULA_PINK)
        curr_y += 24

        spell_box_w = int((win3_content.width - 48) / 2.0)
        misread_field.rect = rl.Rectangle(win3_content.x + 14, curr_y, spell_box_w, inp_h)
        arrow_x = win3_content.x + 14 + spell_box_w + 4
        correction_field.rect = rl.Rectangle(arrow_x + 24, curr_y, spell_box_w, inp_h)

        is_mis_active = (active_spell_idx == 0)
        is_corr_active = (active_spell_idx == 1)

        if is_mouse_pressed and rl.check_collision_point_rec(mouse_pos, misread_field.rect):
            active_spell_idx = 0
            active_field_idx = -1
            misread_field.cursor_pos = len(misread_field.value)
            cursor_timer = 0.0

        rl.draw_rectangle_rounded(misread_field.rect, 0.25, 4, DRACULA_INPUT_BG if is_mis_active else DRACULA_BG)
        rl.draw_rectangle_rounded_lines(misread_field.rect, 0.25, 4, DRACULA_PINK if is_mis_active else DRACULA_BORDER)
        disp_mis = misread_field.value if misread_field.value else "e.g. Mamlatdr"
        draw_text_clean(font, disp_mis, misread_field.rect.x + 8, misread_field.rect.y + 8, int(14 * scale), DRACULA_FG if misread_field.value else DRACULA_MUTED)

        if is_mis_active and (int(cursor_timer * 2.5) % 2 == 0):
            c_w = measure_text_clean(font, misread_field.value[:misread_field.cursor_pos], int(14 * scale))
            rl.draw_line_ex(
                rl.Vector2(misread_field.rect.x + 8 + c_w, misread_field.rect.y + 6),
                rl.Vector2(misread_field.rect.x + 8 + c_w, misread_field.rect.y + 30),
                2.0,
                DRACULA_PINK
            )

        draw_text_clean(font, "➔", arrow_x + 4, curr_y + 8, int(17 * scale), DRACULA_MUTED)

        if is_mouse_pressed and rl.check_collision_point_rec(mouse_pos, correction_field.rect):
            active_spell_idx = 1
            active_field_idx = -1
            correction_field.cursor_pos = len(correction_field.value)
            cursor_timer = 0.0

        rl.draw_rectangle_rounded(correction_field.rect, 0.25, 4, DRACULA_INPUT_BG if is_corr_active else DRACULA_BG)
        rl.draw_rectangle_rounded_lines(correction_field.rect, 0.25, 4, DRACULA_GREEN if is_corr_active else DRACULA_BORDER)
        disp_cor = correction_field.value if correction_field.value else "e.g. Mamlatdar"
        draw_text_clean(font, disp_cor, correction_field.rect.x + 8, correction_field.rect.y + 8, int(14 * scale), DRACULA_FG if correction_field.value else DRACULA_MUTED)

        if is_corr_active and (int(cursor_timer * 2.5) % 2 == 0):
            c_w = measure_text_clean(font, correction_field.value[:correction_field.cursor_pos], int(14 * scale))
            rl.draw_line_ex(
                rl.Vector2(correction_field.rect.x + 8 + c_w, correction_field.rect.y + 6),
                rl.Vector2(correction_field.rect.x + 8 + c_w, correction_field.rect.y + 30),
                2.0,
                DRACULA_GREEN
            )

        curr_y += inp_h + 20

        # CARD D: 🚀 Action Command Bar inside Sub-Window 3 (Proper Constraints, No Overflow)
        action_card_w = win3_content.width - 24
        action_card_rect = rl.Rectangle(win3_content.x + 12, curr_y, action_card_w, 64)
        rl.draw_rectangle_rounded(action_card_rect, 0.08, 6, DRACULA_BG)
        rl.draw_rectangle_rounded_lines(action_card_rect, 0.08, 6, DRACULA_BORDER)

        btn_action_y = action_card_rect.y + 12
        btn_action_h = 40

        skip_w = 140
        submit_w = max(260, int(action_card_w - skip_w - 36))

        btn_skip = rl.Rectangle(action_card_rect.x + 12, btn_action_y, skip_w, btn_action_h)
        skip_clicked, skip_h = draw_button(
            btn_skip, "⏭️ Skip (Esc)", font, int(15 * scale),
            bg_color=DRACULA_CURRENT, hover_color=DRACULA_INPUT_BG,
            text_color=DRACULA_FG, border_color=DRACULA_BORDER,
            mouse_pos=mouse_pos, is_mouse_pressed=is_mouse_pressed, is_mouse_down=is_mouse_down
        )
        if skip_h:
            any_button_hovered = True
        if skip_clicked:
            res = {"action": "skipped", "filePath": file_path}
            print(f"\nJSON_RESULT:{json.dumps(res)}", flush=True)
            if session_mode:
                state = "WAITING"
            else:
                action_result = res
                break

        btn_submit = rl.Rectangle(action_card_rect.x + 12 + skip_w + 12, btn_action_y, submit_w, btn_action_h)
        submit_clicked, submit_h = draw_button(
            btn_submit, "★ Save & Retrain (Ctrl+Enter)", font, int(15 * scale),
            bg_color=DRACULA_GREEN, hover_color=rl.Color(110, 255, 150, 255),
            text_color=DRACULA_BG, border_color=None,
            mouse_pos=mouse_pos, is_mouse_pressed=is_mouse_pressed, is_mouse_down=is_mouse_down
        )
        if submit_h:
            any_button_hovered = True
        if submit_clicked:
            res = {
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
            print(f"\nJSON_RESULT:{json.dumps(res)}", flush=True)
            if session_mode:
                state = "WAITING"
            else:
                action_result = res
                break

        rl.end_scissor_mode()

        # -------------------------------------------------------------
        # GLOBAL FOOTER STATUS BAR
        # -------------------------------------------------------------
        rl.draw_rectangle(0, h - footer_h, w, footer_h, DRACULA_CURRENT)
        rl.draw_line(0, h - footer_h, w, h - footer_h, DRACULA_BORDER)

        hints_text = "⌨️  Tab: Next Field  •  Mouse Wheel: Scroll & Zoom  •  F11: Fullscreen  •  Ctrl+Enter: Save & Retrain  •  Esc: Skip"
        draw_text_clean(font, hints_text, 20, h - footer_h + 12, int(14 * scale), DRACULA_MUTED)

        gpu_status_txt = "🟢 Local GPU Worker: RTX 4060 CUDA (DocTR)"
        gpu_txt_w = measure_text_clean(font, gpu_status_txt, int(13 * scale))
        draw_text_clean(font, gpu_status_txt, w - gpu_txt_w - 20, h - footer_h + 12, int(13 * scale), DRACULA_GREEN)

        # -------------------------------------------------------------
        # MODAL: DOCUMENT CATEGORY SELECTOR (Overlay)
        # -------------------------------------------------------------
        if show_cat_modal:
            # Semi-transparent backdrop
            rl.draw_rectangle(0, 0, w, h, rl.Color(0, 0, 0, 180))

            modal_w = 720
            modal_h = 510
            modal_x = (w - modal_w) // 2
            modal_y = (h - modal_h) // 2
            modal_rect = rl.Rectangle(modal_x, modal_y, modal_w, modal_h)

            rl.draw_rectangle_rounded(modal_rect, 0.04, 8, DRACULA_BG)
            rl.draw_rectangle_rounded_lines(modal_rect, 0.04, 8, DRACULA_PURPLE)

            # Modal Titlebar
            draw_text_clean(font, "🏷️ Select Document Category", modal_x + 24, modal_y + 18, 20, DRACULA_CYAN)

            # Close button in modal
            btn_close_modal = rl.Rectangle(modal_x + modal_w - 44, modal_y + 14, 30, 30)
            modal_close_c, modal_close_h = draw_button(
                btn_close_modal, "✕", font, 16,
                bg_color=DRACULA_CURRENT, hover_color=DRACULA_RED,
                text_color=DRACULA_FG, border_color=DRACULA_BORDER,
                mouse_pos=mouse_pos, is_mouse_pressed=is_mouse_pressed, is_mouse_down=is_mouse_down
            )
            if modal_close_h:
                any_button_hovered = True
            if modal_close_c:
                show_cat_modal = False

            grid_x = modal_x + 24
            grid_y = modal_y + 60
            cat_item_w = 320
            cat_item_h = 36

            for idx, (cat_id, cat_name) in enumerate(SUPPORTED_CATEGORIES):
                col = idx % 2
                row = idx // 2
                bx = grid_x + col * (cat_item_w + 24)
                by = grid_y + row * (cat_item_h + 6)
                brect = rl.Rectangle(bx, by, cat_item_w, cat_item_h)
                is_selected = (cat_id == current_doc_type)

                item_c, item_h = draw_button(
                    brect, cat_name, font, 15,
                    bg_color=DRACULA_PURPLE if is_selected else DRACULA_INPUT_BG,
                    hover_color=DRACULA_CURRENT if not is_selected else DRACULA_PURPLE,
                    text_color=DRACULA_BG if is_selected else DRACULA_FG,
                    border_color=DRACULA_CYAN if is_selected else DRACULA_BORDER,
                    mouse_pos=mouse_pos, is_mouse_pressed=is_mouse_pressed, is_mouse_down=is_mouse_down
                )
                if item_h:
                    any_button_hovered = True
                if item_c:
                    current_doc_type = cat_id
                    current_doc_name = cat_name
                    show_cat_modal = False

        # Update Mouse Cursor Icon
        if any_button_hovered:
            rl.set_mouse_cursor(rl.MOUSE_CURSOR_POINTING_HAND)
        else:
            rl.set_mouse_cursor(rl.MOUSE_CURSOR_DEFAULT)

        rl.end_drawing()

    # Window was closed or loop ended
    if not action_result:
        action_result = {"action": "exit_session"}
        print(f"\nJSON_RESULT:{json.dumps(action_result)}", flush=True)

    # Unload texture and close window
    if texture and texture.id > 0:
        rl.unload_texture(texture)
    if font and hasattr(font, 'baseSize') and font.baseSize > 0:
        rl.unload_font(font)
    rl.close_window()

    return action_result


def main():
    parser = argparse.ArgumentParser(description="GoaOnAuto OCR Quality Trainer GUI")
    parser.add_argument("--session", action="store_true", help="Run interactive multi-document session with persistent window")
    parser.add_argument("--file", help="Path to document image or PDF (optional in session mode)")
    parser.add_argument("--type", default="document", help="Detected document category")
    parser.add_argument("--name", default="Unknown Document", help="Human-readable category name")
    parser.add_argument("--confidence", type=float, default=0.9, help="Detection confidence")
    parser.add_argument("--fields", default="{}", help="JSON string of extracted fields")
    parser.add_argument("--ocr-lines", default="[]", help="JSON string array of raw OCR lines")

    args = parser.parse_args()

    if args.session:
        run_ocr_trainer(session_mode=True)
    elif args.file:
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
            raw_ocr_lines=raw_lines,
            session_mode=False
        )
    else:
        # Default to interactive session mode
        run_ocr_trainer(session_mode=True)


if __name__ == "__main__":
    main()
