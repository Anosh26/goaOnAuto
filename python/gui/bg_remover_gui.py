"""
GoaOnAuto AI Background Removal & Photo Optimizer GUI (Raylib).
Single Responsibility: GPU-accelerated background removal, interactive target KB presets,
real-time percentage progress bar, and before/after photo inspection.
"""
from __future__ import annotations
import sys
import os
import time
import math
import tempfile
import threading
import subprocess
from PIL import Image
import pyray as rl

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from python.gui.core.colors import (
    DRACULA_BG, DRACULA_CURRENT_LINE, DRACULA_FG,
    DRACULA_COMMENT, DRACULA_CYAN, DRACULA_GREEN,
    DRACULA_ORANGE, DRACULA_PINK, DRACULA_PURPLE,
    DRACULA_RED, DRACULA_YELLOW
)
from python.gui.core.fonts import load_custom_font, draw_text_clean, measure_text_clean
from python.gui.core.dialogs import open_file_dialog
from python.gui.core.widgets import draw_button
from python.vision.ai_remove_bg import process_ai_background

PRESETS = [
    (30, "30 KB"),
    (50, "50 KB (Portal)"),
    (100, "100 KB"),
    (200, "200 KB"),
    (500, "500 KB"),
    (1000, "1 MB")
]

MODELS = [
    ("u2net_human_seg", "u2net_human_seg (Human Silhouette & Chest - Recommended)"),
    ("u2net", "u2net (General Object Model)"),
    ("u2netp", "u2netp (Lite Fast Model)")
]

class BgRemoverState:
    """Manages GUI state, texture handles, options, and async processing progress."""

    def __init__(self, input_path: str = ""):
        self.input_path = input_path
        self.output_path = ""
        self.target_kb = 50
        self.use_ai = True
        self.model_idx = 0
        self.crisp_edges = False
        self.downscale_50 = True

        # Slider / input state
        self.slider_dragging = False
        self.manual_kb_text = "50"
        self.is_kb_focused = False
        self.cursor_timer = 0.0

        # Processing & Progress State
        self.is_processing = False
        self.progress_pct = 0.0
        self.display_progress = 0.0
        self.status_msg = "Ready to process photo."
        self.status_color = DRACULA_COMMENT
        self.error_msg = ""
        self.final_size_kb = 0.0
        self.savings_pct = 0.0

        # Textures & Pending main-thread uploads
        self.orig_texture: rl.Texture | None = None
        self.proc_texture: rl.Texture | None = None
        self.orig_dims = (0, 0)
        self.orig_size_kb = 0.0
        self.proc_dims = (0, 0)
        initial_file = ""
        if input_path:
            if os.path.isfile(input_path):
                initial_file = os.path.abspath(input_path)
            elif os.path.isdir(input_path):
                import glob
                for pat in ["*passport_photo*", "*white_bg*", "*photo*", "*face*", "*.jpg", "*.jpeg", "*.png"]:
                    matches = glob.glob(os.path.join(input_path, pat))
                    candidates = [m for m in matches if os.path.isfile(m) and not m.endswith(("_declaration.pdf", "_declaration.tex"))]
                    if candidates:
                        initial_file = os.path.abspath(candidates[0])
                        break

        self.pending_input_path = initial_file
        self.pending_output_path = ""

        # Pulse timer for live animated indicators
        self.pulse_timer = 0.0

    def load_input_image(self, path_str: str) -> None:
        """Loads and pre-measures input photo."""
        self.input_path = os.path.abspath(path_str)
        self.output_path = ""
        self.final_size_kb = 0.0
        self.proc_dims = (0, 0)
        self.progress_pct = 0.0
        self.display_progress = 0.0
        self.status_msg = f"Loaded: {os.path.basename(self.input_path)}"
        self.status_color = DRACULA_CYAN
        self.error_msg = ""

        if self.proc_texture and self.proc_texture.id > 0:
            rl.unload_texture(self.proc_texture)
            self.proc_texture = None

        if self.orig_texture and self.orig_texture.id > 0:
            rl.unload_texture(self.orig_texture)
            self.orig_texture = None

        try:
            with Image.open(self.input_path) as img:
                self.orig_dims = img.size
            self.orig_size_kb = round(os.path.getsize(self.input_path) / 1024.0, 1)

            tex = rl.load_texture(self.input_path.encode('utf-8'))
            if tex and tex.id > 0:
                rl.set_texture_filter(tex, rl.TEXTURE_FILTER_BILINEAR)
                self.orig_texture = tex
        except Exception as e:
            self.status_msg = f"Error loading image: {e}"
            self.status_color = DRACULA_RED

    def load_output_image(self, path_str: str) -> None:
        """Loads processed output photo texture and metrics."""
        self.output_path = os.path.abspath(path_str)
        if self.proc_texture and self.proc_texture.id > 0:
            rl.unload_texture(self.proc_texture)
            self.proc_texture = None

        try:
            with Image.open(self.output_path) as img:
                self.proc_dims = img.size
            self.final_size_kb = round(os.path.getsize(self.output_path) / 1024.0, 1)
            if self.orig_size_kb > 0:
                self.savings_pct = max(0.0, round((1.0 - (self.final_size_kb / self.orig_size_kb)) * 100.0, 1))

            tex = rl.load_texture(self.output_path.encode('utf-8'))
            if tex and tex.id > 0:
                rl.set_texture_filter(tex, rl.TEXTURE_FILTER_BILINEAR)
                self.proc_texture = tex
        except Exception:
            pass

    def unload(self) -> None:
        """Frees all Raylib textures."""
        if self.orig_texture and self.orig_texture.id > 0:
            rl.unload_texture(self.orig_texture)
        if self.proc_texture and self.proc_texture.id > 0:
            rl.unload_texture(self.proc_texture)

