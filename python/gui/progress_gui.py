"""
GoaOnAuto Batch Processing Progress Monitor - Raylib GPU GUI.
Dracula Theme | Real-time Hardware Metrics | Smooth Progress Interpolation | Stable Single Instance.
"""
import sys
import os
import math
import json
import time
import threading
import pyray as rl

# Ensure project root in sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Dracula Theme Palette
DRACULA_BG = rl.Color(40, 42, 54, 255)
DRACULA_CURRENT_LINE = rl.Color(68, 71, 90, 255)
DRACULA_SELECTION = rl.Color(68, 71, 90, 180)
DRACULA_FG = rl.Color(248, 248, 242, 255)
DRACULA_COMMENT = rl.Color(98, 114, 164, 255)
DRACULA_CYAN = rl.Color(139, 233, 253, 255)
DRACULA_GREEN = rl.Color(80, 250, 123, 255)
DRACULA_ORANGE = rl.Color(255, 184, 108, 255)
DRACULA_PINK = rl.Color(255, 121, 198, 255)
DRACULA_PURPLE = rl.Color(189, 147, 249, 255)
DRACULA_RED = rl.Color(255, 85, 85, 255)
DRACULA_YELLOW = rl.Color(241, 250, 140, 255)

# Shared state between stdin reader thread and Raylib rendering thread
state = {
    "current_file": "None (Idle)",
    "queue_length": 0,
    "status": "Watching for documents...",
    "progress_percent": 0.0,
    "should_exit": False
}
state_lock = threading.Lock()

