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

def calculate_age_from_dob(dob_str: str | None) -> int | None:
    """Calculates age in years from various DOB string formats (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, YYYY)."""
    if not dob_str:
        return None
    cleaned = str(dob_str).strip()
    now = datetime.now()

    # 1. DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$", cleaned)
    if m:
        try:
            day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            birth = datetime(year, month, day)
            age = now.year - birth.year - ((now.month, now.day) < (birth.month, birth.day))
            if 0 <= age <= 130:
                return age
        except Exception:
            pass

    # 2. YYYY-MM-DD or YYYY/MM/DD
    m = re.match(r"^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})$", cleaned)
    if m:
        try:
            year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
            birth = datetime(year, month, day)
            age = now.year - birth.year - ((now.month, now.day) < (birth.month, birth.day))
            if 0 <= age <= 130:
                return age
        except Exception:
            pass

    # 3. 4-digit year only (e.g. YOB)
    m = re.search(r"\b(19\d{2}|20\d{2})\b", cleaned)
    if m:
        year = int(m.group(1))
        age = now.year - year
        if 0 <= age <= 130:
            return age

    return None


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

    def extract_age_and_dob(self, dossier: dict, fallback_age: str = "25") -> tuple[str, str]:
        """Extracts age and dob from dossier, automatically calculating age from dob if missing/invalid."""
        dob_val = ""
        for k in ["dob", "dateOfBirth", "birthDate"]:
            val = dossier.get(k)
            if isinstance(val, dict):
                dob_val = str(val.get("value", "")).strip()
            elif isinstance(val, str):
                dob_val = val.strip()
            if dob_val:
                break

        age_val = None
        age_raw = dossier.get("age")
        if isinstance(age_raw, dict):
            raw_v = age_raw.get("value")
            if raw_v is not None and str(raw_v).isdigit():
                parsed = int(raw_v)
                if 1 <= parsed <= 120:
                    age_val = parsed
        elif isinstance(age_raw, (int, str)) and str(age_raw).isdigit():
            parsed = int(age_raw)
            if 1 <= parsed <= 120:
                age_val = parsed

        # If age is not set or invalid, calculate from dob
        if age_val is None and dob_val:
            calc = calculate_age_from_dob(dob_val)
            if calc is not None:
                age_val = calc

        final_age = str(age_val) if age_val is not None else fallback_age
        return final_age, dob_val

    def extract_child_age_and_dob(self, dossier: dict, fallback_age: str = "15") -> tuple[str, str]:
        """Extracts child age and dob from dossier."""
        child_obj = dossier.get("child", {})
        if not isinstance(child_obj, dict):
            child_obj = {}

        dob_val = str(child_obj.get("dob") or child_obj.get("dateOfBirth") or "").strip()
        age_val = None
        raw_age = child_obj.get("age")
        if raw_age is not None and str(raw_age).isdigit():
            parsed = int(raw_age)
            if 0 <= parsed <= 120:
                age_val = parsed

        if age_val is None and dob_val:
            calc = calculate_age_from_dob(dob_val)
            if calc is not None:
                age_val = calc

        final_age = str(age_val) if age_val is not None else fallback_age
        return final_age, dob_val

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
