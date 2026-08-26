/**
 * Windows System Tray Service.
 * Single Responsibility: Manages background watcher process lifecycle and Windows system tray status icon.
 */
import os
import sys
import subprocess
import threading
import winreg
import pystray
from PIL import Image, ImageDraw

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_FILE = os.path.join(PROJECT_DIR, ".env")
LOG_DIR = os.path.join(PROJECT_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "watcher.log")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

def get_work_dir():
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DOCUMENT_WATCH_PATH="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return os.path.expandvars(val)
    return os.path.join(PROJECT_DIR, "work_directory")

STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "GoaOnAutoTray"

def is_startup_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except WindowsError:
        return False

def set_startup(enable: bool):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_SET_VALUE)
        if enable:
            vbs_path = os.path.join(PROJECT_DIR, "tools", "tray", "start_tray.vbs")
            cmd = f'wscript.exe "{vbs_path}"'
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except WindowsError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Error setting startup: {e}")

class GoaOnAutoTrayApp:
    def __init__(self):
        self.process = None
        self.is_running = False
        self.icon = None
        self.lock = threading.Lock()
        self.log_viewer_process = None

    def create_icon_image(self, active: bool):
        img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        draw.ellipse([4, 4, 60, 60], fill=(24, 28, 36, 255), outline=(70, 80, 95, 255), width=2)
        
        if active:
            draw.ellipse([14, 14, 50, 50], fill=(34, 197, 94, 255), outline=(22, 163, 74, 255), width=2)
            draw.ellipse([26, 26, 38, 38], fill=(240, 253, 244, 255))
        else:
            draw.ellipse([14, 14, 50, 50], fill=(234, 88, 12, 255), outline=(194, 65, 12, 255), width=2)
            draw.rectangle([24, 22, 28, 42], fill=(255, 255, 255, 255))
            draw.rectangle([36, 22, 40, 42], fill=(255, 255, 255, 255))

        return img

    def _pipe_logs(self, pipe):
        try:
            with open(LOG_FILE, "a", encoding="utf-8", buffering=1) as log_f:
                for line in iter(pipe.readline, ''):
                    if not line:
                        break
                    log_f.write(line)
                    log_f.flush()
        except Exception:
            pass

    def start_watcher(self):
        with self.lock:
            if self.is_running:
                return

            try:
                with open(LOG_FILE, "a", encoding="utf-8") as log_f:
                    import datetime
                    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    log_f.write(f"\n--- [Watcher Started: {now_str}] ---\n")
                    log_f.flush()

                cmd = ["bun", "src/workDirectoryWatcher.ts"]
                self.process = subprocess.Popen(
                    cmd,
                    cwd=PROJECT_DIR,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                threading.Thread(target=self._pipe_logs, args=(self.process.stdout,), daemon=True).start()

                self.is_running = True
                self.update_tray()
            except Exception as e:
                print(f"Error starting watcher: {e}")

    def stop_watcher(self):
        with self.lock:
            if not self.is_running:
                return

            if self.process:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=3)
                except Exception:
                    try:
                        self.process.kill()
                    except Exception:
                        pass
                self.process = None

            with open(LOG_FILE, "a", encoding="utf-8") as log_f:
                import datetime
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_f.write(f"--- [Watcher Paused/Stopped: {now_str}] ---\n")
                log_f.flush()

            self.is_running = False
            self.update_tray()

    def toggle_watcher(self, icon=None, item=None):
        if self.is_running:
            self.stop_watcher()
        else:
            self.start_watcher()

    def show_live_logs(self, icon=None, item=None):
        try:
            viewer_script = os.path.join(PROJECT_DIR, "tools", "gui", "log_viewer.py")
            subprocess.Popen(
                ["pythonw.exe", viewer_script],
                cwd=PROJECT_DIR,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
        except Exception:
            self.open_log_file()

    def open_log_file(self, icon=None, item=None):
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write("=== GoaOnAuto Watcher Log Initialized ===\n")
        if os.name == "nt":
            os.startfile(LOG_FILE)

    def toggle_startup(self, icon=None, item=None):
        current = is_startup_enabled()
        set_startup(not current)

    def open_work_dir(self, icon=None, item=None):
        work_dir = get_work_dir()
        if not os.path.exists(work_dir):
            os.makedirs(work_dir, exist_ok=True)
        if os.name == "nt":
            os.startfile(work_dir)

    def open_staging_dir(self, icon=None, item=None):
        import tempfile
        stage_dir = os.path.join(tempfile.gettempdir(), "goaOnAuto_drive_stage")
        if not os.path.exists(stage_dir):
            os.makedirs(stage_dir, exist_ok=True)
        if os.name == "nt":
            os.startfile(stage_dir)

    def update_tray(self):
        if self.icon:
            self.icon.icon = self.create_icon_image(self.is_running)
            self.icon.title = f"GoaOnAuto ({'Active (RTX 4060 GPU)' if self.is_running else 'Paused'})"

    def exit_app(self, icon=None, item=None):
        self.stop_watcher()
        if self.icon:
            self.icon.stop()

    def build_menu(self):
        return pystray.Menu(
            pystray.MenuItem(
                lambda text: f"Status: {'🟢 Active (RTX 4060 GPU)' if self.is_running else '🟠 Paused'}",
                self.show_live_logs,
                default=True
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("📊 View Real-Time Live Logs", self.show_live_logs),
            pystray.MenuItem("📄 Open Raw Log File", self.open_log_file),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda text: "⏸️ Pause Watcher" if self.is_running else "▶️ Start Watcher",
                self.toggle_watcher
            ),
            pystray.MenuItem("📁 Open Google Drive Work Folder", self.open_work_dir),
            pystray.MenuItem("📂 Open Local Staging Folder", self.open_staging_dir),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "🚀 Start on Windows Boot",
                self.toggle_startup,
                checked=lambda item: is_startup_enabled()
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Exit", self.exit_app)
        )

    def run(self):
        self.start_watcher()
        initial_img = self.create_icon_image(self.is_running)
        self.icon = pystray.Icon(
            name="GoaOnAuto",
            icon=initial_img,
            title="GoaOnAuto (RTX 4060 GPU Watcher)",
            menu=self.build_menu()
        )
        self.icon.run()

if __name__ == "__main__":
    app = GoaOnAutoTrayApp()
    app.run()
