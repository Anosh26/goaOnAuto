/**
 * Dark Theme Live Log Viewer GUI.
 * Single Responsibility: Renders a real-time tail of logs/watcher.log with auto-scroll and pause controls.
 */
import os
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(PROJECT_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "watcher.log")

class LiveLogViewer:
    def __init__(self, root=None):
        self.own_root = root is None
        self.root = tk.Tk() if self.own_root else tk.Toplevel(root)
        self.root.title("GoaOnAuto - Real-Time Live Logs (RTX 4060 GPU)")
        self.root.geometry("900x560")
        self.root.configure(bg="#0b0f19")

        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self.autoscroll = tk.BooleanVar(value=True)
        self.is_running = True
        self.last_pos = 0

        self.setup_ui()
        self.start_tail_thread()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        header = tk.Frame(self.root, bg="#111827", height=45)
        header.pack(fill=tk.X, side=tk.TOP)

        title_lbl = tk.Label(
            header,
            text="⚡ GoaOnAuto Live Activity & GPU Inference Stream",
            font=("Segoe UI", 11, "bold"),
            fg="#38bdf8",
            bg="#111827"
        )
        title_lbl.pack(side=tk.LEFT, padx=14, pady=10)

        btn_frame = tk.Frame(header, bg="#111827")
        btn_frame.pack(side=tk.RIGHT, padx=10, pady=6)

        chk_autoscroll = tk.Checkbutton(
            btn_frame,
            text="Auto-scroll",
            variable=self.autoscroll,
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#111827",
            selectcolor="#1e293b",
            activebackground="#111827",
            activeforeground="#38bdf8"
        )
        chk_autoscroll.pack(side=tk.LEFT, padx=6)

        btn_clear = tk.Button(
            btn_frame,
            text="Clear View",
            font=("Segoe UI", 9),
            bg="#1f2937",
            fg="#f1f5f9",
            activebackground="#374151",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            command=self.clear_logs
        )
        btn_clear.pack(side=tk.LEFT, padx=4)

        self.text_area = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            bg="#0b0f19",
            fg="#e2e8f0",
            insertbackground="#38bdf8",
            font=("Consolas", 10),
            padx=12,
            pady=10,
            relief=tk.FLAT
        )
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.text_area.tag_config("gpu", foreground="#38bdf8")
        self.text_area.tag_config("success", foreground="#4ade80")
        self.text_area.tag_config("warn", foreground="#facc15")
        self.text_area.tag_config("error", foreground="#f87171")
        self.text_area.tag_config("header", foreground="#c084fc", font=("Consolas", 10, "bold"))
        self.text_area.tag_config("normal", foreground="#e2e8f0")

    def clear_logs(self):
        self.text_area.delete("1.0", tk.END)

    def apply_tags_to_line(self, line: str):
        if "⚡" in line or "GPU" in line or "CUDA" in line:
            tag = "gpu"
        elif "✅" in line or "✨" in line or "Identified" in line or "Renamed" in line or "Success" in line:
            tag = "success"
        elif "⚠️" in line or "Notice" in line:
            tag = "warn"
        elif "❌" in line or "Error" in line:
            tag = "error"
        elif "===" in line or "🚀" in line or "Watcher Started" in line:
            tag = "header"
        else:
            tag = "normal"

        self.text_area.insert(tk.END, line, tag)

    def start_tail_thread(self):
        threading.Thread(target=self.tail_file, daemon=True).start()

    def tail_file(self):
        while self.is_running:
            if os.path.exists(LOG_FILE):
                try:
                    with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                        if self.last_pos == 0:
                            f.seek(0, os.SEEK_END)
                            size = f.tell()
                            f.seek(max(0, size - 15000), os.SEEK_SET)
                        else:
                            f.seek(self.last_pos)

                        lines = f.readlines()
                        self.last_pos = f.tell()

                        if lines:
                            self.root.after(0, self.append_lines, lines)
                except Exception:
                    pass
            time.sleep(0.3)

    def append_lines(self, lines):
        for line in lines:
            self.apply_tags_to_line(line)

        if self.autoscroll.get():
            self.text_area.see(tk.END)

    def on_close(self):
        self.is_running = False
        if self.own_root:
            self.root.destroy()
        else:
            self.root.withdraw()

def main():
    app = LiveLogViewer()
    app.root.mainloop()

if __name__ == "__main__":
    main()
