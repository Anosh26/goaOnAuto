"""
Base Declaration Architecture for GoaOnAuto.
Single Responsibility: Encapsulates common applicant data fields, dossier synchronization,
and defines the declaration extension contract.
"""
from __future__ import annotations
import os
import json
import glob
import re
from abc import ABC, abstractmethod
from datetime import datetime
from ..core.widgets import FormField
from ..core.latex_compiler import escape_latex

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class BaseDeclaration(ABC):
    """Abstract Base Class for all GoaOnline affidavit/declaration modules."""

    def __init__(self, target_dir: str):
        self.target_dir = os.path.abspath(target_dir) if target_dir else os.path.join(_PROJECT_ROOT, "work_directory")
        self.mode = "self"
        self.supported_modes: list[str] = ["self"]
        self.fields: list[FormField] = []
        self.declaration_id = "base"
        self.title = "Declaration"
        self.service_id = ""

    def load_dossier(self) -> dict:
        """Loads client data from applicant_dossier.json if present."""
        dossier_file = os.path.join(self.target_dir, "applicant_dossier.json")
        if os.path.exists(dossier_file):
            try:
                with open(dossier_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def find_file_pattern(self, patterns: list[str]) -> str:
        """Finds matching media files in the client directory."""
        if not os.path.isdir(self.target_dir):
            return ""
        for pat in patterns:
            matches = glob.glob(os.path.join(self.target_dir, pat))
            for m in matches:
                if os.path.isfile(m) and not m.endswith((".json", ".pdf", ".tex")):
                    return os.path.abspath(m)
        return ""

    def get_field_val(self, key: str) -> str:
        for f in self.fields:
            if f.key == key:
                return f.value
        return ""

    def set_field_val(self, key: str, val: str) -> None:
        for f in self.fields:
            if f.key == key:
                f.value = val

    def get_visible_fields(self) -> list[FormField]:
        """Returns fields currently visible based on active mode."""
        if self.mode == "child":
            return self.fields
        # In non-child mode, hide child-specific keyword fields
        return [f for f in self.fields if not f.key.startswith("child_")]

    def get_template_path(self, template_filename: str) -> str:
        """Resolves absolute path to template in templates/latex/."""
        return os.path.join(_PROJECT_ROOT, "templates", "latex", template_filename)

    def inject_photo_and_sig(self, content: str, photo_path: str, sig_path: str) -> str:
        """Replaces LaTeX placeholder boxes with photo and signature image includes."""
        # 1. Photo replacement
        if photo_path and os.path.isfile(photo_path):
            clean_photo = os.path.abspath(photo_path).replace("\\", "/")
            photo_snippet = f'\\fbox{{\\includegraphics[width=1.2in, height=1.5in]{{"{clean_photo}"}}}}'
            fbox_pattern = r"\\fbox\{\\begin\{minipage\}\[t\]\[1\.5in\]\{1\.2in\}.*?\\end\{minipage\}\}"
            content = re.sub(fbox_pattern, lambda m: photo_snippet, content, flags=re.DOTALL)

        # 2. Signature replacement
        if sig_path and os.path.isfile(sig_path):
            clean_sig = os.path.abspath(sig_path).replace("\\", "/")
            sig_snippet = f'\\includegraphics[width=3.2cm, height=1.1cm, keepaspectratio]{{"{clean_sig}"}} \\\\\n    \\rule{{4.5cm}}{{0.4pt}}'
            content = re.sub(r"\\rule\{6cm\}\{0\.4pt\}", lambda m: sig_snippet, content)

        return content

    @abstractmethod
    def load_data(self) -> None:
        """Loads verified data from client directory or dossier."""
        pass

    @abstractmethod
    def save_data(self) -> None:
        """Saves form data JSON and updates applicant_dossier.json."""
        pass

    @abstractmethod
    def generate_tex(self) -> tuple[bool, str, str]:
        """
        Synthesizes the .tex file and saves it in target_dir.
        Returns (success, tex_path, error_message).
        """
        pass

    @abstractmethod
    def get_output_pdf_path(self) -> str:
        """Returns the expected path to the compiled PDF."""
        pass

    @abstractmethod
    def get_output_tex_path(self) -> str:
        """Returns the expected path to the synthesized TeX file."""
        pass
