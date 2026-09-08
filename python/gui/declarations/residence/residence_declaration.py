"""
Residence Certificate Declaration Module.
Single Responsibility: Handles residence declaration fields, data loading/saving, and LaTeX synthesis.
"""
from __future__ import annotations
import os
import json
import re
from datetime import datetime
from ..base import BaseDeclaration
from ...core.widgets import FormField
from ...core.latex_compiler import escape_latex

class ResidenceDeclaration(BaseDeclaration):
    """Encapsulates Residence Certificate declaration logic (Self & Child modes)."""

    def __init__(self, target_dir: str):
        super().__init__(target_dir)
        self.declaration_id = "residence"
        self.title = "🏛️ GoaOnAuto - Residence Certificate Automation"
        self.service_id = "REV05"
        self.supported_modes = ["self", "child"]

        self.load_data()

    def get_output_tex_path(self) -> str:
        return os.path.join(self.target_dir, "residence_declaration.tex")

    def get_output_pdf_path(self) -> str:
        return os.path.join(self.target_dir, "residence_declaration.pdf")

    def load_data(self) -> None:
        """Loads data from residence_form_data.json or applicant_dossier.json."""
        data: dict = {}

        # 1. Try residence_form_data.json first
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
            except Exception:
                pass

        # 2. Fallback to applicant_dossier.json
        if not data:
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

        self.mode = data.get("mode", "self")

        photo_path = data.get("photo_path") or self.find_file_pattern(["*passport_photo*", "*white_bg*", "*photo*", "*.jpg", "*.png"])
        sig_path = data.get("sig_path") or self.find_file_pattern(["*signature*", "*sig*"])

        self.fields = [
            FormField("deponent_name", "Deponent Name", data.get("deponent_name") or "Applicant Name", is_required=True),
            FormField("age", "Age (Years)", data.get("age") or "25", is_required=True),
            FormField("relation_type", "Relation Type", data.get("relation_type") or "Daughter of"),
            FormField("relation_name", "Parent / Spouse Name", data.get("relation_name") or ""),
            FormField("child_name", "Child Name (Child Mode)", data.get("child_name") or ""),
            FormField("child_relation", "Child Relation (Daughter/Son)", data.get("child_relation") or "Daughter"),
            FormField("since_year", "Residing Since Year", data.get("since_year") or "2009", is_required=True),
            FormField("address", "Full Address", data.get("address") or "H.No. 123, Goa", is_required=True),
            FormField("taluka", "Taluka Mamlatdar Office", data.get("taluka") or "Bardez"),
            FormField("place", "Place", data.get("place") or "Mapusa"),
            FormField("date", "Date (DD/MM/YYYY)", data.get("date") or datetime.now().strftime("%d/%m/%Y")),
            FormField("photo_path", "Passport Photo Path", photo_path, is_path=True, is_required=True),
            FormField("sig_path", "Signature Path", sig_path, is_path=True)
        ]

    def save_data(self) -> None:
        """Saves residence_form_data.json and updates applicant_dossier.json."""
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

        tex_file = self.get_output_tex_path()
        pdf_file = self.get_output_pdf_path()

        # 1. Save residence_form_data.json
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
        except Exception:
            pass

        # 2. Update applicant_dossier.json
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
        except Exception:
            pass

    def generate_tex(self) -> tuple[bool, str, str]:
        """Synthesizes residence_declaration.tex reflecting current form state."""
        try:
            is_child = (self.mode == "child")
            template_name = "residence_child.tex" if is_child else "residence_self.tex"
            template_path = self.get_template_path(template_name)

            if not os.path.exists(template_path):
                return False, "", f"Template not found: {template_path}"

            with open(template_path, "r", encoding="utf-8") as f:
                content = f.read()

            deponent_name = escape_latex(self.get_field_val("deponent_name"))
            age = escape_latex(self.get_field_val("age"))
            rel_type = escape_latex(self.get_field_val("relation_type"))
            rel_name = escape_latex(self.get_field_val("relation_name"))
            child_name = escape_latex(self.get_field_val("child_name"))
            child_rel = escape_latex(self.get_field_val("child_relation"))
            address = escape_latex(self.get_field_val("address"))
            since_year = escape_latex(self.get_field_val("since_year"))
            taluka = escape_latex(self.get_field_val("taluka"))
            place = escape_latex(self.get_field_val("place"))
            date_str = escape_latex(self.get_field_val("date"))
            photo_path = self.get_field_val("photo_path")
            sig_path = self.get_field_val("sig_path")

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

            content = self.inject_photo_and_sig(content, photo_path, sig_path)
            content = content.replace(r"\doublespacing", r"\onehalfspacing")

            os.makedirs(self.target_dir, exist_ok=True)
            tex_path = self.get_output_tex_path()
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.save_data()
            return True, tex_path, ""
        except Exception as e:
            return False, "", str(e)