def get_hardware_status():
    """Fetches system RAM, CPU free percentage, and GPU presence."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        cpu_pct = psutil.cpu_percent(interval=None)
        free_ram_gb = round(mem.available / (1024 ** 3), 1)
        cpu_free_pct = round(max(0, 100.0 - cpu_pct), 0)
        return free_ram_gb, cpu_free_pct
    except Exception:
        return 0.0, 0.0

def stdin_reader():
    """Reads JSON updates from stdin in a background thread."""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                # If pipe closed (EOF), signal exit and terminate
                time.sleep(0.5)
                with state_lock:
                    state["should_exit"] = True
                break

            line = line.strip()
            if not line:
                continue

            data = json.loads(line)
            action_type = data.get("type")

            if action_type == "exit":
                with state_lock:
                    state["should_exit"] = True
                break
            elif action_type == "update":
                with state_lock:
                    if "current_file" in data:
                        state["current_file"] = data["current_file"]
                    if "queue_length" in data:
                        state["queue_length"] = data["queue_length"]
                    if "status" in data:
                        state["status"] = data["status"]
                    if "progress_percent" in data:
                        state["progress_percent"] = float(data["progress_percent"])
        except Exception:
            pass

def draw_text_clean(font, text: str, x: int, y: int, font_size: int, color: rl.Color):
    """Draws crisp text using custom TTF if loaded, else fallback to Raylib default font."""
    try:
        raw_bytes = text.encode('utf-8', 'ignore')
        font_valid = False
        if font:
            try:
                font_valid = (font.baseSize > 0)
            except Exception:
                font_valid = (getattr(font, 'base_size', 0) > 0)
        if font_valid:
            rl.draw_text_ex(font, raw_bytes, rl.Vector2(float(x), float(y)), float(font_size), 1.0, color)
        else:
            rl.draw_text(raw_bytes, x, y, font_size, color)
    except Exception:
        pass

def main():
    # Start reader thread
    t = threading.Thread(target=stdin_reader, daemon=True)
    t.start()

    # Window Configuration: Always run in background, smooth MSAA, resizable
    rl.set_config_flags(rl.FLAG_MSAA_4X_HINT | rl.FLAG_WINDOW_ALWAYS_RUN | rl.FLAG_WINDOW_RESIZABLE)

    win_w = 720
    win_h = 280
    rl.init_window(win_w, win_h, "GoaOnAuto - Batch Processing Engine Monitor")
    rl.set_target_fps(60)

    # Position window cleanly at the bottom-right so it never obstructs the center confirmation GUI
    try:
        mon = rl.get_current_monitor()
        mon_w = rl.get_monitor_width(mon)
        mon_h = rl.get_monitor_height(mon)
        if mon_w > 800 and mon_h > 600:
            pos_x = max(20, mon_w - win_w - 40)
            pos_y = max(40, mon_h - win_h - 70)
            rl.set_window_position(pos_x, pos_y)
    except Exception:
        pass

    # Load readable clean JetBrains Mono / Nerd Font
    try:
        from python.gui.core.fonts import load_custom_font
        font = load_custom_font("JetBrainsMono-Bold.ttf", 32)
    except Exception:
        font = None

    if not font:
        font_paths = [
            os.path.join(project_root, "assets", "fonts", "JetBrainsMono-Bold.ttf"),
            os.path.join(project_root, "assets", "fonts", "JetBrainsMono-Regular.ttf"),
            os.path.join(os.path.expanduser("~"), "AppData", "Local", "Microsoft", "Windows", "Fonts", "JetBrainsMonoNerdFont-Regular.ttf"),
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/cascadiacode.ttf",
            "C:/Windows/Fonts/consola.ttf",
            "C:/Windows/Fonts/arial.ttf"
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    loaded = rl.load_font_ex(fp.encode('utf-8'), 32, None, 0)
                    if loaded and (getattr(loaded, 'baseSize', 0) > 0 or getattr(loaded, 'base_size', 0) > 0):
                        rl.set_texture_filter(loaded.texture, rl.TEXTURE_FILTER_BILINEAR)
                        font = loaded
                        break
                except Exception:
                    font = None

    display_progress = 0.0
    pulse_timer = 0.0
    hw_update_timer = 0.0
    free_ram_gb, cpu_free_pct = get_hardware_status()

    while not rl.window_should_close():
        dt = rl.get_frame_time()
        pulse_timer += dt * 3.0
        hw_update_timer += dt

        # Update hardware status every 1.5 seconds
        if hw_update_timer >= 1.5:
            hw_update_timer = 0.0
            free_ram_gb, cpu_free_pct = get_hardware_status()

        with state_lock:
            if state["should_exit"]:
                break
            status_text = state["status"]
            current_file = state["current_file"]
            queue_len = state["queue_length"]
            target_progress = state["progress_percent"]

        # Smooth progress interpolation
        display_progress += (target_progress - display_progress) * min(1.0, dt * 10.0)
        is_active = target_progress > 0.0 or queue_len > 0 or "Running" in status_text or "Processing" in status_text

        # Render Frame
        w = rl.get_screen_width()
        h = rl.get_screen_height()

        rl.begin_drawing()
        rl.clear_background(DRACULA_BG)

        # -----------------------------
        # 1. Header Bar
        # -----------------------------
        rl.draw_rectangle(0, 0, w, 46, DRACULA_CURRENT_LINE)
        rl.draw_line(0, 46, w, 46, DRACULA_COMMENT)

        # Title
        draw_text_clean(font, "⚡ GoaOnAuto Batch Engine", 16, 12, 20, DRACULA_PURPLE)

        # Hardware status right-aligned
        hw_str = f"RAM Free: {free_ram_gb}GB | CPU Free: {int(cpu_free_pct)}% | RTX 4060"
        draw_text_clean(font, hw_str, w - 340, 14, 15, DRACULA_CYAN)

        # Pulsing Live Indicator
        pulse_alpha = int(180 + 75 * abs(math.sin(pulse_timer))) if is_active else 255
        indicator_color = rl.Color(80, 250, 123, pulse_alpha) if not is_active else rl.Color(255, 184, 108, pulse_alpha)
        rl.draw_circle(w - 355, 23, 5, indicator_color)

        # -----------------------------
        # 2. Main Content
        # -----------------------------
        # Status
        status_color = DRACULA_GREEN if "Idle" in status_text or "Watching" in status_text else DRACULA_YELLOW
        draw_text_clean(font, f"Status: {status_text}", 20, 62, 17, status_color)

        # Current File / Document
        display_file = current_file
        if len(display_file) > 55:
            display_file = "..." + display_file[-52:]
        draw_text_clean(font, f"Document: {display_file}", 20, 92, 16, DRACULA_FG)

        # Pending Batches Badge
        badge_x = 20
        badge_y = 124
        badge_w = 180
        badge_h = 28
        rl.draw_rectangle_rounded(rl.Rectangle(badge_x, badge_y, badge_w, badge_h), 0.3, 8, DRACULA_CURRENT_LINE)
        rl.draw_rectangle_rounded_lines(rl.Rectangle(badge_x, badge_y, badge_w, badge_h), 0.3, 8, DRACULA_COMMENT)

        queue_str = f"Batches In Queue: {queue_len}"
        queue_color = DRACULA_PINK if queue_len > 0 else DRACULA_COMMENT
        draw_text_clean(font, queue_str, badge_x + 12, badge_y + 6, 14, queue_color)

        if queue_len > 0:
            rl.draw_circle(badge_x + badge_w - 14, badge_y + 14, 4, DRACULA_PINK)

        # -----------------------------
        # 3. Dynamic Progress Bar
        # -----------------------------
        bar_x = 20
        bar_y = 175
        bar_w = w - 40
        bar_h = 24
        rl.draw_rectangle_rounded(rl.Rectangle(bar_x, bar_y, bar_w, bar_h), 0.4, 8, DRACULA_CURRENT_LINE)
        rl.draw_rectangle_rounded_lines(rl.Rectangle(bar_x, bar_y, bar_w, bar_h), 0.4, 8, DRACULA_COMMENT)

        clamped_pct = max(0.0, min(100.0, display_progress))
        fill_w = (bar_w - 4) * (clamped_pct / 100.0)

        if fill_w > 4:
            # Smooth gradient-like progress bar color
            bar_color = DRACULA_GREEN if clamped_pct >= 99.0 else DRACULA_CYAN
            rl.draw_rectangle_rounded(rl.Rectangle(bar_x + 2, bar_y + 2, fill_w, bar_h - 4), 0.4, 8, bar_color)

        # Progress Percentage Text
        pct_str = f"{int(clamped_pct)}%"
        draw_text_clean(font, pct_str, bar_x + (bar_w // 2) - 15, bar_y + 4, 15, DRACULA_BG if fill_w > (bar_w // 2) else DRACULA_FG)

        # Footer Hint
        hint_str = "GoaOnAuto AI Pipeline Active | Continuous Watcher Enabled"
        draw_text_clean(font, hint_str, 20, h - 30, 13, DRACULA_COMMENT)

        rl.end_drawing()

    if font:
        try:
            rl.unload_font(font)
        except Exception:
            pass
    rl.close_window()

if __name__ == "__main__":
    main()
