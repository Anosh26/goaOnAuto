"""
GoaOnAuto Human Confirmation System - Raylib GPU-Accelerated Verification GUI.
Dracula Theme | 1920x1080 Full HD | Custom Keyword Input | Crisp Typography.
"""
import sys
import os
import argparse
import json
import psutil
import tempfile
import time
from PIL import Image
import pyray as rl

# Ensure project root in sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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

def render_pdf_first_page_to_png(pdf_path: str) -> str:
    """Renders page 1 of PDF to a system temp PNG image file for GUI preview."""
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(pdf_path)
        page = pdf[0]
        image = page.render(scale=2.5).to_pil()
        # Save in OS temp dir to NEVER pollute work directory or Google Drive
        temp_dir = tempfile.gettempdir()
        file_hash = abs(hash(pdf_path)) % 10000000
        temp_png = os.path.join(temp_dir, f"goa_gui_prev_{file_hash}.png")
        image.save(temp_png)
        return temp_png
    except Exception as e:
        print(f"PDF Preview render fallback error: {e}", file=sys.stderr)
        return ""

def get_hardware_status():
    mem = psutil.virtual_memory()
    cpu_pct = psutil.cpu_percent(interval=None)
    free_ram_gb = round(mem.available / (1024 ** 3), 2)
    cpu_free_pct = round(max(0, 100.0 - cpu_pct), 1)
    
    gpu_vram_mb = 0
    try:
        import torch
        if torch.cuda.is_available():
            gpu_vram_mb = round(torch.cuda.memory_allocated(0) / (1024 ** 2), 1)
    except Exception:
        pass
        
    return free_ram_gb, cpu_free_pct, gpu_vram_mb

def draw_text_clean(font, text: str, x: float, y: float, size: float, color):
    """Draws crisp anti-aliased text using custom font or fallback."""
    if font and hasattr(font, 'base_size') and font.base_size > 0:
        rl.draw_text_ex(font, text.encode('utf-8', errors='ignore'), rl.Vector2(float(x), float(y)), float(size), 1.0, color)
    else:
        rl.draw_text(text, int(x), int(y), int(size), color)

def measure_text_clean(font, text: str, size: float) -> float:
    if font and hasattr(font, 'base_size') and font.base_size > 0:
        vec = rl.measure_text_ex(font, text.encode('utf-8', errors='ignore'), float(size), 1.0)
        return vec.x
    return float(rl.measure_text(text, int(size)))

