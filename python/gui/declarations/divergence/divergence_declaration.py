"""
Divergence Certificate Declaration Module.
Single Responsibility: Handles Divergence of Name declaration fields, data loading/saving, and LaTeX synthesis.
"""
from __future__ import annotations
import os
import json
import re
from datetime import datetime
from ..base import BaseDeclaration, calculate_age_from_dob
from ...core.widgets import FormField
from ...core.latex_compiler import escape_latex

class DivergenceDeclaration(BaseDeclaration):
    """Encapsulates Divergence Certificate declaration logic."""

    def __init__(self, target_dir: str):
        super().__init__(target_dir)
        self.declaration_id = "divergence"
        self.title = "🏛️ GoaOnAuto - Divergence Certificate Declaration"
        self.service_id = "REV09"
        self.supported_modes = ["self"]

        self.load_data()

    def get_output_tex_path(self) -> str:
        return os.path.join(self.target_dir, "divergence_declaration.tex")

    def get_output_pdf_path(self) -> str:
        return os.path.join(self.target_dir, "divergence_declaration.pdf")

    def load_data(self) -> None:
        """Loads data from divergence_form_data.json or applicant_dossier.json."""
        data: dict = {}

        form_file = os.path.join(self.target_dir, "divergence_form_data.json")
        if os.path.exists(form_file):
            try:
                with open(form_file, "r", encoding="utf-8") as f:
                    form_json = json.load(f)
                    if isinstance(form_json, dict):
                        data = form_json
            except Exception:
                pass

        if not data:
            dossier = self.load_dossier()
            deponent_name = dossier.get("name", {}).get("value", "")
            address_obj = dossier.get("address", {}).get("value", {})
            full_address = address_obj.get("full", "") if isinstance(address_obj, dict) else str(address_obj or "")
            taluka = address_obj.get("taluka", "Bardez") if isinstance(address_obj, dict) else "Bardez"

            rel_obj = dossier.get("relation", {})
            rel_name = rel_obj.get("name", "") if isinstance(rel_obj, dict) else ""

            deponent_age, deponent_dob = self.extract_age_and_dob(dossier, fallback_age="50")

            data = {
                "deponent_name": deponent_name or "Applicant Name",
                "age": deponent_age,
                "dob": deponent_dob,
                "spouse_name": rel_name,
                "birth_cert_name": deponent_name or "Name On Birth Cert",
                "aadhaar_name": deponent_name or "Name On Aadhaar",
                "daughter_cert_name": deponent_name or "Name On Other Cert",
                "address": full_address or "H.No. 123, Goa",
                "village": "Calangute",
                "taluka": taluka,
                "place": "Mapusa",
                "date": datetime.now().strftime("%d/%m/%Y"),
                "photo_path": dossier.get("photoPath", ""),
                "sig_path": dossier.get("signaturePath", "")
            }

        photo_path = data.get("photo_path") or self.find_file_pattern(["*passport_photo*", "*white_bg*", "*photo*", "*.jpg", "*.png"])
        sig_path = data.get("sig_path") or self.find_file_pattern(["*signature*", "*sig*"])

        deponent_age = str(data.get("age") or "")
        dob_str = str(data.get("dob") or "")
        if (not deponent_age or not deponent_age.isdigit()) and dob_str:
            calc = calculate_age_from_dob(dob_str)
            deponent_age = str(calc) if calc is not None else "50"
        if not deponent_age:
            deponent_age = "50"

        self.fields = [
            FormField("deponent_name", "Deponent Name", data.get("deponent_name") or "Applicant Name", is_required=True),
            FormField("age", "Age (Years)", deponent_age, is_required=True),
            FormField("dob", "Date of Birth (DD/MM/YYYY)", dob_str),
            FormField("spouse_name", "Spouse / Parent Name", data.get("spouse_name") or ""),
            FormField("birth_cert_name", "Name on Birth Certificate", data.get("birth_cert_name") or "Name as per Birth Cert", is_required=True),
            FormField("aadhaar_name", "Name on Aadhaar Card", data.get("aadhaar_name") or "Name as per Aadhaar", is_required=True),
            FormField("daughter_cert_name", "Name on Child/Other Cert", data.get("daughter_cert_name") or "Name as per Other Doc", is_required=True),
            FormField("address", "Full Residential Address", data.get("address") or "H.No. 123, Goa", is_required=True),
            FormField("village", "Village / Town", data.get("village") or "Calangute"),
            FormField("taluka", "Taluka Mamlatdar Office", data.get("taluka") or "Bardez"),
            FormField("place", "Place", data.get("place") or "Mapusa"),
            FormField("date", "Date (DD/MM/YYYY)", data.get("date") or datetime.now().strftime("%d/%m/%Y")),
            FormField("photo_path", "Passport Photo Path", photo_path, is_path=True, is_required=True),
            FormField("sig_path", "Signature Path", sig_path, is_path=True)
        ]

    def save_data(self) -> None:
        """Saves divergence_form_data.json and updates applicant_dossier.json."""
        if not os.path.isdir(self.target_dir):
            return

        dob_val = self.get_field_val("dob")
        age_str = self.get_field_val("age")
        if (not age_str or not age_str.isdigit()) and dob_val:
            calc = calculate_age_from_dob(dob_val)
            age_val = calc if calc is not None else 50
        else:
            try:
                age_val = int(age_str) if age_str.isdigit() else 50
            except Exception:
                age_val = 50

        form_data = {
            "serviceType": "divergence_certificate",
            "applicantName": self.get_field_val("deponent_name"),
            "age": age_val,
            "dob": dob_val,
            "spouseName": self.get_field_val("spouse_name"),
            "birthCertName": self.get_field_val("birth_cert_name"),
            "aadhaarName": self.get_field_val("aadhaar_name"),
            "otherDocName": self.get_field_val("daughter_cert_name"),
            "address": self.get_field_val("address"),
            "village": self.get_field_val("village"),
            "taluka": self.get_field_val("taluka"),
            "place": self.get_field_val("place"),
            "declarationDate": self.get_field_val("date"),
            "photoPath": self.get_field_val("photo_path"),
            "signaturePath": self.get_field_val("sig_path"),
            "declarationTexPath": self.get_output_tex_path(),
            "declarationPdfPath": self.get_output_pdf_path(),
            "updatedAt": datetime.now().isoformat()
        }

        form_file = os.path.join(self.target_dir, "divergence_form_data.json")
        try:
            with open(form_file, "w", encoding="utf-8") as f:
                json.dump(form_data, f, indent=2)
        except Exception:
            pass

        # Update applicant_dossier.json
        dossier = self.load_dossier()
        dossier["name"] = {
            "value": self.get_field_val("deponent_name"),
            "confidence": 1.0,
            "sourceDoc": "User Confirmed GUI"
        }
        dossier["age"] = {
            "value": age_val,
            "confidence": 1.0,
            "sourceDoc": "User Confirmed GUI (Calculated from DOB)" if dob_val else "User Confirmed GUI"
        }
        if dob_val:
            dossier["dob"] = {
                "value": dob_val,
                "confidence": 1.0,
                "sourceDoc": "User Confirmed GUI"
            }

        dossier_path = os.path.join(self.target_dir, "applicant_dossier.json")
        try:
            with open(dossier_path, "w", encoding="utf-8") as f:
                json.dump(dossier, f, indent=2)
        except Exception:
            pass

    def generate_tex(self) -> tuple[bool, str, str]:
        """Synthesizes divergence_declaration.tex reflecting current form state."""
        try:
            template_path = self.get_template_path("divergence.tex")
            if not os.path.exists(template_path):
                return False, "", f"Template not found: {template_path}"

            with open(template_path, "r", encoding="utf-8") as f:
                content = f.read()

            deponent_name = escape_latex(self.get_field_val("deponent_name"))
            age_raw = self.get_field_val("age")
            dob_raw = self.get_field_val("dob")
            if (not age_raw or not age_raw.isdigit()) and dob_raw:
                calc = calculate_age_from_dob(dob_raw)
                age_raw = str(calc) if calc is not None else "50"
            age = escape_latex(age_raw or "50")

            spouse_name = escape_latex(self.get_field_val("spouse_name"))
            birth_name = escape_latex(self.get_field_val("birth_cert_name"))
            aadhaar_name = escape_latex(self.get_field_val("aadhaar_name"))
            other_name = escape_latex(self.get_field_val("daughter_cert_name"))
            address = escape_latex(self.get_field_val("address"))
            village = escape_latex(self.get_field_val("village"))
            taluka = escape_latex(self.get_field_val("taluka"))
            place = escape_latex(self.get_field_val("place"))
            date_str = escape_latex(self.get_field_val("date"))
            photo_path = self.get_field_val("photo_path")
            sig_path = self.get_field_val("sig_path")

            new_decl = f"I, {deponent_name}, Age {age} years, Wife of {spouse_name}, an Indian national, residing at {address}, {village}, {taluka}, North Goa, Goa"
            content = re.sub(r"I,\s*\[Applicant Name\],\s*Age\s*\[Age\]\s*years,\s*Wife of\s*\[Spouse Name\],\s*an Indian national,\s*residing at\s*\[Address\],\s*\[Village\],\s*\[Taluka\],\s*North Goa,\s*Goa", lambda m: new_decl, content)
            content = re.sub(r"recorded as \[Birth Certificate Name\]\.", lambda m: f"recorded as {birth_name}.", content)
            content = re.sub(r"recorded as \[Aadhaar Name\]\.", lambda m: f"recorded as {aadhaar_name}.", content)
            content = re.sub(r"recorded as \[Name on Daughter's Cert\]\.", lambda m: f"recorded as {other_name}.", content)
            content = re.sub(r"names as \[Birth Certificate Name\], \[Aadhaar Name\] and \[Name on Daughter's Cert\]", lambda m: f"names as {birth_name}, {aadhaar_name} and {other_name}", content)
            content = re.sub(r"Mamlatdar of \[Taluka\] Taluka", lambda m: f"Mamlatdar of {taluka} Taluka", content)
            content = re.sub(r"\\textbf\{Place:\} \[Place\]", lambda m: f"\\textbf{{Place:}} {place}", content)
            content = re.sub(r"\\textbf\{Date:\} \[Date\]", lambda m: f"\\textbf{{Date:}} {date_str}", content)
            content = re.sub(r"\\textbf\{Identified by: \[Applicant Name\]\}", lambda m: f"\\textbf{{Identified by: {deponent_name}}}", content)

            content = self.inject_photo_and_sig(content, photo_path, sig_path)

            os.makedirs(self.target_dir, exist_ok=True)
            tex_path = self.get_output_tex_path()
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.save_data()
            return True, tex_path, ""
        except Exception as e:
            return False, "", str(e)