def run_worker_thread(state: BgRemoverState) -> None:
    """Executes AI background removal & C JPEG compression in background."""
    try:
        input_file = state.input_path
        if not input_file or not os.path.isfile(input_file):
            raise FileNotFoundError("Valid input photo file required.")

        dir_name = os.path.dirname(input_file)
        stem = os.path.splitext(os.path.basename(input_file))[0]
        final_output = os.path.join(dir_name, f"{stem}_processed.jpg")
        temp_ai = os.path.join(tempfile.gettempdir(), f"ai_temp_{int(time.time())}_{stem}.png")

        current_input = input_file
        skip_c_bg = False

        # Phase 1: AI Background Removal
        if state.use_ai:
            state.progress_pct = 15.0
            state.status_msg = "Initializing RTX 4060 CUDA Execution Providers..."
            state.status_color = DRACULA_CYAN
            time.sleep(0.15)

            selected_model = MODELS[state.model_idx][0]
            state.progress_pct = 35.0
            state.status_msg = f"Loading ONNX Model ({selected_model}) in VRAM..."
            time.sleep(0.15)

            state.progress_pct = 55.0
            state.status_msg = "Segmenting Human Silhouette & Extracting Matte..."
            
            process_ai_background(
                input_path=input_file,
                output_path=temp_ai,
                model_name=selected_model,
                crisp_edges=state.crisp_edges,
                mask_threshold=128
            )

            state.progress_pct = 75.0
            state.status_msg = "Synthesizing Clean White Background..."
            time.sleep(0.1)

            if os.path.isfile(temp_ai):
                current_input = temp_ai
                skip_c_bg = True

        # Phase 2: C Fast Resizing & Iterative JPEG Compression
        state.progress_pct = 85.0
        state.status_msg = f"C Engine Fast JPEG Compression (Target ≤ {state.target_kb} KB)..."
        state.status_color = DRACULA_PURPLE

        bin_path = os.path.join(_PROJECT_ROOT, "bin", "process_image.exe")
        if not os.path.isfile(bin_path):
            raise FileNotFoundError(f"C Processor binary not found: {bin_path}")

        c_args = [bin_path, "--max-kb", str(int(state.target_kb))]
        if skip_c_bg:
            c_args.append("--skip-bg-remove")

        if not state.downscale_50:
            # Keep 100% original dimensions
            c_args.extend(["--width", str(state.orig_dims[0]), "--height", str(state.orig_dims[1])])

        c_args.extend([current_input, final_output])

        res = subprocess.run(c_args, capture_output=True, text=True)
        if res.returncode != 0 or not os.path.isfile(final_output):
            err_detail = res.stderr or res.stdout or "Compression failed"
            raise RuntimeError(f"C Engine error: {err_detail}")

        # Cleanup temp AI file
        if os.path.isfile(temp_ai):
            try:
                os.remove(temp_ai)
            except Exception:
                pass

        # Phase 3: Complete
        state.progress_pct = 100.0
        state.output_path = final_output
        state.pending_output_path = final_output
        final_bytes = os.path.getsize(final_output) if os.path.isfile(final_output) else 0
        state.final_size_kb = round(final_bytes / 1024.0, 1)
        if state.orig_size_kb > 0:
            state.savings_pct = max(0.0, round((1.0 - (state.final_size_kb / state.orig_size_kb)) * 100.0, 1))
        state.status_msg = f"✨ Photo Processed Successfully! Saved: {state.final_size_kb} KB"
        state.status_color = DRACULA_GREEN

    except Exception as err:
        state.progress_pct = 0.0
        state.error_msg = str(err)
        state.status_msg = f"Processing Failed: {str(err)}"
        state.status_color = DRACULA_RED
    finally:
        state.is_processing = False