def run_confirmation_gui(file_path: str, detected_type: str, detected_name: str, extracted_name: str, confidence: float) -> dict:
    if not os.path.exists(file_path):
        return {"action": "error", "message": f"File not found: {file_path}"}

    # Prepare preview image file
    preview_img_path = file_path
    is_temp_preview = False
    if file_path.lower().endswith(".pdf"):
        rendered_png = render_pdf_first_page_to_png(file_path)
        if rendered_png and os.path.exists(rendered_png):
            preview_img_path = rendered_png
            is_temp_preview = True

    # Window Configuration (Responsive to screen, centered, fits within taskbar bounds)
    rl.set_config_flags(rl.FLAG_WINDOW_RESIZABLE | rl.FLAG_MSAA_4X_HINT | rl.FLAG_WINDOW_ALWAYS_RUN)
    
    # Initialize with comfortable dimensions that fit any 1080p display
    init_w = 1680
    init_h = 940
    rl.init_window(init_w, init_h, "GoaOnAuto - Human Confirmation & Dataset Verification System")
    rl.set_target_fps(60)

    # Dynamic monitor fitting & centering
    try:
        mon = rl.get_current_monitor()
        mon_w = rl.get_monitor_width(mon)
        mon_h = rl.get_monitor_height(mon)
        if mon_w > 800 and mon_h > 600:
            target_w = min(1720, mon_w - 60)
            target_h = min(960, mon_h - 90)
            rl.set_window_size(target_w, target_h)
            rl.set_window_position((mon_w - target_w) // 2, max(20, (mon_h - target_h) // 2 - 20))
    except Exception:
        pass

    # Windows ShowWindow Restore & Foreground Activation
    try:
        import ctypes
        user32 = ctypes.windll.user32
        target_hwnd = user32.FindWindowW(None, "GoaOnAuto - Human Confirmation & Dataset Verification System")
        if target_hwnd:
            SW_RESTORE = 9
            user32.ShowWindow(target_hwnd, SW_RESTORE)
            user32.SetForegroundWindow(target_hwnd)
            user32.SetActiveWindow(target_hwnd)
            user32.BringWindowToTop(target_hwnd)
    except Exception:
        pass

    # Load Crisp Readable Font (JetBrains Mono Nerd Font / JetBrains Mono / Cascadia / Consolas / Segoe UI)
    font = None
    home_dir = os.path.expanduser("~")
    font_paths = [
        os.path.join(home_dir, "AppData", "Local", "Microsoft", "Windows", "Fonts", "JetBrainsMonoNerdFont-Regular.ttf"),
        os.path.join(home_dir, "AppData", "Local", "Microsoft", "Windows", "Fonts", "JetBrainsMonoNerdFontMono-Regular.ttf"),
        os.path.join(home_dir, "AppData", "Local", "Microsoft", "Windows", "Fonts", "JetBrainsMono-Regular.ttf"),
        "C:/Windows/Fonts/JetBrainsMonoNerdFont-Regular.ttf",
        "C:/Windows/Fonts/JetBrainsMono-Regular.ttf",
        "C:/Windows/Fonts/cascadiacode.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf"
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = rl.load_font_ex(fp.encode('utf-8'), 36, None, 0)
                if font and font.base_size > 0:
                    rl.set_texture_filter(font.texture, rl.TEXTURE_FILTER_BILINEAR)
                    print(f"[GUI] Loaded font: {fp}")
                    break
            except Exception:
                font = None

    # Load Texture
    texture = None
    if os.path.exists(preview_img_path) and not preview_img_path.lower().endswith(".pdf"):
        try:
            texture = rl.load_texture(preview_img_path.encode('utf-8'))
            if texture and texture.id > 0:
                rl.set_texture_filter(texture, rl.TEXTURE_FILTER_BILINEAR)
        except Exception as e:
            print(f"Texture load error: {e}", file=sys.stderr)

    selected_type = detected_type
    selected_name = detected_name
    current_extracted_name = extracted_name or ""
    custom_keyword = ""
    is_keyword_focused = False
    show_grid = False
    action_result = None

    # Dracula Color Palette
    dracula_bg = rl.Color(40, 42, 54, 255)         # #282a36 (Main background)
    dracula_card = rl.Color(68, 71, 90, 255)       # #44475a (Current line / Panels)
    dracula_input = rl.Color(33, 34, 44, 255)      # #21222c (Darker input fields)
    dracula_border = rl.Color(98, 114, 164, 255)   # #6272a4 (Comment / Borders)
    dracula_fg = rl.Color(248, 248, 242, 255)      # #f8f8f2 (White text)
    dracula_muted = rl.Color(140, 153, 190, 255)   # Muted readable text
    dracula_purple = rl.Color(189, 147, 249, 255)  # #bd93f9 (Accent Purple)
    dracula_cyan = rl.Color(139, 233, 253, 255)    # #8be9fd (Accent Cyan)
    dracula_green = rl.Color(80, 250, 123, 255)    # #50fa7b (Success / Confirm)
    dracula_orange = rl.Color(255, 184, 108, 255)  # #ffb86c (Warning / Changed)
    dracula_pink = rl.Color(255, 121, 198, 255)    # #ff79c6 (Highlight / Details)
    dracula_red = rl.Color(255, 85, 85, 255)       # #ff5555 (Danger / Skip)
    dracula_yellow = rl.Color(241, 250, 140, 255)  # #f1fa8c (Confidence score)

    frame_count = 0

    while not rl.window_should_close() and action_result is None:
        w = rl.get_screen_width()
        h = rl.get_screen_height()
        mouse_pos = rl.get_mouse_position()
        frame_count += 1

        if frame_count == 1:
            try:
                import ctypes
                user32 = ctypes.windll.user32
                target_hwnd = user32.FindWindowW(None, "GoaOnAuto - Human Confirmation & Dataset Verification System")
                if target_hwnd:
                    user32.ShowWindow(target_hwnd, 9)  # SW_RESTORE
                    user32.SetForegroundWindow(target_hwnd)
                    user32.SetActiveWindow(target_hwnd)
            except Exception:
                pass

        # Text input handling when keyword box is focused
        if is_keyword_focused:
            char_pressed = rl.get_char_pressed()
            while char_pressed > 0:
                if (char_pressed >= 32) and (char_pressed <= 126) and len(custom_keyword) < 60:
                    custom_keyword += chr(char_pressed)
                char_pressed = rl.get_char_pressed()

            if (rl.is_key_pressed(rl.KEY_BACKSPACE) or (rl.is_key_down(rl.KEY_BACKSPACE) and frame_count % 6 == 0)) and len(custom_keyword) > 0:
                custom_keyword = custom_keyword[:-1]

            if rl.is_key_pressed(rl.KEY_TAB) or rl.is_key_pressed(rl.KEY_ESCAPE):
                is_keyword_focused = False

        # Global Keyboard shortcuts (when not actively typing in input box)
        if not is_keyword_focused:
            if rl.is_key_pressed(rl.KEY_ENTER) or rl.is_key_pressed(rl.KEY_KP_ENTER):
                action_result = {
                    "action": "confirmed" if selected_type == detected_type else "changed",
                    "docType": selected_type,
                    "docTypeName": selected_name,
                    "extractedName": current_extracted_name,
                    "customKeyword": custom_keyword.strip()
                }
            elif rl.is_key_pressed(rl.KEY_ESCAPE):
                action_result = {
                    "action": "skipped",
                    "docType": detected_type,
                    "docTypeName": detected_name,
                    "extractedName": current_extracted_name,
                    "customKeyword": custom_keyword.strip()
                }
            elif rl.is_key_pressed(rl.KEY_C):
                show_grid = not show_grid
        else:
            # If enter pressed inside input box, confirm
            if rl.is_key_pressed(rl.KEY_ENTER) or rl.is_key_pressed(rl.KEY_KP_ENTER):
                action_result = {
                    "action": "confirmed" if selected_type == detected_type else "changed",
                    "docType": selected_type,
                    "docTypeName": selected_name,
                    "extractedName": current_extracted_name,
                    "customKeyword": custom_keyword.strip()
                }

        free_ram_gb, cpu_free_pct, gpu_vram_mb = get_hardware_status()

        rl.begin_drawing()
        rl.clear_background(dracula_bg)

        # -----------------------------
        # 1. Top Header Bar (Dracula Style)
        # -----------------------------
        rl.draw_rectangle(0, 0, w, 70, dracula_card)
        rl.draw_line(0, 70, w, 70, dracula_border)
        draw_text_clean(font, "GoaOnAuto Document Verification & Continuous Learning", 30, 20, 26, dracula_fg)

        # Hardware Resource Gauges
        ram_color = dracula_green if free_ram_gb >= 3.0 else dracula_red
        cpu_color = dracula_green if cpu_free_pct >= 20.0 else dracula_orange
        
        status_str = f"RAM Free: {free_ram_gb} GB  |  CPU Free: {cpu_free_pct}%  |  RTX 4060 VRAM: {gpu_vram_mb} MB"
        draw_text_clean(font, status_str, w - 750, 24, 20, dracula_cyan)
        rl.draw_circle(w - 770, 35, 7, ram_color)

        # -----------------------------
        # 2. Main Panels Layout (Spacious 1920x1080)
        # -----------------------------
        preview_w = int(w * 0.58)
        info_x = preview_w + 25
        info_w = w - info_x - 30

        # Left Panel (Image Preview Box)
        rl.draw_rectangle(25, 95, preview_w - 20, h - 125, dracula_card)
        rl.draw_rectangle_lines_ex(rl.Rectangle(25, 95, preview_w - 20, h - 125), 2.0, dracula_border)
        draw_text_clean(font, "DOCUMENT VISUAL PREVIEW", 45, 110, 18, dracula_purple)

        if texture and texture.id > 0:
            box_w = preview_w - 60
            box_h = h - 200
            img_w = texture.width
            img_h = texture.height

            scale = min(box_w / img_w, box_h / img_h)
            draw_w = img_w * scale
            draw_h = img_h * scale
            draw_x = 25 + (preview_w - 20 - draw_w) / 2
            draw_y = 150 + (box_h - draw_h) / 2

            src_rect = rl.Rectangle(0, 0, float(img_w), float(img_h))
            dest_rect = rl.Rectangle(float(draw_x), float(draw_y), float(draw_w), float(draw_h))
            origin = rl.Vector2(0, 0)
            rl.draw_texture_pro(texture, src_rect, dest_rect, origin, 0.0, rl.WHITE)
        else:
            draw_text_clean(font, "Visual Preview Unavailable", preview_w // 2 - 120, h // 2, 22, dracula_muted)

        # Right Panel (AI Verification Details & Custom Input)
        rl.draw_rectangle(info_x, 95, info_w, h - 125, dracula_card)
        rl.draw_rectangle_lines_ex(rl.Rectangle(info_x, 95, info_w, h - 125), 2.0, dracula_border)

        # File & Category details
        draw_text_clean(font, "AI CLASSIFICATION ANALYSIS", info_x + 30, 115, 20, dracula_cyan)
        file_basename = os.path.basename(file_path)
        if len(file_basename) > 42:
            file_basename = file_basename[:39] + "..."
        draw_text_clean(font, f"File: {file_basename}", info_x + 30, 155, 20, dracula_fg)

        # Category Section
        draw_text_clean(font, "Document Category:", info_x + 30, 200, 18, dracula_muted)
        badge_rect = rl.Rectangle(info_x + 30, 230, info_w - 60, 54)
        rl.draw_rectangle_rec(badge_rect, dracula_input)
        rl.draw_rectangle_lines_ex(badge_rect, 2.0, dracula_purple)
        draw_text_clean(font, f"  🏷️  {selected_name} ({selected_type})", info_x + 45, 244, 22, dracula_fg)

        # Confidence Bar
        conf_pct = int(confidence * 100)
        draw_text_clean(font, f"AI Confidence Score: {conf_pct}%", info_x + 30, 305, 18, dracula_muted)
        conf_bar_bg = rl.Rectangle(info_x + 30, 335, info_w - 60, 14)
        conf_bar_fg = rl.Rectangle(info_x + 30, 335, (info_w - 60) * confidence, 14)
        rl.draw_rectangle_rec(conf_bar_bg, dracula_input)
        rl.draw_rectangle_rec(conf_bar_fg, dracula_green if confidence > 0.75 else dracula_orange)

        # Extracted Person Name
        draw_text_clean(font, "Extracted Applicant Name:", info_x + 30, 370, 18, dracula_muted)
        name_str = current_extracted_name if current_extracted_name else "(None detected)"
        draw_text_clean(font, f"👤  {name_str}", info_x + 30, 395, 22, dracula_fg)

        # -----------------------------
        # Custom Keyword / Feedback Input Box (Dracula Styled)
        # -----------------------------
        input_y = 445
        draw_text_clean(font, "Custom Keyword / Learned Trigger (Optional):", info_x + 30, input_y, 18, dracula_pink)
        draw_text_clean(font, "(Type keywords to train the model, e.g. 'residence certificate 15 years')", info_x + 30, input_y + 24, 15, dracula_muted)

        kw_box = rl.Rectangle(info_x + 30, input_y + 50, info_w - 60, 50)
        is_hover_kw = rl.check_collision_point_rec(mouse_pos, kw_box)
        if is_hover_kw and rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT):
            is_keyword_focused = True
        elif rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT) and not is_hover_kw:
            is_keyword_focused = False

        rl.draw_rectangle_rec(kw_box, dracula_input)
        kw_border_color = dracula_pink if is_keyword_focused else (dracula_purple if is_hover_kw else dracula_border)
        rl.draw_rectangle_lines_ex(kw_box, 2.0, kw_border_color)

        display_kw = custom_keyword
        if is_keyword_focused and (frame_count // 30) % 2 == 0:
            display_kw += "|"
        elif not custom_keyword and not is_keyword_focused:
            display_kw = "Click here to type custom training keywords..."

        kw_text_color = dracula_fg if (custom_keyword or is_keyword_focused) else dracula_muted
        draw_text_clean(font, display_kw, info_x + 45, input_y + 63, 19, kw_text_color)

        # -----------------------------
        # Action Buttons (Dracula Theme)
        # -----------------------------
        btn_y = 575
        btn_w = info_w - 60

        # 1. Confirm Button
        btn_confirm = rl.Rectangle(info_x + 30, btn_y, btn_w, 58)
        is_hover_confirm = rl.check_collision_point_rec(mouse_pos, btn_confirm)
        confirm_color = dracula_green if not is_hover_confirm else rl.Color(100, 255, 140, 255)
        rl.draw_rectangle_rec(btn_confirm, confirm_color)
        draw_text_clean(font, "✅  Confirm Document  (Enter)", info_x + btn_w // 2 - 130, btn_y + 16, 22, dracula_input)
        if is_hover_confirm and rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT):
            action_result = {
                "action": "confirmed" if selected_type == detected_type else "changed",
                "docType": selected_type,
                "docTypeName": selected_name,
                "extractedName": current_extracted_name,
                "customKeyword": custom_keyword.strip()
            }

        # 2. Change Category Button
        btn_change = rl.Rectangle(info_x + 30, btn_y + 75, btn_w, 58)
        is_hover_change = rl.check_collision_point_rec(mouse_pos, btn_change)
        change_color = dracula_purple if not is_hover_change else rl.Color(210, 175, 255, 255)
        rl.draw_rectangle_rec(btn_change, change_color)
        lbl_change = "✏️  Close Category Grid" if show_grid else "✏️  Change Document Category... (Press C)"
        draw_text_clean(font, lbl_change, info_x + btn_w // 2 - 180, btn_y + 91, 22, dracula_input)
        if is_hover_change and rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT):
            show_grid = not show_grid

        # 3. Skip Button
        btn_skip = rl.Rectangle(info_x + 30, btn_y + 150, btn_w, 52)
        is_hover_skip = rl.check_collision_point_rec(mouse_pos, btn_skip)
        skip_color = dracula_red if not is_hover_skip else rl.Color(255, 110, 110, 255)
        rl.draw_rectangle_rec(btn_skip, skip_color)
        draw_text_clean(font, "⏭️  Skip / Leave File Unchanged (Esc)", info_x + btn_w // 2 - 170, btn_y + 164, 20, dracula_fg)
        if is_hover_skip and rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT):
            action_result = {
                "action": "skipped",
                "docType": detected_type,
                "docTypeName": detected_name,
                "extractedName": current_extracted_name,
                "customKeyword": custom_keyword.strip()
            }

        # -----------------------------
        # Category Selector Grid Overlay (Dracula Theme)
        # -----------------------------
        if show_grid:
            grid_rect = rl.Rectangle(info_x + 15, 180, info_w - 30, h - 300)
            rl.draw_rectangle_rec(grid_rect, rl.Color(33, 34, 44, 252))
            rl.draw_rectangle_lines_ex(grid_rect, 3.0, dracula_purple)
            draw_text_clean(font, "SELECT CORRECT CATEGORY:", info_x + 35, 195, 20, dracula_cyan)

            cols = 2
            gx = info_x + 35
            gy = 235
            gw = (info_w - 90) // cols
            gh = 48

            for idx, (cat_id, cat_lbl) in enumerate(SUPPORTED_CATEGORIES):
                col = idx % cols
                row = idx // cols
                bx = gx + col * (gw + 20)
                by = gy + row * (gh + 8)
                c_btn = rl.Rectangle(bx, by, gw, gh)
                
                is_curr = cat_id == selected_type
                is_hvr = rl.check_collision_point_rec(mouse_pos, c_btn)
                
                btn_c = dracula_purple if is_curr else (dracula_card if is_hvr else dracula_input)
                rl.draw_rectangle_rec(c_btn, btn_c)
                rl.draw_rectangle_lines_ex(c_btn, 1.5, dracula_border)
                
                txt_c = dracula_input if is_curr else (dracula_fg if is_hvr else dracula_muted)
                draw_text_clean(font, cat_lbl, bx + 15, by + 12, 18, txt_c)

                if is_hvr and rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT):
                    selected_type = cat_id
                    selected_name = cat_lbl
                    show_grid = False

        rl.end_drawing()

    if texture and texture.id > 0:
        rl.unload_texture(texture)
    if font and hasattr(font, 'base_size') and font.base_size > 0:
        rl.unload_font(font)
    rl.close_window()

    # Clean up temp PDF preview if created
    if is_temp_preview and os.path.exists(preview_img_path):
        try:
            os.remove(preview_img_path)
        except Exception:
            pass

    return action_result or {
        "action": "skipped",
        "docType": detected_type,
        "docTypeName": detected_name,
        "extractedName": current_extracted_name,
        "customKeyword": custom_keyword.strip()
    }

def main():
    parser = argparse.ArgumentParser(description="GoaOnAuto Raylib Human Confirmation GUI")
    parser.add_argument("--file", required=True, help="Path to target document file")
    parser.add_argument("--type", default="document", help="Detected document category ID")
    parser.add_argument("--name", default="General Document", help="Detected document type display name")
    parser.add_argument("--person", default="", help="Extracted applicant name")
    parser.add_argument("--confidence", type=float, default=0.9, help="Classification confidence score")

    args = parser.parse_args()

    result = run_confirmation_gui(
        file_path=args.file,
        detected_type=args.type,
        detected_name=args.name,
        extracted_name=args.person,
        confidence=args.confidence
    )

    # Output JSON result to stdout for TypeScript bridge
    print("JSON_RESULT:" + json.dumps(result))

if __name__ == "__main__":
    main()
