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
    from .declarations.base import calculate_age_from_dob
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
    from python.gui.declarations.base import calculate_age_from_dob

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

        # Multitasking & Responsive UI State
        self.active_tab = "form"  # "form" or "assets" (used in narrow mode)
        self.scroll_y = 0.0
        self.target_scroll_y = 0.0

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

    # Set minimum window bounds so UI never collapses
    try:
        rl.set_window_min_size(560, 420)
    except Exception:
        pass

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

        # Layout Dimensions & Responsive Breakpoints
        w = rl.get_screen_width()
        h = rl.get_screen_height()
        is_narrow = (w < 960)

        # Scale typography comfortably: NEVER shrink below readable thresholds
        scale = max(0.95, min(1.35, w / 1260.0))
        scale_y = max(0.90, min(1.25, h / 820.0))

        title_size = max(16, min(20, int(18 * scale)))
        label_size = max(13, min(15, int(14 * scale)))
        input_size = max(13, min(15, int(14 * scale)))
        btn_size = max(12, min(14, int(13 * scale)))

        mouse_pos = rl.get_mouse_position()
        is_mouse_down = rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT)

        visible_fields = declaration.get_visible_fields()
        if app_state.active_field_idx >= len(visible_fields):
            app_state.active_field_idx = 0
        active_f = visible_fields[app_state.active_field_idx] if visible_fields else None

        header_h = int(54 * scale_y)
        footer_h = int(56 * scale_y)
        content_y = header_h + 10
        view_h = max(100, h - content_y - footer_h - 6)

        # Keyboard Navigation: Tab / Shift+Tab with automatic viewport scrolling
        row_h = 52
        if rl.is_key_pressed(rl.KEY_TAB):
            if rl.is_key_down(rl.KEY_LEFT_SHIFT) or rl.is_key_down(rl.KEY_RIGHT_SHIFT):
                app_state.active_field_idx = (app_state.active_field_idx - 1) % len(visible_fields)
            else:
                app_state.active_field_idx = (app_state.active_field_idx + 1) % len(visible_fields)

            # Auto-scroll active field into view
            field_top = app_state.active_field_idx * row_h
            if field_top < app_state.target_scroll_y:
                app_state.target_scroll_y = max(0.0, float(field_top))
            elif field_top + row_h > app_state.target_scroll_y + view_h:
                app_state.target_scroll_y = float(field_top + row_h - view_h + 20)

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

            # Dynamic age recalculation if typing in DOB field
            if active_f.key == "dob":
                calc = calculate_age_from_dob(active_f.value)
                if calc is not None:
                    declaration.set_field_val("age", str(calc))
            elif active_f.key == "child_dob":
                calc = calculate_age_from_dob(active_f.value)
                if calc is not None:
                    declaration.set_field_val("child_age", str(calc))

        # Mouse wheel vertical scrolling
        wheel = rl.get_mouse_wheel_move()
        if wheel != 0:
            app_state.target_scroll_y -= wheel * 55.0

        # Render Frame
        rl.begin_drawing()
        rl.clear_background(DRACULA_BG)

        # -------------------------------------------------------------
        # 1. Header Bar (Adaptive Title, Tabs, Mode Selector)
        # -------------------------------------------------------------
        rl.draw_rectangle(0, 0, w, header_h, DRACULA_CURRENT_LINE)
        rl.draw_line(0, header_h, w, header_h, DRACULA_COMMENT)

        # Title / Icon
        display_title = declaration.title if w > 720 else "🏛️ Declaration"
        draw_text_clean(font_bold, display_title, 20, 16 * scale_y, title_size, DRACULA_PURPLE)

        # Mode Selector Buttons (Self / Child)
        right_offset = 20
        if len(declaration.supported_modes) > 1:
            mode_btn_w = 95 if is_narrow else 115
            mode_btn_h = int(32 * scale_y)
            btn_y = int(11 * scale_y)

            child_x = w - mode_btn_w - right_offset
            self_x = child_x - mode_btn_w - 10

            self_rect = rl.Rectangle(self_x, btn_y, mode_btn_w, mode_btn_h)
            child_rect = rl.Rectangle(child_x, btn_y, mode_btn_w, mode_btn_h)

            self_bg = DRACULA_PURPLE if declaration.mode == "self" else DRACULA_BG
            self_fg = DRACULA_BG if declaration.mode == "self" else DRACULA_FG
            if draw_button("Self", self_rect, self_bg, self_fg, font_bold, btn_size, mouse_pos, is_mouse_down):
                if declaration.mode != "self":
                    declaration.mode = "self"
                    app_state.tex_dirty = True
                    app_state.status_msg = "Switched to Self Declaration Mode"
                    app_state.status_color = DRACULA_CYAN

            child_bg = DRACULA_YELLOW if declaration.mode == "child" else DRACULA_BG
            child_fg = DRACULA_BG if declaration.mode == "child" else DRACULA_FG
            if draw_button("Child", child_rect, child_bg, child_fg, font_bold, btn_size, mouse_pos, is_mouse_down):
                if declaration.mode != "child":
                    declaration.mode = "child"
                    app_state.tex_dirty = True
                    app_state.status_msg = "Switched to Child Declaration Mode"
                    app_state.status_color = DRACULA_YELLOW

            right_offset += (mode_btn_w * 2) + 20

        # Narrow Multitasking Mode: Navigation Tab Switcher
        if is_narrow:
            tab_btn_w = 120
            tab_btn_h = int(32 * scale_y)
            tab_y = int(11 * scale_y)
            tab_assets_x = w - right_offset - tab_btn_w
            tab_form_x = tab_assets_x - tab_btn_w - 8

            form_rect = rl.Rectangle(tab_form_x, tab_y, tab_btn_w, tab_btn_h)
            assets_rect = rl.Rectangle(tab_assets_x, tab_y, tab_btn_w, tab_btn_h)

            form_bg = DRACULA_CYAN if app_state.active_tab == "form" else DRACULA_CURRENT_LINE
            form_fg = DRACULA_BG if app_state.active_tab == "form" else DRACULA_FG
            if draw_button("📝 Form", form_rect, form_bg, form_fg, font_bold, btn_size, mouse_pos, is_mouse_down):
                app_state.active_tab = "form"
                app_state.target_scroll_y = 0.0

            assets_bg = DRACULA_CYAN if app_state.active_tab == "assets" else DRACULA_CURRENT_LINE
            assets_fg = DRACULA_BG if app_state.active_tab == "assets" else DRACULA_FG
            if draw_button("⚡ Assets/PDF", assets_rect, assets_bg, assets_fg, font_bold, btn_size, mouse_pos, is_mouse_down):
                app_state.active_tab = "assets"
                app_state.target_scroll_y = 0.0

        # -------------------------------------------------------------
        # 2. Main Content (Wide Side-by-Side OR Reoriented Full-Width)
        # -------------------------------------------------------------
        total_form_h = (len(visible_fields) * row_h) + 24

        if not is_narrow:
            # ===================== WIDE DUAL-COLUMN MODE =====================
            left_w = int(w * 0.58)
            right_x = left_w + 18
            right_w = w - right_x - 20

            # Clamp scroll bounds for left form column
            max_scroll = max(0.0, float(total_form_h - view_h))
            app_state.target_scroll_y = max(0.0, min(max_scroll, app_state.target_scroll_y))
            app_state.scroll_y += (app_state.target_scroll_y - app_state.scroll_y) * min(1.0, dt * 16.0)

            # Left Form View with Scissor Clipping
            rl.begin_scissor_mode(0, content_y, left_w + 10, view_h)

            lbl_x = 22
            lbl_w = min(190, int(left_w * 0.35))
            inp_x = lbl_x + lbl_w + 12

            for i, field in enumerate(visible_fields):
                curr_y = content_y + 12 + (i * row_h) - int(app_state.scroll_y)
                browse_btn_w = 74 if field.is_path else 0
                inp_w = left_w - inp_x - (browse_btn_w + 12 if field.is_path else 0)

                # Skip drawing if outside vertical viewport
                if curr_y + row_h < content_y or curr_y > content_y + view_h:
                    continue

                clicked_box, val_changed = draw_input_row(
                    field=field,
                    is_focused=(active_f == field),
                    lbl_x=lbl_x,
                    lbl_w=lbl_w,
                    inp_x=inp_x,
                    inp_w=inp_w,
                    curr_y=curr_y,
                    inp_h=36,
                    scale=scale,
                    scale_y=scale_y,
                    label_size=label_size,
                    input_size=input_size,
                    font_bold=font_bold,
                    font_regular=font_regular,
                    mouse_pos=mouse_pos,
                    is_mouse_down=is_mouse_down,
                    cursor_timer=app_state.cursor_timer,
                    clip_min_y=content_y,
                    clip_max_y=content_y + view_h
                )

                if clicked_box:
                    app_state.active_field_idx = i
                if val_changed:
                    app_state.tex_dirty = True

            rl.end_scissor_mode()

            # Sleek Scrollbar for left column
            if max_scroll > 0:
                bar_h = max(24, int(view_h * (view_h / total_form_h)))
                bar_y = content_y + int((app_state.scroll_y / max_scroll) * (view_h - bar_h))
                rl.draw_rectangle_rounded(rl.Rectangle(left_w - 4, bar_y, 5, bar_h), 0.5, 4, DRACULA_COMMENT)

            # Right Actions & Live Asset Cards
            preview_box = rl.Rectangle(right_x, content_y + 6, right_w, view_h - 12)
            rl.draw_rectangle_rounded(preview_box, 0.04, 8, DRACULA_CURRENT_LINE)
            rl.draw_rectangle_rounded_lines(preview_box, 0.04, 8, DRACULA_COMMENT)

            draw_text_clean(font_bold, "📄 Live Preview & Document Assets", right_x + 18, content_y + 18, int(15 * scale), DRACULA_CYAN)

            # Photo Preview Card
            photo_box_w = min(140, int(right_w * 0.42))
            photo_box_h = int(photo_box_w * 1.25)
            photo_box_x = right_x + 20
            photo_box_y = content_y + 50
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
                missing_msg="⚠️ Missing\nClick to Pick"
            ):
                picked = open_file_dialog("Select Passport Photo for Applicant")
                if picked:
                    declaration.set_field_val("photo_path", picked)
                    app_state.tex_dirty = True

            # Signature Preview Card
            sig_box_x = photo_box_x + photo_box_w + 16
            sig_box_w = right_w - photo_box_w - 56
            sig_box_h = int(photo_box_h * 0.65)
            sig_box_y = photo_box_y + int((photo_box_h - sig_box_h) / 2)
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
                missing_msg="Signature Optional\nClick to Pick"
            ):
                picked = open_file_dialog("Select Signature Image for Applicant")
                if picked:
                    declaration.set_field_val("sig_path", picked)
                    app_state.tex_dirty = True

            # Status Badges
            sync_y = photo_box_y + photo_box_h + 30
            draw_text_clean(font_bold, f"🟢 {os.path.basename(declaration.get_output_tex_path())} (Live in Sync)", right_x + 20, sync_y, 13, DRACULA_GREEN)
            draw_text_clean(font_regular, f"Last update: {app_state.last_sync_time}", right_x + 20, sync_y + 18, 11, DRACULA_COMMENT)

            save_y = sync_y + 44
            draw_text_clean(font_bold, "💾 Form Data & Dossier (Auto-Saved)", right_x + 20, save_y, 13, DRACULA_CYAN)
            draw_text_clean(font_regular, "Ready for GoaOnline Portal Automation", right_x + 20, save_y + 18, 11, DRACULA_COMMENT)

            # Primary Compile PDF Button
            btn_w = right_w - 40
            btn_h = 46
            btn_x = right_x + 20
            btn_y = preview_box.y + preview_box.height - btn_h - 18
            action_rect = rl.Rectangle(btn_x, btn_y, btn_w, btn_h)

            if draw_button("⚡ GENERATE & COMPILE PDF", action_rect, DRACULA_PURPLE, DRACULA_BG, font_bold, 14, mouse_pos, is_mouse_down):
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

        else:
            # ===================== NARROW MULTITASKING REORIENTED MODE =====================
            if app_state.active_tab == "form":
                # Full Width Adaptive Form
                max_scroll = max(0.0, float(total_form_h - view_h))
                app_state.target_scroll_y = max(0.0, min(max_scroll, app_state.target_scroll_y))
                app_state.scroll_y += (app_state.target_scroll_y - app_state.scroll_y) * min(1.0, dt * 16.0)

                rl.begin_scissor_mode(0, content_y, w, view_h)

                lbl_x = 20
                lbl_w = min(170, max(120, int(w * 0.32)))
                inp_x = lbl_x + lbl_w + 10

                for i, field in enumerate(visible_fields):
                    curr_y = content_y + 10 + (i * row_h) - int(app_state.scroll_y)
                    browse_btn_w = 70 if field.is_path else 0
                    inp_w = w - inp_x - 24 - (browse_btn_w + 8 if field.is_path else 0)

                    if curr_y + row_h < content_y or curr_y > content_y + view_h:
                        continue

                    clicked_box, val_changed = draw_input_row(
                        field=field,
                        is_focused=(active_f == field),
                        lbl_x=lbl_x,
                        lbl_w=lbl_w,
                        inp_x=inp_x,
                        inp_w=inp_w,
                        curr_y=curr_y,
                        inp_h=36,
                        scale=scale,
                        scale_y=scale_y,
                        label_size=label_size,
                        input_size=input_size,
                        font_bold=font_bold,
                        font_regular=font_regular,
                        mouse_pos=mouse_pos,
                        is_mouse_down=is_mouse_down,
                        cursor_timer=app_state.cursor_timer,
                        clip_min_y=content_y,
                        clip_max_y=content_y + view_h
                    )

                    if clicked_box:
                        app_state.active_field_idx = i
                    if val_changed:
                        app_state.tex_dirty = True

                rl.end_scissor_mode()

                # Scrollbar
                if max_scroll > 0:
                    bar_h = max(24, int(view_h * (view_h / total_form_h)))
                    bar_y = content_y + int((app_state.scroll_y / max_scroll) * (view_h - bar_h))
                    rl.draw_rectangle_rounded(rl.Rectangle(w - 8, bar_y, 5, bar_h), 0.5, 4, DRACULA_COMMENT)

            else:
                # Tab: Assets & PDF Compilation View (Reoriented)
                total_assets_h = 420
                max_scroll = max(0.0, float(total_assets_h - view_h))
                app_state.target_scroll_y = max(0.0, min(max_scroll, app_state.target_scroll_y))
                app_state.scroll_y += (app_state.target_scroll_y - app_state.scroll_y) * min(1.0, dt * 16.0)

                rl.begin_scissor_mode(0, content_y, w, view_h)
                asset_y = content_y + 16 - int(app_state.scroll_y)

                # Centered Previews Container
                container_w = min(540, w - 40)
                container_x = (w - container_w) // 2

                # Photo Card & Signature Card
                card_w = int((container_w - 20) / 2)
                photo_rect = rl.Rectangle(container_x, asset_y, card_w, 160)
                sig_rect = rl.Rectangle(container_x + card_w + 20, asset_y, card_w, 160)

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
                    missing_msg="⚠️ Missing\nClick to Pick"
                ):
                    picked = open_file_dialog("Select Passport Photo for Applicant")
                    if picked:
                        declaration.set_field_val("photo_path", picked)
                        app_state.tex_dirty = True

                if draw_image_preview_card(
                    title="Signature Image",
                    texture=app_state.sig_texture,
                    rect=sig_rect,
                    scale=scale,
                    scale_y=scale_y,
                    font_bold=font_bold,
                    font_regular=font_regular,
                    mouse_pos=mouse_pos,
                    is_mouse_down=is_mouse_down,
                    missing_msg="Signature Optional\nClick to Pick"
                ):
                    picked = open_file_dialog("Select Signature Image for Applicant")
                    if picked:
                        declaration.set_field_val("sig_path", picked)
                        app_state.tex_dirty = True

                # Badges
                badge_y = asset_y + 195
                draw_text_clean(font_bold, f"🟢 {os.path.basename(declaration.get_output_tex_path())} (Live in Sync)", container_x, badge_y, 13, DRACULA_GREEN)
                draw_text_clean(font_regular, f"Last update: {app_state.last_sync_time}", container_x, badge_y + 18, 11, DRACULA_COMMENT)

                save_y = badge_y + 44
                draw_text_clean(font_bold, "💾 Form Data & Dossier Auto-Saved", container_x, save_y, 13, DRACULA_CYAN)

                # Big Compile PDF Button
                btn_w = container_w
                btn_h = 48
                action_rect = rl.Rectangle(container_x, save_y + 36, btn_w, btn_h)

                if draw_button("⚡ GENERATE & COMPILE PDF", action_rect, DRACULA_PURPLE, DRACULA_BG, font_bold, 14, mouse_pos, is_mouse_down):
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

                rl.end_scissor_mode()

        # -------------------------------------------------------------
        # 3. Bottom Status & Fast Action Bar
        # -------------------------------------------------------------
        footer_y = h - footer_h
        rl.draw_rectangle(0, footer_y, w, footer_h, DRACULA_CURRENT_LINE)
        rl.draw_line(0, footer_y, w, footer_y, DRACULA_COMMENT)

        # Status indicator
        draw_text_clean(font_bold, "Status:", 20, footer_y + 18, 13, DRACULA_COMMENT)
        status_disp = app_state.status_msg
        max_status_len = max(20, int((w - 360) / 8.5))
        if len(status_disp) > max_status_len:
            status_disp = status_disp[:max_status_len - 3] + "..."
        draw_text_clean(font_bold, status_disp, 80, footer_y + 18, 13, app_state.status_color)

        btn_right_x = w - 20

        # "Open PDF" Button if compiled
        if app_state.is_compiled and os.path.exists(app_state.compiled_pdf):
            open_btn_w = 120
            btn_right_x -= open_btn_w
            open_rect = rl.Rectangle(btn_right_x, footer_y + 10, open_btn_w, 36)

            if draw_button("📂 Open PDF", open_rect, DRACULA_GREEN, DRACULA_BG, font_bold, 13, mouse_pos, is_mouse_down):
                try:
                    os.startfile(app_state.compiled_pdf)
                except Exception as e:
                    app_state.status_msg = f"Error opening PDF: {e}"
            btn_right_x -= 12

        # In Narrow Mode, when on Form Tab: Provide Quick "⚡ Compile" button in footer
        if is_narrow and app_state.active_tab == "form":
            quick_compile_w = 135
            btn_right_x -= quick_compile_w
            quick_rect = rl.Rectangle(btn_right_x, footer_y + 10, quick_compile_w, 36)

            if draw_button("⚡ Compile PDF", quick_rect, DRACULA_PURPLE, DRACULA_BG, font_bold, 13, mouse_pos, is_mouse_down):
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
