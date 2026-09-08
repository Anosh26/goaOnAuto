"""
GoaOnAuto GUI Core Package.
Provides shared UI tokens, fonts, dialogs, widgets, and LaTeX compiler services.
"""
from .colors import (
    DRACULA_BG, DRACULA_CURRENT_LINE, DRACULA_SELECTION,
    DRACULA_FG, DRACULA_COMMENT, DRACULA_CYAN,
    DRACULA_GREEN, DRACULA_ORANGE, DRACULA_PINK,
    DRACULA_PURPLE, DRACULA_RED, DRACULA_YELLOW
)
from .fonts import load_custom_font, draw_text_clean, measure_text_clean
from .dialogs import open_file_dialog
from .latex_compiler import escape_latex, find_pdflatex_binary, compile_latex_to_pdf
from .widgets import FormField, draw_button, draw_input_row, draw_image_preview_card

__all__ = [
    "DRACULA_BG", "DRACULA_CURRENT_LINE", "DRACULA_SELECTION",
    "DRACULA_FG", "DRACULA_COMMENT", "DRACULA_CYAN",
    "DRACULA_GREEN", "DRACULA_ORANGE", "DRACULA_PINK",
    "DRACULA_PURPLE", "DRACULA_RED", "DRACULA_YELLOW",
    "load_custom_font", "draw_text_clean", "measure_text_clean",
    "open_file_dialog",
    "escape_latex", "find_pdflatex_binary", "compile_latex_to_pdf",
    "FormField", "draw_button", "draw_input_row", "draw_image_preview_card"
]
