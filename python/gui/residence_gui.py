"""
GoaOnAuto Residence Certificate Declaration Automation GUI.
Powered by Raylib & MiKTeX | Dynamic Window Resizing | JetBrainsMono Font | Native File Picker.
"""
import sys
import os
import json
import argparse
import subprocess
import glob
import re
from datetime import datetime
import pyray as rl

# Ensure project root is in sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Dracula Color Palette
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

def escape_latex(text: str) -> str:
    """Escapes special LaTeX characters in text inputs."""
    if not text:
        return ""
    mapping = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
        '\\': r'\textbackslash{}'
    }
    return "".join(mapping.get(c, c) for c in text)

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

class FormField:
    def __init__(self, key: str, label: str, default_val: str = "", is_path: bool = False):
        self.key = key
        self.label = label
        self.value = default_val
        self.is_path = is_path
        self.rect = rl.Rectangle(0, 0, 0, 0)
        self.btn_rect = rl.Rectangle(0, 0, 0, 0)

class ResidenceFormState:
    def __init__(self, target_dir: str):
        self.target_dir = os.path.abspath(target_dir) if target_dir else os.path.join(project_root, "work_directory")
        self.mode = "self"  # "self" or "child"
        self.active_field_idx = 0
        self.status_msg = "Ready to customize and generate Residence Declaration"
        self.status_color = DRACULA_CYAN
        self.is_compiled = False
        self.compiled_pdf = ""
        self.compiled_tex = ""
        self.cursor_timer = 0.0
        self.tex_dirty = True
        self.last_sync_time = "Not synced yet"

        # Textures
        self.photo_texture = None
        self.sig_texture = None
        self.last_photo_path = ""
        self.last_sig_path = ""

        # Prepopulate from client directory data (residence_form_data.json or applicant_dossier.json)
        client_data = self.load_client_data()
        self.mode = client_data.get("mode", "self")

        deponent_name = client_data.get("deponent_name", "")
        deponent_age = client_data.get("age", "")
        rel_type = client_data.get("relation_type", "Daughter of")
        rel_name = client_data.get("relation_name", "")
        child_name = client_data.get("child_name", "")
        child_rel = client_data.get("child_relation", "Daughter")
        full_address = client_data.get("address", "")
        taluka = client_data.get("taluka", "Bardez")
        since_year = client_data.get("since_year", "2009")
        place = client_data.get("place", "Mapusa")
        current_date = client_data.get("date", datetime.now().strftime("%d/%m/%Y"))

        # Detect photo and signature in target dir if not already set
        photo_path = client_data.get("photo_path") or self.find_file_pattern(["*passport_photo*", "*white_bg*", "*photo*", "*.jpg", "*.png"])
        sig_path = client_data.get("sig_path") or self.find_file_pattern(["*signature*", "*sig*"])

        # Fields definition
        self.fields = [
            FormField("deponent_name", "Deponent Name", deponent_name or "Applicant Name"),
            FormField("age", "Age (Years)", deponent_age or "25"),
            FormField("relation_type", "Relation Type", rel_type or "Daughter of"),
            FormField("relation_name", "Parent / Spouse Name", rel_name),
            FormField("child_name", "Child Name (Child Mode)", child_name),
            FormField("child_relation", "Child Relation (Daughter/Son)", child_rel or "Daughter"),
            FormField("since_year", "Residing Since Year", since_year or "2009"),
            FormField("address", "Full Address", full_address or "H.No. 123, Goa"),
            FormField("taluka", "Taluka Mamlatdar Office", taluka or "Bardez"),
            FormField("place", "Place", place or "Mapusa"),
            FormField("date", "Date (DD/MM/YYYY)", current_date),
            FormField("photo_path", "Passport Photo Path", photo_path, is_path=True),
            FormField("sig_path", "Signature Path", sig_path, is_path=True)
        ]

    def load_dossier(self) -> dict:
        dossier_file = os.path.join(self.target_dir, "applicant_dossier.json")
        if os.path.exists(dossier_file):
            try:
                with open(dossier_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def load_client_data(self) -> dict:
        """
        Loads existing data for this client from residence_form_data.json or applicant_dossier.json.
        Returns a unified dict of all keyword fields.
        """
        data = {}
        # 1. Try residence_form_data.json first (contains user's prior edits)
        form_file = os.path.join(self.target_dir, "residence_form_data.json")
        if os.path.exists(form_file):
            try:
                with open(form_file, "r", encoding="utf-8") as f:
                    form_json = json.load(f)
                    if isinstance(form_json, dict):
                        data["mode"] = form_json.get("mode", "self")
                        data["deponent_name"] = form_json.get("applicantName", "")
                        data["age"] = str(form_json.get("age", ""))
                        data["relation_type"] = form_json.get("relationType", "Daughter of")
                        data["relation_name"] = form_json.get("relationName", "")
                        data["child_name"] = form_json.get("childName", "")
                        data["child_relation"] = form_json.get("childRelation", "Daughter")
                        data["since_year"] = str(form_json.get("sinceYear", ""))
                        data["address"] = form_json.get("address", "")
                        data["taluka"] = form_json.get("taluka", "Bardez")
                        data["place"] = form_json.get("place", "Mapusa")
                        data["date"] = form_json.get("declarationDate", datetime.now().strftime("%d/%m/%Y"))
                        data["photo_path"] = form_json.get("photoPath", "")
                        data["sig_path"] = form_json.get("signaturePath", "")
                        return data
            except Exception:
                pass

        # 2. Fallback to applicant_dossier.json (synthesized from scanner/OCR)
        dossier = self.load_dossier()
        deponent_name = dossier.get("name", {}).get("value", "")
        deponent_age = str(dossier.get("age", {}).get("value", ""))
        address_obj = dossier.get("address", {}).get("value", {})
        full_address = address_obj.get("full", "") if isinstance(address_obj, dict) else str(address_obj or "")
        taluka = address_obj.get("taluka", "Bardez") if isinstance(address_obj, dict) else "Bardez"
        years_in_goa = dossier.get("yearsInGoa", {}).get("value", 15)
        current_year = datetime.now().year
        since_year = str(current_year - (int(years_in_goa) if years_in_goa else 15))

        rel_obj = dossier.get("relation", {})
        rel_type = rel_obj.get("type", "Daughter of") if isinstance(rel_obj, dict) else "Daughter of"
        rel_name = rel_obj.get("name", "") if isinstance(rel_obj, dict) else ""

        child_obj = dossier.get("child", {})
        child_name = child_obj.get("name", "") if isinstance(child_obj, dict) else ""
        child_rel = child_obj.get("relation", "Daughter") if isinstance(child_obj, dict) else "Daughter"

        data["mode"] = "child" if child_name else "self"
        data["deponent_name"] = deponent_name
        data["age"] = deponent_age
        data["relation_type"] = rel_type
        data["relation_name"] = rel_name
        data["child_name"] = child_name
        data["child_relation"] = child_rel
        data["since_year"] = since_year
        data["address"] = full_address
        data["taluka"] = taluka
        data["place"] = "Mapusa"
        data["date"] = datetime.now().strftime("%d/%m/%Y")
        data["photo_path"] = dossier.get("photoPath", "")
        data["sig_path"] = dossier.get("signaturePath", "")
        return data

    def save_client_data(self) -> None:
        """
        Saves all verified details directly in the client's directory for form filling:
        1. residence_form_data.json (Direct schema for web portal automation)
        2. applicant_dossier.json (Updates/merges with user-confirmed values)
        """
        if not os.path.isdir(self.target_dir):
            return

        current_year = datetime.now().year
        since_year_str = self.get_field_val("since_year")
        try:
            since_year_int = int(since_year_str) if since_year_str else (current_year - 15)
            years_in_goa = max(0, current_year - since_year_int)
        except Exception:
            since_year_int = current_year - 15
            years_in_goa = 15

        age_str = self.get_field_val("age")
        try:
            age_val = int(age_str) if age_str.isdigit() else age_str
        except Exception:
            age_val = 25

        tex_file = os.path.join(self.target_dir, "residence_declaration.tex")
        pdf_file = os.path.join(self.target_dir, "residence_declaration.pdf")

        # 1. Direct structure for GoaOnline Portal Form Automation
        form_data = {
            "serviceType": "residence_certificate",
            "mode": self.mode,
            "applicantName": self.get_field_val("deponent_name"),
            "age": age_val,
            "relationType": self.get_field_val("relation_type"),
            "relationName": self.get_field_val("relation_name"),
            "childName": self.get_field_val("child_name") if self.mode == "child" else "",
            "childRelation": self.get_field_val("child_relation") if self.mode == "child" else "",
            "sinceYear": since_year_int,
            "yearsInGoa": years_in_goa,
            "address": self.get_field_val("address"),
            "taluka": self.get_field_val("taluka"),
            "place": self.get_field_val("place"),
            "declarationDate": self.get_field_val("date"),
            "photoPath": self.get_field_val("photo_path"),
            "signaturePath": self.get_field_val("sig_path"),
            "declarationTexPath": tex_file if os.path.exists(tex_file) else "",
            "declarationPdfPath": pdf_file if os.path.exists(pdf_file) else "",
            "updatedAt": datetime.now().isoformat()
        }

        form_json_path = os.path.join(self.target_dir, "residence_form_data.json")
        try:
            with open(form_json_path, "w", encoding="utf-8") as f:
                json.dump(form_data, f, indent=2)
        except Exception as e:
            print(f"Notice saving residence_form_data.json: {e}", file=sys.stderr)

        # 2. Update/Merge applicant_dossier.json with confirmed values
        dossier = self.load_dossier()
        dossier["name"] = {
            "value": self.get_field_val("deponent_name"),
            "confidence": 1.0,
            "sourceDoc": "User Confirmed GUI"
        }
        dossier["age"] = {
            "value": age_val,
            "confidence": 1.0,
            "sourceDoc": "User Confirmed GUI"
        }
        dossier["relation"] = {
            "type": self.get_field_val("relation_type"),
            "name": self.get_field_val("relation_name"),
            "confidence": 1.0
        }
        if self.mode == "child":
            dossier["child"] = {
                "name": self.get_field_val("child_name"),
                "relation": self.get_field_val("child_relation")
            }

        addr_obj = dossier.get("address", {}).get("value", {})
        if not isinstance(addr_obj, dict):
            addr_obj = {}
        addr_obj["full"] = self.get_field_val("address")
        addr_obj["taluka"] = self.get_field_val("taluka")
        addr_obj["state"] = "Goa"
        dossier["address"] = {
            "value": addr_obj,
            "confidence": 1.0,
            "sourceDoc": "User Confirmed GUI"
        }

        dossier["yearsInGoa"] = {
            "value": years_in_goa,
            "sinceYear": since_year_int,
            "confidence": 1.0,
            "sourceDoc": "User Confirmed GUI"
        }

        if self.get_field_val("photo_path"):
            dossier["photoPath"] = self.get_field_val("photo_path")
        if self.get_field_val("sig_path"):
            dossier["signaturePath"] = self.get_field_val("sig_path")

        if os.path.exists(tex_file):
            dossier["declarationTex"] = tex_file
        if os.path.exists(pdf_file):
            dossier["declarationPdf"] = pdf_file

        dossier_path = os.path.join(self.target_dir, "applicant_dossier.json")
        try:
            with open(dossier_path, "w", encoding="utf-8") as f:
                json.dump(dossier, f, indent=2)
        except Exception as e:
            print(f"Notice saving applicant_dossier.json: {e}", file=sys.stderr)

    def find_file_pattern(self, patterns) -> str:
        if not os.path.isdir(self.target_dir):
            return ""
        for pat in patterns:
            matches = glob.glob(os.path.join(self.target_dir, pat))
            for m in matches:
                if os.path.isfile(m) and not m.endswith(".json") and not m.endswith(".pdf") and not m.endswith(".tex"):
                    return os.path.abspath(m)
        return ""

    def get_field_val(self, key: str) -> str:
        for f in self.fields:
            if f.key == key:
                return f.value
        return ""

    def set_field_val(self, key: str, val: str):
        for f in self.fields:
            if f.key == key:
                f.value = val

def load_custom_font(font_filename: str, base_size: int = 48):
    """Loads JetBrainsMono font with crisp bilinear filtering."""
    font_path = os.path.join(project_root, "assets", "fonts", font_filename)
    if os.path.exists(font_path):
        try:
            font = rl.load_font_ex(font_path.encode('utf-8'), base_size, None, 0)
            if font and font.baseSize > 0:
                rl.set_texture_filter(font.texture, rl.TEXTURE_FILTER_BILINEAR)
                return font
        except Exception as e:
            print(f"Error loading {font_filename}: {e}", file=sys.stderr)
    return None

def sync_tex_file(state: ResidenceFormState) -> tuple[bool, str, str]:
    """
    Generates and writes residence_declaration.tex reflecting current form state.
    Uses safe lambda regex replacement to completely avoid backslash character corruption.
    """
    try:
        is_child = (state.mode == "child")
        template_name = "residence_child.tex" if is_child else "residence_self.tex"
        template_path = os.path.join(project_root, "templates", "latex", template_name)

        if not os.path.exists(template_path):
            return False, "", f"Template not found: {template_path}"

        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()

        deponent_name = escape_latex(state.get_field_val("deponent_name"))
        age = escape_latex(state.get_field_val("age"))
        rel_type = escape_latex(state.get_field_val("relation_type"))
        rel_name = escape_latex(state.get_field_val("relation_name"))
        child_name = escape_latex(state.get_field_val("child_name"))
        child_rel = escape_latex(state.get_field_val("child_relation"))
        address = escape_latex(state.get_field_val("address"))
        since_year = escape_latex(state.get_field_val("since_year"))
        taluka = escape_latex(state.get_field_val("taluka"))
        place = escape_latex(state.get_field_val("place"))
        date_str = escape_latex(state.get_field_val("date"))
        photo_path = state.get_field_val("photo_path")
        sig_path = state.get_field_val("sig_path")

        if not is_child:
            decl_pattern = r"I, [^,]+, \[Age\] years, \[Daughter/Wife\] of \[Name\], an Indian national, residing at \[Address\]"
            new_decl = f"I, {deponent_name}, {age} years, {rel_type} {rel_name}, an Indian national, residing at {address}"
            content = re.sub(decl_pattern, lambda m: new_decl, content)
            content = re.sub(r"from the year \d{4} to date", lambda m: f"from the year {since_year} to date", content)
            content = re.sub(r"office of the Mamlatdar of [^,]+ Taluka", lambda m: f"office of the Mamlatdar of {taluka} Taluka", content)
            content = re.sub(r"\\textbf\{DEPONENT: [^}]+\}", lambda m: f"\\textbf{{DEPONENT: {deponent_name}}}", content)
        else:
            decl_pattern = r"I, [^,]+, \[Age\] years, \[Wife\] of [^,]+, an Indian national, residing at \[Address\]"
            new_decl = f"I, {deponent_name}, {age} years, {rel_type} {rel_name}, an Indian national, residing at {address}"
            content = re.sub(decl_pattern, lambda m: new_decl, content)
            content = re.sub(r"My Daughter Miss\..*? is a permanent", lambda m: f"My {child_rel} {child_name} is a permanent", content)
            content = re.sub(r"from the year \d{4} to date My Daughter", lambda m: f"from the year {since_year} to date My {child_rel}", content)
            content = re.sub(r"My Daughter has not surrendered", lambda m: f"My {child_rel} has not surrendered", content)
            content = re.sub(r"my Daughter has been permanent", lambda m: f"my {child_rel} has been permanent", content)
            content = re.sub(r"Residence Certificate for my Daughter", lambda m: f"Residence Certificate for my {child_rel}", content)
            content = re.sub(r"office of the Mamlatdar of [^,]+ Taluka", lambda m: f"office of the Mamlatdar of {taluka} Taluka", content)
            content = re.sub(r"\\textbf\{DEPONENT: [^}]+\}", lambda m: f"\\textbf{{DEPONENT: {deponent_name}}}", content)

        content = re.sub(r"\\textbf\{Place:\} [^\\]+\\\\", lambda m: f"\\textbf{{Place:}} {place} \\\\", content)
        content = re.sub(r"\\textbf\{Date:\} [^\n]+", lambda m: f"\\textbf{{Date:}} {date_str}", content)

        # Photo replacement if file exists
        if photo_path and os.path.isfile(photo_path):
            clean_photo_path = os.path.abspath(photo_path).replace("\\", "/")
            photo_snippet = f'\\fbox{{\\includegraphics[width=1.2in, height=1.5in]{{"{clean_photo_path}"}}}}'
            fbox_pattern = r"\\fbox\{\\begin\{minipage\}\[t\]\[1\.5in\]\{1\.2in\}.*?\\end\{minipage\}\}"
            content = re.sub(fbox_pattern, lambda m: photo_snippet, content, flags=re.DOTALL)

        # Signature replacement if file exists
        if sig_path and os.path.isfile(sig_path):
            clean_sig_path = os.path.abspath(sig_path).replace("\\", "/")
            sig_snippet = f'\\includegraphics[width=4.5cm]{{"{clean_sig_path}"}} \\\\\n    \\rule{{6cm}}{{0.4pt}}'
            content = re.sub(r"\\rule\{6cm\}\{0\.4pt\}", lambda m: sig_snippet, content)

        # Ensure single page fit
        content = content.replace(r"\doublespacing", r"\onehalfspacing")

        out_dir = state.target_dir if os.path.isdir(state.target_dir) else project_root
        os.makedirs(out_dir, exist_ok=True)
        tex_path = os.path.join(out_dir, "residence_declaration.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(content)

        state.last_sync_time = datetime.now().strftime("%H:%M:%S")
        state.compiled_tex = tex_path
        # Auto-save all form data directly into the client directory
        state.save_client_data()
        return True, tex_path, ""
    except Exception as e:
        return False, "", str(e)

def compile_residence_pdf(state: ResidenceFormState) -> tuple[bool, str]:
    """Generates LaTeX file and compiles via pdflatex into applicant directory."""
    # First ensure .tex is completely up-to-date
    ok, tex_path, err = sync_tex_file(state)
    if not ok:
        return False, f"Failed to generate .tex file: {err}"

    out_dir = state.target_dir if os.path.isdir(state.target_dir) else project_root

    # Compile via pdflatex
    pdflatex_exe = "pdflatex"
    default_miktex = r"C:\Users\Anosh\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"
    if os.path.exists(default_miktex):
        pdflatex_exe = default_miktex

    cmd = [
        pdflatex_exe,
        "-interaction=nonstopmode",
        f"-output-directory={out_dir}",
        tex_path
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=out_dir)
        pdf_path = os.path.join(out_dir, "residence_declaration.pdf")

        if os.path.exists(pdf_path):
            state.is_compiled = True
            state.compiled_pdf = pdf_path
            state.save_client_data()
            # Clean up intermediate logs
            for ext in [".aux", ".log", ".out"]:
                tmp_f = os.path.join(out_dir, f"residence_declaration{ext}")
                if os.path.exists(tmp_f):
                    try:
                        os.remove(tmp_f)
                    except Exception:
                        pass
            return True, pdf_path
        else:
            return False, f"pdflatex compilation failed (Code {proc.returncode}): {proc.stderr[:300]}"
    except Exception as e:
        return False, f"pdflatex execution error: {str(e)}"

def draw_text_clean(font, text: str, x: float, y: float, font_size: int, color: rl.Color):
    """Renders crisp text using loaded JetBrainsMono TTF font."""
    try:
        raw_bytes = text.encode('utf-8', 'ignore')
        if font and font.baseSize > 0:
            rl.draw_text_ex(font, raw_bytes, rl.Vector2(float(x), float(y)), float(font_size), 1.0, color)
        else:
            rl.draw_text(raw_bytes, int(x), int(y), font_size, color)
    except Exception:
        pass

def measure_text_clean(font, text: str, font_size: int) -> float:
    """Measures exact text width using loaded JetBrainsMono TTF font."""
    try:
        raw_bytes = text.encode('utf-8', 'ignore')
        if font and font.baseSize > 0:
            return float(rl.measure_text_ex(font, raw_bytes, float(font_size), 1.0).x)
        else:
            return float(rl.measure_text(raw_bytes, font_size))
    except Exception:
        return float(len(text) * font_size * 0.6)

def main():
    parser = argparse.ArgumentParser(description="GoaOnAuto Residence Certificate Automation GUI")
    parser.add_argument("--dir", default="", help="Applicant folder directory path")
    parser.add_argument("--no-prompt", action="store_true", help="Do not prompt for missing files on launch")
    args = parser.parse_args()

    state = ResidenceFormState(args.dir)

    # Window Configuration: Resizable, smooth MSAA, Always runs
    rl.set_config_flags(rl.FLAG_WINDOW_RESIZABLE | rl.FLAG_MSAA_4X_HINT | rl.FLAG_WINDOW_ALWAYS_RUN)

    init_w = 1260
    init_h = 820
    rl.init_window(init_w, init_h, "GoaOnAuto - Residence Certificate LaTeX Declaration Generator")
    rl.set_target_fps(60)

    # Dynamic monitor fitting & centering
    try:
        mon = rl.get_current_monitor()
        mon_w = rl.get_monitor_width(mon)
        mon_h = rl.get_monitor_height(mon)
        if mon_w > 900 and mon_h > 700:
            target_w = min(1380, mon_w - 60)
            target_h = min(900, mon_h - 80)
            rl.set_window_size(target_w, target_h)
            rl.set_window_position((mon_w - target_w) // 2, max(20, (mon_h - target_h) // 2 - 20))
    except Exception:
        pass

    # Prompt if photo path is not correct/missing on startup (unless --no-prompt)
    if not args.no_prompt:
        current_photo = state.get_field_val("photo_path")
        if not current_photo or not os.path.isfile(current_photo):
            picked_photo = open_file_dialog("Photo path not found/incorrect. Please select Passport Photo (.jpg, .png):")
            if picked_photo:
                state.set_field_val("photo_path", picked_photo)
                state.tex_dirty = True

    # Load high-DPI JetBrainsMono Fonts (base size 48 with Bilinear texture filtering)
    font_regular = load_custom_font("JetBrainsMono-Regular.ttf", 48)
    font_bold = load_custom_font("JetBrainsMono-Bold.ttf", 48)

    # Perform initial .tex sync so the file exists right away
    sync_tex_file(state)
    state.tex_dirty = False

    while not rl.window_should_close():
        dt = rl.get_frame_time()
        state.cursor_timer += dt

        w = rl.get_screen_width()
        h = rl.get_screen_height()

        # Dynamic Scale Factor based on window dimensions
        scale = max(0.75, min(1.6, w / 1260.0))
        scale_y = max(0.75, min(1.6, h / 820.0))

        title_size = int(21 * scale)
        label_size = max(11, int(13.5 * scale))
        input_size = max(12, int(14.5 * scale))
        btn_size = max(12, int(14 * scale))

        mouse_pos = rl.get_mouse_position()
        is_mouse_down = rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT)

        # -----------------------------
        # Live Sync .tex if state changed
        # -----------------------------
        if state.tex_dirty:
            sync_tex_file(state)
            state.tex_dirty = False

        # -----------------------------
        # Handle Texture Loads/Updates
        # -----------------------------
        curr_photo = state.get_field_val("photo_path")
        if curr_photo != state.last_photo_path:
            state.last_photo_path = curr_photo
            if state.photo_texture:
                rl.unload_texture(state.photo_texture)
                state.photo_texture = None
            if curr_photo and os.path.isfile(curr_photo):
                try:
                    tex = rl.load_texture(curr_photo.encode('utf-8'))
                    if tex and tex.id > 0:
                        rl.set_texture_filter(tex, rl.TEXTURE_FILTER_BILINEAR)
                        state.photo_texture = tex
                except Exception:
                    pass

        curr_sig = state.get_field_val("sig_path")
        if curr_sig != state.last_sig_path:
            state.last_sig_path = curr_sig
            if state.sig_texture:
                rl.unload_texture(state.sig_texture)
                state.sig_texture = None
            if curr_sig and os.path.isfile(curr_sig):
                try:
                    tex = rl.load_texture(curr_sig.encode('utf-8'))
                    if tex and tex.id > 0:
                        rl.set_texture_filter(tex, rl.TEXTURE_FILTER_BILINEAR)
                        state.sig_texture = tex
                except Exception:
                    pass

        # -----------------------------
        # Visible Fields Calculation
        # -----------------------------
        visible_fields = [f for f in state.fields if state.mode == "child" or not f.key.startswith("child_")]

        # Clamp active index to visible fields
        if state.active_field_idx >= len(visible_fields):
            state.active_field_idx = 0
        active_f = visible_fields[state.active_field_idx] if visible_fields else None

        # -----------------------------
        # Keyboard Input Handling
        # -----------------------------
        if rl.is_key_pressed(rl.KEY_TAB):
            if rl.is_key_down(rl.KEY_LEFT_SHIFT) or rl.is_key_down(rl.KEY_RIGHT_SHIFT):
                state.active_field_idx = (state.active_field_idx - 1) % len(visible_fields)
            else:
                state.active_field_idx = (state.active_field_idx + 1) % len(visible_fields)

        if active_f:
            # Backspace
            if rl.is_key_pressed(rl.KEY_BACKSPACE) or (rl.is_key_down(rl.KEY_BACKSPACE) and state.cursor_timer > 0.4):
                if len(active_f.value) > 0:
                    active_f.value = active_f.value[:-1]
                    state.tex_dirty = True
                    if rl.is_key_down(rl.KEY_BACKSPACE):
                        state.cursor_timer = 0.35

            # Paste support (Ctrl+V)
            if (rl.is_key_down(rl.KEY_LEFT_CONTROL) or rl.is_key_down(rl.KEY_RIGHT_CONTROL)) and rl.is_key_pressed(rl.KEY_V):
                try:
                    import tkinter as tk
                    root = tk.Tk()
                    root.withdraw()
                    clipboard = root.clipboard_get()
                    root.destroy()
                    if clipboard:
                        active_f.value += clipboard.replace("\n", " ").replace("\r", "")
                        state.tex_dirty = True
                except Exception:
                    pass

            # Char input
            char_code = rl.get_char_pressed()
            while char_code > 0:
                if 32 <= char_code <= 126:
                    active_f.value += chr(char_code)
                    state.tex_dirty = True
                char_code = rl.get_char_pressed()

        # -----------------------------
        # Render Frame
        # -----------------------------
        rl.begin_drawing()
        rl.clear_background(DRACULA_BG)

        # 1. Header Bar
        header_h = int(54 * scale_y)
        rl.draw_rectangle(0, 0, w, header_h, DRACULA_CURRENT_LINE)
        rl.draw_line(0, header_h, w, header_h, DRACULA_COMMENT)

        draw_text_clean(font_bold, "🏛️ GoaOnAuto - Residence Certificate Automation", 24 * scale, 15 * scale_y, title_size, DRACULA_PURPLE)

        # Mode Selector Buttons in Header
        mode_btn_w = int(145 * scale)
        mode_btn_h = int(32 * scale_y)
        self_btn_x = w - (mode_btn_w * 2) - int(30 * scale)
        child_btn_x = w - mode_btn_w - int(20 * scale)
        btn_y = int(11 * scale_y)

        self_rect = rl.Rectangle(self_btn_x, btn_y, mode_btn_w, mode_btn_h)
        child_rect = rl.Rectangle(child_btn_x, btn_y, mode_btn_w, mode_btn_h)

        if is_mouse_down and rl.check_collision_point_rec(mouse_pos, self_rect):
            if state.mode != "self":
                state.mode = "self"
                state.tex_dirty = True
                state.status_msg = "Switched to Self Declaration Mode (residence_self.tex)"
                state.status_color = DRACULA_CYAN
        if is_mouse_down and rl.check_collision_point_rec(mouse_pos, child_rect):
            if state.mode != "child":
                state.mode = "child"
                state.tex_dirty = True
                state.status_msg = "Switched to Child Declaration Mode (residence_child.tex)"
                state.status_color = DRACULA_YELLOW

        self_bg = DRACULA_PURPLE if state.mode == "self" else DRACULA_BG
        self_fg = DRACULA_BG if state.mode == "self" else DRACULA_FG
        rl.draw_rectangle_rounded(self_rect, 0.3, 6, self_bg)
        rl.draw_rectangle_rounded_lines(self_rect, 0.3, 6, DRACULA_COMMENT)
        draw_text_clean(font_bold, "Self Mode", self_btn_x + int(28 * scale), btn_y + int(7 * scale_y), btn_size, self_fg)

        child_bg = DRACULA_YELLOW if state.mode == "child" else DRACULA_BG
        child_fg = DRACULA_BG if state.mode == "child" else DRACULA_FG
        rl.draw_rectangle_rounded(child_rect, 0.3, 6, child_bg)
        rl.draw_rectangle_rounded_lines(child_rect, 0.3, 6, DRACULA_COMMENT)
        draw_text_clean(font_bold, "Child Mode", child_btn_x + int(24 * scale), btn_y + int(7 * scale_y), btn_size, child_fg)

        # 2. Main Layout Split (Left = Dynamic Form, Right = Live Asset Preview & Actions)
        left_w = int(w * 0.61)
        right_x = left_w + int(20 * scale)
        right_w = w - right_x - int(20 * scale)
        content_y = header_h + int(14 * scale_y)
        footer_h = int(60 * scale_y)
        available_h = h - content_y - footer_h

        # Dynamic Row Height based on visible field count and available height
        num_fields = len(visible_fields)
        row_h = min(int(52 * scale_y), max(int(36 * scale_y), int(available_h / (num_fields + 0.2))))
        inp_h = max(26, int(row_h * 0.74))

        for i, field in enumerate(visible_fields):
            curr_y = content_y + (i * row_h)
            lbl_x = int(24 * scale)
            lbl_w = int(210 * scale)
            inp_x = lbl_x + lbl_w + int(10 * scale)

            # Check if path field is invalid
            is_invalid_path = field.is_path and field.value and not os.path.isfile(field.value)
            is_empty_required_photo = (field.key == "photo_path" and not field.value)

            browse_btn_w = int(74 * scale) if field.is_path else 0
            inp_w = left_w - inp_x - (browse_btn_w + int(12 * scale) if field.is_path else 0)

            field.rect = rl.Rectangle(inp_x, curr_y, inp_w, inp_h)

            # Draw Label
            label_col = DRACULA_ORANGE if (is_invalid_path or is_empty_required_photo) else DRACULA_FG
            draw_text_clean(font_bold, field.label, lbl_x, curr_y + int((inp_h - label_size) / 2), label_size, label_col)

            # Check click focus or launch picker on click if path is invalid
            if is_mouse_down and rl.check_collision_point_rec(mouse_pos, field.rect):
                state.active_field_idx = i
                if field.is_path and (is_invalid_path or not field.value):
                    picked = open_file_dialog(f"Path not correct. Select {field.label}")
                    if picked:
                        field.value = picked
                        state.tex_dirty = True

            is_focused = (active_f == field)
            box_bg = DRACULA_CURRENT_LINE if is_focused else DRACULA_BG
            if is_invalid_path or is_empty_required_photo:
                border_color = DRACULA_RED
            elif is_focused:
                border_color = DRACULA_CYAN
            else:
                border_color = DRACULA_COMMENT

            rl.draw_rectangle_rounded(field.rect, 0.25, 6, box_bg)
            rl.draw_rectangle_rounded_lines(field.rect, 0.25, 6, border_color)

            # Display text with overflow clipping
            display_val = field.value
            char_w = max(6.0, measure_text_clean(font_regular, "W", input_size))
            max_char_len = max(10, int((inp_w - 20) / (char_w * 0.75)))
            if len(display_val) > max_char_len:
                display_val = "..." + display_val[-(max_char_len - 3):]

            text_y = curr_y + int((inp_h - input_size) / 2)
            draw_text_clean(font_regular, display_val, inp_x + int(10 * scale), text_y, input_size, DRACULA_FG)

            # Blinking cursor
            if is_focused and (int(state.cursor_timer * 2.5) % 2 == 0):
                tw = measure_text_clean(font_regular, display_val, input_size)
                cursor_x = inp_x + int(10 * scale) + tw + 2
                cursor_top = curr_y + int(4 * scale_y)
                cursor_bot = curr_y + inp_h - int(4 * scale_y)
                rl.draw_line(int(cursor_x), int(cursor_top), int(cursor_x), int(cursor_bot), DRACULA_CYAN)

            # File Finder Button for path fields
            if field.is_path:
                btn_browse_x = inp_x + inp_w + int(10 * scale)
                field.btn_rect = rl.Rectangle(btn_browse_x, curr_y, browse_btn_w, inp_h)

                btn_hover = rl.check_collision_point_rec(mouse_pos, field.btn_rect)
                btn_bg = DRACULA_PURPLE if btn_hover else (DRACULA_RED if (is_invalid_path or is_empty_required_photo) else DRACULA_CURRENT_LINE)
                btn_fg = DRACULA_BG if btn_hover else DRACULA_FG

                rl.draw_rectangle_rounded(field.btn_rect, 0.25, 6, btn_bg)
                rl.draw_rectangle_rounded_lines(field.btn_rect, 0.25, 6, DRACULA_COMMENT)
                browse_label = "Browse" if not (is_invalid_path or is_empty_required_photo) else "Fix Path"
                draw_text_clean(font_bold, browse_label, btn_browse_x + int(10 * scale), text_y, max(10, int(12 * scale)), btn_fg)

                if is_mouse_down and btn_hover:
                    prompt = f"Select {field.label}" if not is_invalid_path else f"File not found at specified path. Please select {field.label}"
                    picked = open_file_dialog(prompt)
                    if picked:
                        field.value = picked
                        state.tex_dirty = True

        # 3. Right Column: Document Previews & Generation Actions
        preview_box_rect = rl.Rectangle(right_x, content_y, right_w, available_h)
        rl.draw_rectangle_rounded(preview_box_rect, 0.05, 8, DRACULA_CURRENT_LINE)
        rl.draw_rectangle_rounded_lines(preview_box_rect, 0.05, 8, DRACULA_COMMENT)

        draw_text_clean(font_bold, "📄 Live Preview & Document Assets", right_x + int(16 * scale), content_y + int(14 * scale_y), int(16 * scale), DRACULA_CYAN)

        # Photo Preview Box
        photo_box_w = int(140 * scale)
        photo_box_h = int(175 * scale_y)
        photo_box_x = right_x + int(20 * scale)
        photo_box_y = content_y + int(46 * scale_y)

        photo_rect = rl.Rectangle(photo_box_x, photo_box_y, photo_box_w, photo_box_h)
        rl.draw_rectangle(photo_box_x, photo_box_y, photo_box_w, photo_box_h, DRACULA_BG)
        photo_border = DRACULA_COMMENT if (state.photo_texture and state.photo_texture.id > 0) else DRACULA_RED
        rl.draw_rectangle_lines(photo_box_x, photo_box_y, photo_box_w, photo_box_h, photo_border)

        if state.photo_texture and state.photo_texture.id > 0:
            tex_w = state.photo_texture.width
            tex_h = state.photo_texture.height
            src_rect = rl.Rectangle(0, 0, tex_w, tex_h)
            dst_rect = rl.Rectangle(photo_box_x + 2, photo_box_y + 2, photo_box_w - 4, photo_box_h - 4)
            rl.draw_texture_pro(state.photo_texture, src_rect, dst_rect, rl.Vector2(0, 0), 0.0, rl.WHITE)
        else:
            draw_text_clean(font_regular, "⚠️ Photo Missing\nClick to Browse", photo_box_x + int(18 * scale), photo_box_y + int(70 * scale_y), int(12 * scale), DRACULA_RED)

        # Click on Photo box triggers file picker
        if is_mouse_down and rl.check_collision_point_rec(mouse_pos, photo_rect):
            picked_photo = open_file_dialog("Select Passport Photo for Applicant")
            if picked_photo:
                state.set_field_val("photo_path", picked_photo)
                state.tex_dirty = True

        draw_text_clean(font_bold, "Passport Photo", photo_box_x + int(18 * scale), photo_box_y + photo_box_h + int(6 * scale_y), int(13 * scale), DRACULA_FG)

        # Signature Preview Box
        sig_box_w = right_w - photo_box_w - int(50 * scale)
        sig_box_h = int(105 * scale_y)
        sig_box_x = photo_box_x + photo_box_w + int(20 * scale)
        sig_box_y = photo_box_y + int(30 * scale_y)
        sig_rect = rl.Rectangle(sig_box_x, sig_box_y, sig_box_w, sig_box_h)

        rl.draw_rectangle(sig_box_x, sig_box_y, sig_box_w, sig_box_h, DRACULA_BG)
        rl.draw_rectangle_lines(sig_box_x, sig_box_y, sig_box_w, sig_box_h, DRACULA_COMMENT)

        if state.sig_texture and state.sig_texture.id > 0:
            tex_w = state.sig_texture.width
            tex_h = state.sig_texture.height
            src_rect = rl.Rectangle(0, 0, tex_w, tex_h)
            dst_rect = rl.Rectangle(sig_box_x + 2, sig_box_y + 2, sig_box_w - 4, sig_box_h - 4)
            rl.draw_texture_pro(state.sig_texture, src_rect, dst_rect, rl.Vector2(0, 0), 0.0, rl.WHITE)
        else:
            draw_text_clean(font_regular, "Signature (Optional)\nClick to Browse", sig_box_x + int(20 * scale), sig_box_y + int(40 * scale_y), int(12 * scale), DRACULA_COMMENT)

        # Click on Signature box triggers file picker
        if is_mouse_down and rl.check_collision_point_rec(mouse_pos, sig_rect):
            picked_sig = open_file_dialog("Select Signature Image (Optional)")
            if picked_sig:
                state.set_field_val("sig_path", picked_sig)
                state.tex_dirty = True

        draw_text_clean(font_bold, "Deponent Signature", sig_box_x + int(10 * scale), sig_box_y + sig_box_h + int(6 * scale_y), int(13 * scale), DRACULA_FG)

        # Live Synchronization Badge
        info_y = photo_box_y + photo_box_h + int(35 * scale_y)
        rl.draw_line(right_x + int(16 * scale), info_y, right_x + right_w - int(16 * scale), info_y, DRACULA_COMMENT)

        template_used = "residence_child.tex" if state.mode == "child" else "residence_self.tex"
        draw_text_clean(font_regular, f"Template: templates/latex/{template_used}", right_x + int(20 * scale), info_y + int(12 * scale_y), int(13 * scale), DRACULA_PINK)

        sync_badge_text = f"🟢 residence_declaration.tex (Live in Sync: {state.last_sync_time})"
        draw_text_clean(font_bold, sync_badge_text, right_x + int(20 * scale), info_y + int(34 * scale_y), max(10, int(11.5 * scale)), DRACULA_GREEN)

        form_badge_text = "💾 residence_form_data.json & dossier (Auto-Saved)"
        draw_text_clean(font_bold, form_badge_text, right_x + int(20 * scale), info_y + int(53 * scale_y), max(10, int(11.5 * scale)), DRACULA_CYAN)

        dir_display = state.target_dir
        if len(dir_display) > 42:
            dir_display = "..." + dir_display[-39:]
        draw_text_clean(font_regular, f"Client Dir: {dir_display}", right_x + int(20 * scale), info_y + int(72 * scale_y), max(10, int(11 * scale)), DRACULA_COMMENT)

        # Generate & Compile Action Button
        gen_btn_w = right_w - int(40 * scale)
        gen_btn_h = int(50 * scale_y)
        gen_btn_x = right_x + int(20 * scale)
        gen_btn_y = content_y + available_h - gen_btn_h - int(20 * scale_y)

        gen_rect = rl.Rectangle(gen_btn_x, gen_btn_y, gen_btn_w, gen_btn_h)
        gen_hover = rl.check_collision_point_rec(mouse_pos, gen_rect)
        gen_bg = DRACULA_GREEN if gen_hover else rl.Color(60, 200, 100, 255)

        rl.draw_rectangle_rounded(gen_rect, 0.3, 8, gen_bg)
        rl.draw_rectangle_rounded_lines(gen_rect, 0.3, 8, DRACULA_FG)
        btn_caption = "⚡ GENERATE & COMPILE PDF"
        btn_tw = measure_text_clean(font_bold, btn_caption, int(16 * scale))
        draw_text_clean(font_bold, btn_caption, gen_btn_x + (gen_btn_w - btn_tw) / 2, gen_btn_y + int(15 * scale_y), int(16 * scale), DRACULA_BG)

        if is_mouse_down and gen_hover:
            # Check if photo path is valid or missing; ask user via native file finder UI if not correct!
            photo_val = state.get_field_val("photo_path")
            if not photo_val or not os.path.isfile(photo_val):
                state.status_msg = "⚠️ Photo path not correct. Asking for photo via file finder UI..."
                state.status_color = DRACULA_ORANGE
                picked_photo = open_file_dialog("Passport Photo is required. Please select applicant photo (.jpg, .png):")
                if picked_photo:
                    state.set_field_val("photo_path", picked_photo)
                    state.tex_dirty = True
                    photo_val = picked_photo
                else:
                    state.status_msg = "⚠️ Valid passport photo path is required to compile Residence Declaration."
                    state.status_color = DRACULA_RED

            if photo_val and os.path.isfile(photo_val):
                state.status_msg = "Compiling LaTeX via pdflatex..."
                state.status_color = DRACULA_YELLOW
                success, msg = compile_residence_pdf(state)
                if success:
                    state.status_msg = f"✅ Success! PDF generated: {os.path.basename(msg)}"
                    state.status_color = DRACULA_GREEN
                    state.is_compiled = True
                    state.compiled_pdf = msg
                    try:
                        os.startfile(msg)
                    except Exception:
                        pass
                else:
                    state.status_msg = f"❌ Compilation Error: {msg}"
                    state.status_color = DRACULA_RED

        # 4. Footer Status Bar
        footer_y = h - footer_h
        rl.draw_rectangle(0, footer_y, w, footer_h, DRACULA_CURRENT_LINE)
        rl.draw_line(0, footer_y, w, footer_h, DRACULA_COMMENT)

        draw_text_clean(font_bold, state.status_msg, 24 * scale, footer_y + int(20 * scale_y), int(14.5 * scale), state.status_color)

        if state.is_compiled and state.compiled_pdf:
            open_btn_w = int(140 * scale)
            open_btn_h = int(34 * scale_y)
            open_btn_x = w - open_btn_w - int(24 * scale)
            open_btn_y = footer_y + int(13 * scale_y)
            open_rect = rl.Rectangle(open_btn_x, open_btn_y, open_btn_w, open_btn_h)

            open_hover = rl.check_collision_point_rec(mouse_pos, open_rect)
            open_bg = DRACULA_CYAN if open_hover else DRACULA_BG
            open_fg = DRACULA_BG if open_hover else DRACULA_CYAN

            rl.draw_rectangle_rounded(open_rect, 0.3, 6, open_bg)
            rl.draw_rectangle_rounded_lines(open_rect, 0.3, 6, DRACULA_CYAN)
            draw_text_clean(font_bold, "📂 Open PDF", open_btn_x + int(28 * scale), open_btn_y + int(8 * scale_y), int(14 * scale), open_fg)

            if is_mouse_down and open_hover:
                try:
                    os.startfile(state.compiled_pdf)
                except Exception:
                    pass

        rl.end_drawing()

    # Cleanup textures and fonts
    if state.photo_texture:
        rl.unload_texture(state.photo_texture)
    if state.sig_texture:
        rl.unload_texture(state.sig_texture)
    if font_regular and font_regular.baseSize > 0:
        rl.unload_font(font_regular)
    if font_bold and font_bold.baseSize > 0:
        rl.unload_font(font_bold)

    rl.close_window()

if __name__ == "__main__":
    main()