def run_bg_remover_gui(input_path: str = "", max_test_frames: int = -1) -> None:
    """Main Raylib window runner for Background Removal GUI."""
    rl.set_config_flags(rl.FLAG_WINDOW_RESIZABLE | rl.FLAG_MSAA_4X_HINT | rl.FLAG_WINDOW_ALWAYS_RUN)
    win_w, win_h = 1080, 760
    rl.init_window(win_w, win_h, "GoaOnAuto - AI Background Removal & Photo Optimizer")
    rl.set_target_fps(60)

    try:
        rl.set_window_min_size(780, 600)
    except Exception:
        pass

    # Dynamic monitor centering
    try:
        mon = rl.get_current_monitor()
        mw, mh = rl.get_monitor_width(mon), rl.get_monitor_height(mon)
        if mw > 800 and mh > 600:
            rl.set_window_position((mw - win_w) // 2, max(20, (mh - win_h) // 2 - 20))
    except Exception:
        pass

    font_bold = load_custom_font("JetBrainsMono-Bold.ttf", 48)
    font_regular = load_custom_font("JetBrainsMono-Regular.ttf", 48)

    state = BgRemoverState(input_path)
    frames_rendered = 0

    while not rl.window_should_close():
        if max_test_frames > 0:
            frames_rendered += 1
            if frames_rendered >= max_test_frames:
                break

        dt = rl.get_frame_time()
        state.pulse_timer += dt * 3.0
        state.cursor_timer += dt

        # Drag-and-drop file loading support
        if rl.is_file_dropped():
            dropped = rl.load_dropped_files()
            if dropped.count > 0:
                first_file = rl.ffi.string(dropped.paths[0]).decode('utf-8', errors='ignore')
                if os.path.isfile(first_file):
                    state.load_input_image(first_file)
                elif os.path.isdir(first_file):
                    import glob
                    for pat in ["*passport_photo*", "*white_bg*", "*photo*", "*face*", "*.jpg", "*.jpeg", "*.png"]:
                        matches = glob.glob(os.path.join(first_file, pat))
                        candidates = [m for m in matches if os.path.isfile(m) and not m.endswith(("_declaration.pdf", "_declaration.tex"))]
                        if candidates:
                            state.load_input_image(candidates[0])
                            break
            rl.unload_dropped_files(dropped)

        # Safely upload pending textures on main thread where OpenGL context lives
        if state.pending_input_path:
            path_to_load = state.pending_input_path
            state.pending_input_path = ""
            state.load_input_image(path_to_load)

        if state.pending_output_path:
            path_to_load = state.pending_output_path
            state.pending_output_path = ""
            state.load_output_image(path_to_load)

        # Smooth progress interpolation
        state.display_progress += (state.progress_pct - state.display_progress) * min(1.0, dt * 10.0)

        w = rl.get_screen_width()
        h = rl.get_screen_height()
        mouse_pos = rl.get_mouse_position()
        is_mouse_down = rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT)

        # Handle keyboard input when target KB box is focused
        if state.is_kb_focused and not state.is_processing:
            if rl.is_key_pressed(rl.KEY_BACKSPACE) and len(state.manual_kb_text) > 0:
                state.manual_kb_text = state.manual_kb_text[:-1]
                if state.manual_kb_text.isdigit():
                    state.target_kb = max(10, min(2000, int(state.manual_kb_text)))

            char_code = rl.get_char_pressed()
            while char_code > 0:
                if 48 <= char_code <= 57 and len(state.manual_kb_text) < 4:  # digits 0-9
                    state.manual_kb_text += chr(char_code)
                    if state.manual_kb_text.isdigit():
                        state.target_kb = max(10, min(2000, int(state.manual_kb_text)))
                char_code = rl.get_char_pressed()

        rl.begin_drawing()
        rl.clear_background(DRACULA_BG)

        # -------------------------------------------------------------
        # 1. Header Bar
        # -------------------------------------------------------------
        header_h = 56
        rl.draw_rectangle(0, 0, w, header_h, DRACULA_CURRENT_LINE)
        rl.draw_line(0, header_h, w, header_h, DRACULA_COMMENT)

        draw_text_clean(font_bold, "⚡ GoaOnAuto AI Photo Optimizer", 20, 16, 18, DRACULA_PURPLE)

        # Hardware Badge right-aligned
        badge_str = "RTX 4060 CUDA Active | 50 KB Portal Ready"
        draw_text_clean(font_regular, badge_str, w - 360, 18, 13, DRACULA_CYAN)

        # -------------------------------------------------------------
        # 2. Main Content Split (Left = Dual Previews, Right = Controls & Presets)
        # -------------------------------------------------------------
        content_y = header_h + 12
        footer_h = 56
        content_h = h - content_y - footer_h

        preview_col_w = int(w * 0.44)
        ctrl_x = preview_col_w + 20
        ctrl_w = w - ctrl_x - 20

        # --- A. DUAL PREVIEW CARDS (Original vs Processed) ---
        preview_box_h = int((content_h - 20) / 2)

        # Card 1: Original Image
        orig_box = rl.Rectangle(20, content_y, preview_col_w, preview_box_h)
        rl.draw_rectangle_rounded(orig_box, 0.04, 6, DRACULA_CURRENT_LINE)
        rl.draw_rectangle_rounded_lines(orig_box, 0.04, 6, DRACULA_COMMENT)

        orig_title = "📷 Original Input Photo"
        if state.orig_dims[0] > 0:
            orig_title += f" ({state.orig_dims[0]}x{state.orig_dims[1]} | {state.orig_size_kb} KB)"
        draw_text_clean(font_bold, orig_title, orig_box.x + 12, orig_box.y + 10, 13, DRACULA_FG)

        # Pick photo button
        pick_btn_rect = rl.Rectangle(orig_box.x + orig_box.width - 95, orig_box.y + 6, 85, 26)
        if draw_button("Browse...", pick_btn_rect, DRACULA_BG, DRACULA_CYAN, font_bold, 11, mouse_pos, is_mouse_down):
            picked = open_file_dialog("Select Image to Process")
            if picked:
                state.load_input_image(picked)

        if state.orig_texture and state.orig_texture.id > 0:
            # Fit texture with preserved aspect ratio
            img_area_rect = rl.Rectangle(orig_box.x + 10, orig_box.y + 36, orig_box.width - 20, orig_box.height - 46)
            tw, th = state.orig_texture.width, state.orig_texture.height
            aspect = tw / float(th) if th > 0 else 1.0
            
            fit_w = img_area_rect.width
            fit_h = fit_w / aspect
            if fit_h > img_area_rect.height:
                fit_h = img_area_rect.height
                fit_w = fit_h * aspect

            draw_x = img_area_rect.x + (img_area_rect.width - fit_w) / 2
            draw_y = img_area_rect.y + (img_area_rect.height - fit_h) / 2
            rl.draw_texture_pro(
                state.orig_texture,
                rl.Rectangle(0, 0, tw, th),
                rl.Rectangle(draw_x, draw_y, fit_w, fit_h),
                rl.Vector2(0, 0),
                0.0,
                rl.WHITE
            )
        else:
            msg = "No image loaded.\nClick Browse to select photo."
            draw_text_clean(font_regular, msg, orig_box.x + 30, orig_box.y + orig_box.height / 2 - 15, 13, DRACULA_COMMENT)

        # Card 2: Processed Output Image
        proc_box = rl.Rectangle(20, content_y + preview_box_h + 12, preview_col_w, preview_box_h)
        rl.draw_rectangle_rounded(proc_box, 0.04, 6, DRACULA_CURRENT_LINE)
        rl.draw_rectangle_rounded_lines(proc_box, 0.04, 6, DRACULA_COMMENT)

        proc_title = "✨ Processed White-BG Photo"
        if state.proc_dims[0] > 0:
            proc_title += f" ({state.proc_dims[0]}x{state.proc_dims[1]} | {state.final_size_kb} KB)"
        draw_text_clean(font_bold, proc_title, proc_box.x + 12, proc_box.y + 10, 13, DRACULA_GREEN)

        if state.proc_texture and state.proc_texture.id > 0:
            img_area_rect = rl.Rectangle(proc_box.x + 10, proc_box.y + 36, proc_box.width - 20, proc_box.height - 46)
            tw, th = state.proc_texture.width, state.proc_texture.height
            aspect = tw / float(th) if th > 0 else 1.0

            fit_w = img_area_rect.width
            fit_h = fit_w / aspect
            if fit_h > img_area_rect.height:
                fit_h = img_area_rect.height
                fit_w = fit_h * aspect

            draw_x = img_area_rect.x + (img_area_rect.width - fit_w) / 2
            draw_y = img_area_rect.y + (img_area_rect.height - fit_h) / 2
            rl.draw_texture_pro(
                state.proc_texture,
                rl.Rectangle(0, 0, tw, th),
                rl.Rectangle(draw_x, draw_y, fit_w, fit_h),
                rl.Vector2(0, 0),
                0.0,
                rl.WHITE
            )
        else:
            hint = "Processed white-background preview\nwill appear here once generated."
            draw_text_clean(font_regular, hint, proc_box.x + 30, proc_box.y + proc_box.height / 2 - 15, 13, DRACULA_COMMENT)

        # --- B. CONTROLS & SETTINGS PANEL ---
        curr_ctrl_y = content_y

        # Group 1: Target File Size & Radio Presets
        size_grp_h = 135
        size_grp = rl.Rectangle(ctrl_x, curr_ctrl_y, ctrl_w, size_grp_h)
        rl.draw_rectangle_rounded(size_grp, 0.04, 6, DRACULA_CURRENT_LINE)
        rl.draw_rectangle_rounded_lines(size_grp, 0.04, 6, DRACULA_COMMENT)

        draw_text_clean(font_bold, "🎯 Target Maximum File Size (KB Presets)", ctrl_x + 16, curr_ctrl_y + 12, 14, DRACULA_YELLOW)

        # Radio Preset Buttons Row (FIXED BUG: Exactly one preset is highlighted at a time!)
        preset_btn_w = int((ctrl_w - 40) / len(PRESETS))
        preset_y = curr_ctrl_y + 38

        for idx, (kb_val, label) in enumerate(PRESETS):
            btn_x = ctrl_x + 16 + (idx * preset_btn_w)
            p_rect = rl.Rectangle(btn_x, preset_y, preset_btn_w - 6, 32)

            is_active = (state.target_kb == kb_val)
            p_bg = DRACULA_PURPLE if is_active else DRACULA_BG
            p_fg = DRACULA_BG if is_active else DRACULA_FG

            if draw_button(label, p_rect, p_bg, p_fg, font_bold, 11, mouse_pos, is_mouse_down):
                state.target_kb = kb_val
                state.manual_kb_text = str(kb_val)

        # Interactive Slider + Manual Number Box
        slider_y = preset_y + 44
        slider_track_w = ctrl_w - 150
        slider_rect = rl.Rectangle(ctrl_x + 16, slider_y + 10, slider_track_w, 12)

        # Track bar
        rl.draw_rectangle_rounded(slider_rect, 0.5, 4, DRACULA_BG)
        rl.draw_rectangle_rounded_lines(slider_rect, 0.5, 4, DRACULA_COMMENT)

        # Slider Thumb
        slider_pct = max(0.0, min(1.0, (state.target_kb - 10) / (2000 - 10)))
        thumb_x = slider_rect.x + (slider_pct * slider_rect.width)
        thumb_rect = rl.Rectangle(thumb_x - 7, slider_rect.y - 4, 14, 20)
        rl.draw_rectangle_rounded(thumb_rect, 0.4, 4, DRACULA_CYAN)

        if rl.is_mouse_button_down(rl.MOUSE_BUTTON_LEFT) and rl.check_collision_point_rec(mouse_pos, rl.Rectangle(slider_rect.x - 10, slider_rect.y - 10, slider_rect.width + 20, 32)):
            rel_x = max(0.0, min(1.0, (mouse_pos.x - slider_rect.x) / slider_rect.width))
            state.target_kb = int(10 + rel_x * 1990)
            state.manual_kb_text = str(state.target_kb)

        # Number input box
        num_box_rect = rl.Rectangle(ctrl_x + 24 + slider_track_w, slider_y, 70, 32)
        if is_mouse_down:
            state.is_kb_focused = rl.check_collision_point_rec(mouse_pos, num_box_rect)

        box_border = DRACULA_CYAN if state.is_kb_focused else DRACULA_COMMENT
        rl.draw_rectangle_rounded(num_box_rect, 0.25, 4, DRACULA_BG)
        rl.draw_rectangle_rounded_lines(num_box_rect, 0.25, 4, box_border)
        draw_text_clean(font_bold, state.manual_kb_text, num_box_rect.x + 8, num_box_rect.y + 8, 14, DRACULA_CYAN)

        # Blinking cursor in input box
        if state.is_kb_focused and (int(state.cursor_timer * 2.5) % 2 == 0):
            cur_x = num_box_rect.x + 8 + measure_text_clean(font_bold, state.manual_kb_text, 14) + 2
            rl.draw_line(int(cur_x), int(num_box_rect.y + 6), int(cur_x), int(num_box_rect.y + 26), DRACULA_CYAN)

        draw_text_clean(font_bold, "KB", num_box_rect.x + num_box_rect.width + 6, num_box_rect.y + 8, 13, DRACULA_FG)

        curr_ctrl_y += size_grp_h + 12

        # Group 2: AI Neural Segmentation & Model Options
        ai_grp_h = 160
        ai_grp = rl.Rectangle(ctrl_x, curr_ctrl_y, ctrl_w, ai_grp_h)
        rl.draw_rectangle_rounded(ai_grp, 0.04, 6, DRACULA_CURRENT_LINE)
        rl.draw_rectangle_rounded_lines(ai_grp, 0.04, 6, DRACULA_COMMENT)

        draw_text_clean(font_bold, "🧠 AI Human & Silhouette Segmentation (NVIDIA CUDA)", ctrl_x + 16, curr_ctrl_y + 12, 14, DRACULA_PURPLE)

        # Toggle 1: Use AI Checkbox
        chk_rect = rl.Rectangle(ctrl_x + 16, curr_ctrl_y + 38, 20, 20)
        rl.draw_rectangle_rounded(chk_rect, 0.2, 4, DRACULA_BG)
        rl.draw_rectangle_rounded_lines(chk_rect, 0.2, 4, DRACULA_CYAN if state.use_ai else DRACULA_COMMENT)
        if state.use_ai:
            rl.draw_rectangle_rounded(rl.Rectangle(chk_rect.x + 4, chk_rect.y + 4, 12, 12), 0.2, 4, DRACULA_GREEN)

        draw_text_clean(font_regular, "Enable AI Human Background Removal (RTX 4060 GPU)", ctrl_x + 44, curr_ctrl_y + 40, 13, DRACULA_FG)
        if is_mouse_down and rl.check_collision_point_rec(mouse_pos, rl.Rectangle(ctrl_x + 16, curr_ctrl_y + 36, 400, 24)):
            state.use_ai = not state.use_ai

        # Model Selector Pills
        draw_text_clean(font_bold, "Model:", ctrl_x + 16, curr_ctrl_y + 70, 13, DRACULA_COMMENT)
        model_pill_w = int((ctrl_w - 90) / 3)
        for m_idx, (m_code, m_desc) in enumerate(MODELS):
            m_rect = rl.Rectangle(ctrl_x + 75 + (m_idx * model_pill_w), curr_ctrl_y + 66, model_pill_w - 6, 28)
            is_m_active = (state.model_idx == m_idx)
            m_bg = DRACULA_CYAN if is_m_active else DRACULA_BG
            m_fg = DRACULA_BG if is_m_active else DRACULA_FG
            if draw_button(m_code, m_rect, m_bg, m_fg, font_bold, 11, mouse_pos, is_mouse_down):
                state.model_idx = m_idx

        # Toggle 2: Resolution (50% Portal Downscale vs 100% Original)
        draw_text_clean(font_bold, "Resolution:", ctrl_x + 16, curr_ctrl_y + 112, 13, DRACULA_COMMENT)
        btn50_rect = rl.Rectangle(ctrl_x + 115, curr_ctrl_y + 106, 175, 28)
        btn100_rect = rl.Rectangle(ctrl_x + 300, curr_ctrl_y + 106, 160, 28)

        bg50 = DRACULA_GREEN if state.downscale_50 else DRACULA_BG
        fg50 = DRACULA_BG if state.downscale_50 else DRACULA_FG
        if draw_button("50% Downscale (Portal)", btn50_rect, bg50, fg50, font_bold, 11, mouse_pos, is_mouse_down):
            state.downscale_50 = True

        bg100 = DRACULA_GREEN if not state.downscale_50 else DRACULA_BG
        fg100 = DRACULA_BG if not state.downscale_50 else DRACULA_FG
        if draw_button("100% Original", btn100_rect, bg100, fg100, font_bold, 11, mouse_pos, is_mouse_down):
            state.downscale_50 = False

        curr_ctrl_y += ai_grp_h + 16

        # Group 3: Real-Time Dynamic Progress Bar & Execution
        prog_grp_h = content_h - (curr_ctrl_y - content_y)
        prog_grp = rl.Rectangle(ctrl_x, curr_ctrl_y, ctrl_w, prog_grp_h)
        rl.draw_rectangle_rounded(prog_grp, 0.04, 6, DRACULA_CURRENT_LINE)
        rl.draw_rectangle_rounded_lines(prog_grp, 0.04, 6, DRACULA_COMMENT)

        # Progress Section Header with Live Activity Pulse
        draw_text_clean(font_bold, "📊 Processing Pipeline Progress", ctrl_x + 16, curr_ctrl_y + 14, 14, DRACULA_CYAN)

        if state.is_processing:
            pulse_alpha = int(180 + 75 * abs(math.sin(state.pulse_timer)))
            rl.draw_circle(ctrl_x + ctrl_w - 24, curr_ctrl_y + 22, 6, rl.Color(80, 250, 123, pulse_alpha))

        # Real-time Progress Bar Track
        pbar_x = ctrl_x + 16
        pbar_y = curr_ctrl_y + 44
        pbar_w = ctrl_w - 32
        pbar_h = 28

        rl.draw_rectangle_rounded(rl.Rectangle(pbar_x, pbar_y, pbar_w, pbar_h), 0.35, 6, DRACULA_BG)
        rl.draw_rectangle_rounded_lines(rl.Rectangle(pbar_x, pbar_y, pbar_w, pbar_h), 0.35, 6, DRACULA_COMMENT)

        # Animated Fill Bar
        clamped_pct = max(0.0, min(100.0, state.display_progress))
        fill_w = (pbar_w - 4) * (clamped_pct / 100.0)

        if fill_w > 4:
            fill_color = DRACULA_GREEN if clamped_pct >= 99.0 else DRACULA_CYAN
            rl.draw_rectangle_rounded(rl.Rectangle(pbar_x + 2, pbar_y + 2, fill_w, pbar_h - 4), 0.35, 6, fill_color)

        # Progress Percentage Text (High Contrast & Legible)
        pct_label = f"{int(clamped_pct)}%"
        pct_x = pbar_x + (pbar_w - measure_text_clean(font_bold, pct_label, 14)) / 2
        pct_fg = DRACULA_BG if fill_w > (pbar_w / 2) else DRACULA_FG
        draw_text_clean(font_bold, pct_label, pct_x, pbar_y + 6, 14, pct_fg)

        # Progress Status / Phase details
        draw_text_clean(font_regular, f"Step: {state.status_msg}", ctrl_x + 18, pbar_y + 36, 13, state.status_color)

        # Primary Action Button: "⚡ Process Photo"
        action_btn_w = 210
        action_btn_h = 44
        action_btn_x = ctrl_x + 16
        action_btn_y = curr_ctrl_y + prog_grp_h - action_btn_h - 14
        action_rect = rl.Rectangle(action_btn_x, action_btn_y, action_btn_w, action_btn_h)

        btn_label = "⚡ Processing..." if state.is_processing else "⚡ PROCESS PHOTO"
        btn_bg = DRACULA_COMMENT if state.is_processing else DRACULA_PURPLE
        btn_fg = DRACULA_FG if state.is_processing else DRACULA_BG

        if not state.is_processing:
            if draw_button(btn_label, action_rect, btn_bg, btn_fg, font_bold, 13, mouse_pos, is_mouse_down):
                if state.input_path and os.path.isfile(state.input_path):
                    state.is_processing = True
                    state.progress_pct = 5.0
                    state.status_msg = "Starting pipeline..."
                    state.error_msg = ""
                    t = threading.Thread(target=run_worker_thread, args=(state,), daemon=True)
                    t.start()
                else:
                    state.status_msg = "Please select a photo first via Browse button."
                    state.status_color = DRACULA_ORANGE
        else:
            rl.draw_rectangle_rounded(action_rect, 0.3, 6, btn_bg)
            draw_text_clean(font_bold, btn_label, action_btn_x + 30, action_btn_y + 14, 13, btn_fg)

        # "Open Output" Button (Active when processed)
        if state.output_path and os.path.isfile(state.output_path):
            open_btn_rect = rl.Rectangle(action_btn_x + action_btn_w + 14, action_btn_y, 140, action_btn_h)
            if draw_button("📂 View Photo", open_btn_rect, DRACULA_GREEN, DRACULA_BG, font_bold, 13, mouse_pos, is_mouse_down):
                try:
                    os.startfile(state.output_path)
                except Exception:
                    pass

            folder_btn_rect = rl.Rectangle(open_btn_rect.x + open_btn_rect.width + 12, action_btn_y, 135, action_btn_h)
            if draw_button("📁 Open Folder", folder_btn_rect, DRACULA_CURRENT_LINE, DRACULA_CYAN, font_bold, 13, mouse_pos, is_mouse_down):
                try:
                    subprocess.run(["explorer", "/select,", state.output_path])
                except Exception:
                    pass

        # -------------------------------------------------------------
        # 3. Bottom Status Bar
        # -------------------------------------------------------------
        footer_y = h - footer_h
        rl.draw_rectangle(0, footer_y, w, footer_h, DRACULA_CURRENT_LINE)
        rl.draw_line(0, footer_y, w, footer_y, DRACULA_COMMENT)

        draw_text_clean(font_bold, "Status:", 20, footer_y + 18, 13, DRACULA_COMMENT)
        disp_status = state.status_msg
        if len(disp_status) > 85:
            disp_status = disp_status[:82] + "..."
        draw_text_clean(font_bold, disp_status, 85, footer_y + 18, 13, state.status_color)

        if state.final_size_kb > 0:
            result_tag = f"Size: {state.final_size_kb} KB ({state.savings_pct}% reduced)"
            draw_text_clean(font_bold, result_tag, w - 260, footer_y + 18, 13, DRACULA_GREEN)

        rl.end_drawing()

    state.unload()
    rl.close_window()

def main():
    target_path = ""
    max_test_frames = -1
    for arg in sys.argv[1:]:
        if arg.startswith("--test-frames="):
            try:
                max_test_frames = int(arg.split("=")[1])
            except Exception:
                pass
        elif not arg.startswith("--") and not target_path:
            target_path = arg

    run_bg_remover_gui(target_path, max_test_frames=max_test_frames)

if __name__ == "__main__":
    main()
