"""
Native File Picker Dialogs for Windows.
Single Responsibility: Opens modal file dialogs using Tkinter.
"""
import sys

def open_file_dialog(title: str, filetypes=None) -> str:
    """Opens native Windows file picker dialog."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        if filetypes is None:
            filetypes = [
                ("Images & PDFs", "*.jpg;*.jpeg;*.png;*.pdf"),
                ("Images (*.jpg, *.png)", "*.jpg;*.jpeg;*.png"),
                ("All files", "*.*")
            ]
        selected = filedialog.askopenfilename(title=title, filetypes=filetypes)
        root.destroy()
        return selected or ""
    except Exception as e:
        print(f"File picker notice: {e}", file=sys.stderr)
        return ""
