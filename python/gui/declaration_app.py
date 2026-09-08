"""
GoaOnAuto Modular Declaration GUI Application (The General Window).
Single Responsibility: Hosts the Raylib application window, responsive scaling layout,
keyboard/mouse event dispatching, and renders the active declaration module.
"""
from __future__ import annotations
import sys
import os
import argparse
import subprocess
from datetime import datetime
import pyray as rl

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    from .core.colors import (
        DRACULA_BG, DRACULA_CURRENT_LINE, DRACULA_FG,
        DRACULA_COMMENT, DRACULA_CYAN, DRACULA_GREEN,
        DRACULA_ORANGE, DRACULA_PINK, DRACULA_PURPLE,
        DRACULA_RED, DRACULA_YELLOW
    )
    from .core.fonts import load_custom_font, draw_text_clean, measure_text_clean
    from .core.dialogs import open_file_dialog
    from .core.latex_compiler import compile_latex_to_pdf
    from .core.widgets import draw_button, draw_input_row, draw_image_preview_card
    from .declarations import get_declaration, BaseDeclaration
except (ImportError, ValueError):
    from python.gui.core.colors import (
        DRACULA_BG, DRACULA_CURRENT_LINE, DRACULA_FG,
        DRACULA_COMMENT, DRACULA_CYAN, DRACULA_GREEN,
        DRACULA_ORANGE, DRACULA_PINK, DRACULA_PURPLE,
        DRACULA_RED, DRACULA_YELLOW
    )
    from python.gui.core.fonts import load_custom_font, draw_text_clean, measure_text_clean
    from python.gui.core.dialogs import open_file_dialog
    from python.gui.core.latex_compiler import compile_latex_to_pdf
    from python.gui.core.widgets import draw_button, draw_input_row, draw_image_preview_card
    from python.gui.declarations import get_declaration, BaseDeclaration

class DeclarationAppState:
    """Manages application-level UI state for the General Window."""

    def __init__(self, declaration: BaseDeclaration):
        self.declaration = declaration
        self.active_field_idx = 0
        self.status_msg = f"Ready to customize and generate {declaration.declaration_id.upper()} declaration"
        self.status_color = DRACULA_CYAN
        self.cursor_timer = 0.0
        self.tex_dirty = True
        self.last_sync_time = "Not synced yet"
        self.is_compiled = False
        self.compiled_pdf = ""

        # Raylib Texture handles
        self.photo_texture: rl.Texture | None = None
        self.sig_texture: rl.Texture | None = None
        self.last_photo_path = ""
        self.last_sig_path = ""

    def update_textures(self) -> None:
        """Loads or refreshes photo and signature textures when file paths change."""
        current_photo = self.declaration.get_field_val("photo_path")
        if current_photo != self.last_photo_path:
            if self.photo_texture and self.photo_texture.id > 0:
                rl.unload_texture(self.photo_texture)
                self.photo_texture = None
            if current_photo and os.path.isfile(current_photo):
                try:
                    self.photo_texture = rl.load_texture(current_photo.encode('utf-8'))
                    if self.photo_texture and self.photo_texture.id > 0:
                        rl.set_texture_filter(self.photo_texture, rl.TEXTURE_FILTER_BILINEAR)
                except Exception:
                    self.photo_texture = None
            self.last_photo_path = current_photo

        current_sig = self.declaration.get_field_val("sig_path")
        if current_sig != self.last_sig_path:
            if self.sig_texture and self.sig_texture.id > 0:
                rl.unload_texture(self.sig_texture)
                self.sig_texture = None
            if current_sig and os.path.isfile(current_sig):
                try:
                    self.sig_texture = rl.load_texture(current_sig.encode('utf-8'))
                    if self.sig_texture and self.sig_texture.id > 0:
                        rl.set_texture_filter(self.sig_texture, rl.TEXTURE_FILTER_BILINEAR)
                except Exception:
                    self.sig_texture = None
            self.last_sig_path = current_sig

    def sync_tex(self) -> tuple[bool, str, str]:
        """Triggers LaTeX generation on active declaration."""
        ok, tex_path, err = self.declaration.generate_tex()
        if ok:
            self.last_sync_time = datetime.now().strftime("%H:%M:%S")
            self.tex_dirty = False
        return ok, tex_path, err

    def compile_pdf(self) -> tuple[bool, str]:
        """Generates TeX and invokes pdflatex compiler."""
        ok, tex_path, err = self.sync_tex()
        if not ok:
            return False, f"TeX generation failed: {err}"

        success, pdf_or_err = compile_latex_to_pdf(tex_path, self.declaration.target_dir)
        if success:
            self.is_compiled = True
            self.compiled_pdf = pdf_or_err
            self.declaration.save_data()
        return success, pdf_or_err

    def unload(self) -> None:
        """Frees GPU textures on exit."""
        if self.photo_texture and self.photo_texture.id > 0:
            rl.unload_texture(self.photo_texture)
        if self.sig_texture and self.sig_texture.id > 0:
            rl.unload_texture(self.sig_texture)

def run_app(declaration_type: str = "residence", target_dir: str = "", no_prompt: bool = False) -> None:
    """Entrypoint for the General Declaration Raylib Window."""
    declaration = get_declaration(declaration_type, target_dir)
    app_state = DeclarationAppState(declaration)

    # Initial TeX sync so file exists immediately on startup
    app_state.sync_tex()

    rl.set_config_flags(rl.FLAG_WINDOW_RESIZABLE | rl.FLAG_MSAA_4X_HINT | rl.FLAG_WINDOW_ALWAYS_RUN)
    init_w, init_h = 1260, 820
    rl.init_window(init_w, init_h, f"GoaOnAuto - {declaration.title}")
    rl.set_target_fps(60)

    # Dynamic monitor fitting
    try:
        mon = rl.get_current_monitor()
        mon_w, mon_h = rl.get_monitor_width(mon), rl.get_monitor_height(mon)
        if mon_w > 900 and mon_h > 700:
            target_w = min(1380, mon_w - 60)
            target_h = min(900, mon_h - 80)
            rl.set_window_size(target_w, target_h)
            rl.set_window_position((mon_w - target_w) // 2, max(20, (mon_h - target_h) // 2 - 20))
    except Exception:
        pass

    # Prompt if photo path is missing on launch
    if not no_prompt:
        current_photo = declaration.get_field_val("photo_path")
        if not current_photo or not os.path.isfile(current_photo):
            picked_photo = open_file_dialog("Photo not found. Please select Passport Photo (.jpg, .png):")
            if picked_photo:
                declaration.set_field_val("photo_path", picked_photo)
                app_state.tex_dirty = True

    font_bold = load_custom_font("JetBrainsMono-Bold.ttf", 48)
    font_regular = load_custom_font("JetBrainsMono-Regular.ttf", 48)

    while not rl.window_should_close():
        dt = rl.get_frame_time()
        app_state.cursor_timer += dt

        # Auto-sync TeX if dirty
        if app_state.tex_dirty:
            app_state.sync_tex()

        app_state.update_textures()

        # Layout Dimensions
        w = rl.get_screen_width()
        h = rl.get_screen_height()
        scale = max(0.75, min(1.6, w / 1260.0))
        scale_y = max(0.75, min(1.5, h / 820.0))

        title_size = max(14, int(19 * scale))
        label_size = max(11, int(13 * scale))
        input_size = max(11, int(13 * scale))
        btn_size = max(11, int(13 * scale))

        mouse_pos = rl.get_mouse_position()
        is_mouse_down = rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT)

        visible_fields = declaration.get_visible_fields()
        if app_state.active_field_idx >= len(visible_fields):
            app_state.active_field_idx = 0
        active_f = visible_fields[app_state.active_field_idx] if visible_fields else None

        # Keyboard Navigation: Tab / Shift+Tab
        if rl.is_key_pressed(rl.KEY_TAB):
            if rl.is_key_down(rl.KEY_LEFT_SHIFT) or rl.is_key_down(rl.KEY_RIGHT_SHIFT):
                app_state.active_field_idx = (app_state.active_field_idx - 1) % len(visible_fields)
            else:
                app_state.active_field_idx = (app_state.active_field_idx + 1) % len(visible_fields)

        # Text input & Backspace
        if active_f:
            if rl.is_key_pressed(rl.KEY_BACKSPACE) or (rl.is_key_down(rl.KEY_BACKSPACE) and app_state.cursor_timer > 0.4):
                if len(active_f.value) > 0:
                    active_f.value = active_f.value[:-1]
                    app_state.tex_dirty = True
                    if rl.is_key_down(rl.KEY_BACKSPACE):
                        app_state.cursor_timer = 0.35

            if (rl.is_key_down(rl.KEY_LEFT_CONTROL) or rl.is_key_down(rl.KEY_RIGHT_CONTROL)) and rl.is_key_pressed(rl.KEY_V):
                try:
                    import tkinter as tk
                    root = tk.Tk()
                    root.withdraw()
                    clipboard = root.clipboard_get()
                    root.destroy()
                    if clipboard:
                        active_f.value += clipboard.replace("\n", " ").replace("\r", "")
                        app_state.tex_dirty = True
                except Exception:
                    pass

            char_code = rl.get_char_pressed()
            while char_code > 0:
                if 32 <= char_code <= 126:
                    active_f.value += chr(char_code)
                    app_state.tex_dirty = True
                char_code = rl.get_char_pressed()

        # Render Frame
        rl.begin_drawing()
        rl.clear_background(DRACULA_BG)

        # 1. Header Bar
        header_h = int(54 * scale_y)
        rl.draw_rectangle(0, 0, w, header_h, DRACULA_CURRENT_LINE)
        rl.draw_line(0, header_h, w, header_h, DRACULA_COMMENT)

        draw_text_clean(font_bold, declaration.title, 24 * scale, 15 * scale_y, title_size, DRACULA_PURPLE)

        # Mode Selector Buttons (if declaration supports multiple modes, e.g. Self/Child)
        if len(declaration.supported_modes) > 1:
            mode_btn_w = int(145 * scale)
            mode_btn_h = int(32 * scale_y)
            self_btn_x = w - (mode_btn_w * 2) - int(30 * scale)
            child_btn_x = w - mode_btn_w - int(20 * scale)
            btn_y = int(11 * scale_y)

            self_rect = rl.Rectangle(self_btn_x, btn_y, mode_btn_w, mode_btn_h)
            child_rect = rl.Rectangle(child_btn_x, btn_y, mode_btn_w, mode_btn_h)

            self_bg = DRACULA_PURPLE if declaration.mode == "self" else DRACULA_BG
            self_fg = DRACULA_BG if declaration.mode == "self" else DRACULA_FG
            if draw_button("Self Mode", self_rect, self_bg, self_fg, font_bold, btn_size, mouse_pos, is_mouse_down):
                if declaration.mode != "self":
                    declaration.mode = "self"
                    app_state.tex_dirty = True
                    app_state.status_msg = f"Switched to Self Declaration Mode"
                    app_state.status_color = DRACULA_CYAN

            child_bg = DRACULA_YELLOW if declaration.mode == "child" else DRACULA_BG
            child_fg = DRACULA_BG if declaration.mode == "child" else DRACULA_FG
            if draw_button("Child Mode", child_rect, child_bg, child_fg, font_bold, btn_size, mouse_pos, is_mouse_down):
                if declaration.mode != "child":
                    declaration.mode = "child"
                    app_state.tex_dirty = True
                    app_state.status_msg = f"Switched to Child Declaration Mode"
                    app_state.status_color = DRACULA_YELLOW

        # 2. Main Layout Split (Left = Form, Right = Live Asset Preview & Actions)
        left_w = int(w * 0.61)
        right_x = left_w + int(20 * scale)
        right_w = w - right_x - int(20 * scale)
        content_y = header_h + int(14 * scale_y)
        footer_h = int(60 * scale_y)
        available_h = h - content_y - footer_h

        num_fields = len(visible_fields)
        row_h = min(int(52 * scale_y), max(int(36 * scale_y), int(available_h / (num_fields + 0.2))))
        inp_h = max(26, int(row_h * 0.74))

        # Render Form Rows
        for i, field in enumerate(visible_fields):
            curr_y = content_y + (i * row_h)
            lbl_x = int(24 * scale)
            lbl_w = int(210 * scale)
            inp_x = lbl_x + lbl_w + int(10 * scale)

            browse_btn_w = int(74 * scale) if field.is_path else 0
            inp_w = left_w - inp_x - (browse_btn_w + int(12 * scale) if field.is_path else 0)

            clicked_box, val_changed = draw_input_row(
                field=field,
                is_focused=(active_f == field),
                lbl_x=lbl_x,
                lbl_w=lbl_w,
                inp_x=inp_x,
                inp_w=inp_w,
                curr_y=curr_y,
                inp_h=inp_h,
                scale=scale,
                scale_y=scale_y,
                label_size=label_size,
                input_size=input_size,
                font_bold=font_bold,
                font_regular=font_regular,
                mouse_pos=mouse_pos,
                is_mouse_down=is_mouse_down,
                cursor_timer=app_state.cursor_timer
            )

            if clicked_box:
                app_state.active_field_idx = i
            if val_changed:
                app_state.tex_dirty = True

        # 3. Right Column: Document Previews & Generation Actions
        preview_box_rect = rl.Rectangle(right_x, content_y, right_w, available_h)
        rl.draw_rectangle_rounded(preview_box_rect, 0.05, 8, DRACULA_CURRENT_LINE)
        rl.draw_rectangle_rounded_lines(preview_box_rect, 0.05, 8, DRACULA_COMMENT)

        draw_text_clean(font_bold, "📄 Live Preview & Document Assets", right_x + int(16 * scale), content_y + int(14 * scale_y), int(16 * scale), DRACULA_CYAN)

        # Photo Preview Card
        photo_box_w = int(140 * scale)
        photo_box_h = int(175 * scale_y)
        photo_box_x = right_x + int(20 * scale)
        photo_box_y = content_y + int(46 * scale_y)
        photo_rect = rl.Rectangle(photo_box_x, photo_box_y, photo_box_w, photo_box_h)

        if draw_image_preview_card(
            title="Passport Photo",
            texture=app_state.photo_texture,
            rect=photo_rect,
            scale=scale,
            scale_y=scale_y,
            font_bold=font_bold,
            font_regular=font_regular,
            mouse_pos=mouse_pos,
            is_mouse_down=is_mouse_down,
            missing_msg="⚠️ Photo Missing\nClick to Browse"
        ):
            picked = open_file_dialog("Select Passport Photo for Applicant")
            if picked:
                declaration.set_field_val("photo_path", picked)
                app_state.tex_dirty = True

        # Signature Preview Card
        sig_box_w = right_w - photo_box_w - int(50 * scale)
        sig_box_h = int(105 * scale_y)
        sig_box_x = photo_box_x + photo_box_w + int(20 * scale)
        sig_box_y = photo_box_y + int(30 * scale_y)
        sig_rect = rl.Rectangle(sig_box_x, sig_box_y, sig_box_w, sig_box_h)

        if draw_image_preview_card(
            title="Signature Asset",
            texture=app_state.sig_texture,
            rect=sig_rect,
            scale=scale,
            scale_y=scale_y,
            font_bold=font_bold,
            font_regular=font_regular,
            mouse_pos=mouse_pos,
            is_mouse_down=is_mouse_down,
            missing_msg="Signature Optional\nClick to Select"
        ):
            picked = open_file_dialog("Select Signature Image for Applicant")
            if picked:
                declaration.set_field_val("sig_path", picked)
                app_state.tex_dirty = True

        # Status Badges
        sync_badge_y = photo_box_y + photo_box_h + int(36 * scale_y)
        draw_text_clean(font_bold, f"🟢 {os.path.basename(declaration.get_output_tex_path())} (Live in Sync)", right_x + int(20 * scale), sync_badge_y, int(13 * scale), DRACULA_GREEN)
        draw_text_clean(font_regular, f"Last TeX update: {app_state.last_sync_time}", right_x + int(20 * scale), sync_badge_y + int(18 * scale_y), int(11 * scale), DRACULA_COMMENT)

        save_badge_y = sync_badge_y + int(42 * scale_y)
        draw_text_clean(font_bold, f"💾 Form Data & Dossier (Auto-Saved)", right_x + int(20 * scale), save_badge_y, int(13 * scale), DRACULA_CYAN)
        draw_text_clean(font_regular, "Ready for GoaOnline Portal Filling", right_x + int(20 * scale), save_badge_y + int(18 * scale_y), int(11 * scale), DRACULA_COMMENT)

        # Primary Action Button: Compile PDF
        action_btn_w = right_w - int(40 * scale)
        action_btn_h = int(48 * scale_y)
        action_btn_x = right_x + int(20 * scale)
        action_btn_y = preview_box_rect.y + preview_box_rect.height - action_btn_h - int(20 * scale_y)
        action_rect = rl.Rectangle(action_btn_x, action_btn_y, action_btn_w, action_btn_h)

        btn_clicked = draw_button(
            text="⚡ GENERATE & COMPILE PDF",
            rect=action_rect,
            bg_color=DRACULA_PURPLE,
            fg_color=DRACULA_BG,
            font=font_bold,
            font_size=int(15 * scale),
            mouse_pos=mouse_pos,
            is_mouse_down=is_mouse_down
        )

        if btn_clicked:
            # Check photo presence before compile
            current_photo = declaration.get_field_val("photo_path")
            if not current_photo or not os.path.isfile(current_photo):
                picked_photo = open_file_dialog("Photo path missing. Please select Passport Photo (.jpg, .png):")
                if picked_photo:
                    declaration.set_field_val("photo_path", picked_photo)
                    app_state.tex_dirty = True
                    app_state.sync_tex()

            ok, res_path = app_state.compile_pdf()
            if ok:
                app_state.status_msg = f"Compiled successfully: {os.path.basename(res_path)}"
                app_state.status_color = DRACULA_GREEN
                try:
                    os.startfile(res_path)
                except Exception:
                    pass
            else:
                app_state.status_msg = f"Compilation failed: {res_path}"
                app_state.status_color = DRACULA_RED

        # 4. Bottom Status Bar
        footer_y = h - footer_h
        rl.draw_rectangle(0, footer_y, w, footer_h, DRACULA_CURRENT_LINE)
        rl.draw_line(0, footer_y, w, footer_y, DRACULA_COMMENT)

        draw_text_clean(font_bold, "Status:", 24 * scale, footer_y + int(20 * scale_y), int(13 * scale), DRACULA_COMMENT)
        draw_text_clean(font_bold, app_state.status_msg, int(90 * scale), footer_y + int(20 * scale_y), int(13 * scale), app_state.status_color)

        # "Open PDF" Button if compiled
        if app_state.is_compiled and os.path.exists(app_state.compiled_pdf):
            open_btn_w = int(140 * scale)
            open_btn_h = int(36 * scale_y)
            open_btn_x = w - open_btn_w - int(24 * scale)
            open_btn_y = footer_y + int(12 * scale_y)
            open_rect = rl.Rectangle(open_btn_x, open_btn_y, open_btn_w, open_btn_h)

            if draw_button("📂 Open PDF", open_rect, DRACULA_GREEN, DRACULA_BG, font_bold, int(13 * scale), mouse_pos, is_mouse_down):
                try:
                    os.startfile(app_state.compiled_pdf)
                except Exception as e:
                    app_state.status_msg = f"Error opening PDF: {e}"

        rl.end_drawing()

    app_state.unload()
    rl.close_window()

def main():
    parser = argparse.ArgumentParser(description="GoaOnAuto Modular Declaration GUI")
    parser.add_argument("--type", default="residence", help="Declaration type: residence, obc, divergence")
    parser.add_argument("--dir", default="", help="Applicant folder directory path")
    parser.add_argument("--no-prompt", action="store_true", help="Do not prompt for missing files on launch")
    args = parser.parse_args()

    run_app(declaration_type=args.type, target_dir=args.dir, no_prompt=args.no_prompt)

if __name__ == "__main__":
    main()
