"""
OBC Certificate Declaration Module.
Single Responsibility: Handles OBC declaration fields, data loading/saving, and LaTeX synthesis.
"""
from __future__ import annotations
import os
import json
import re
from datetime import datetime
from ..base import BaseDeclaration, calculate_age_from_dob
from ...core.widgets import FormField
from ...core.latex_compiler import escape_latex

class ObcDeclaration(BaseDeclaration):
    """Encapsulates OBC Certificate declaration logic (Self & Child modes)."""

    def __init__(self, target_dir: str):
        super().__init__(target_dir)
        self.declaration_id = "obc"
        self.title = "🏛️ GoaOnAuto - OBC Certificate Declaration"
        self.service_id = "REV08"
        self.supported_modes = ["self", "child"]

        self.load_data()

    def get_output_tex_path(self) -> str:
        return os.path.join(self.target_dir, "obc_declaration.tex")

    def get_output_pdf_path(self) -> str:
        return os.path.join(self.target_dir, "obc_declaration.pdf")

    def load_data(self) -> None:
        """Loads data from obc_form_data.json or applicant_dossier.json."""
        data: dict = {}

        form_file = os.path.join(self.target_dir, "obc_form_data.json")
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
            address_obj = dossier.get("address", {}).get("value", {})
            full_address = address_obj.get("full", "") if isinstance(address_obj, dict) else str(address_obj or "")
            taluka = address_obj.get("taluka", "Bardez") if isinstance(address_obj, dict) else "Bardez"

            rel_obj = dossier.get("relation", {})
            rel_name = rel_obj.get("name", "") if isinstance(rel_obj, dict) else ""

            child_obj = dossier.get("child", {})
            child_name = child_obj.get("name", "") if isinstance(child_obj, dict) else ""

            deponent_age, deponent_dob = self.extract_age_and_dob(dossier, fallback_age="25")
            child_age, child_dob = self.extract_child_age_and_dob(dossier, fallback_age="15")

            data = {
                "mode": "child" if child_name else "self",
                "deponent_name": dossier.get("name", {}).get("value", ""),
                "age": deponent_age,
                "dob": deponent_dob,
                "relation_name": rel_name,
                "child_name": child_name,
                "child_age": child_age,
                "child_dob": child_dob,
                "samaj": "Bhandari Naik",
                "village": "Calangute",
                "annual_income": "974800",
                "address": full_address or "H.No. 123, Goa",
                "taluka": taluka,
                "place": "Mapusa",
                "date": datetime.now().strftime("%d/%m/%Y"),
                "photo_path": dossier.get("photoPath", ""),
                "sig_path": dossier.get("signaturePath", "")
            }

        self.mode = data.get("mode", "self")

        photo_path = data.get("photo_path") or self.find_file_pattern(["*passport_photo*", "*white_bg*", "*photo*", "*.jpg", "*.png"])
        sig_path = data.get("sig_path") or self.find_file_pattern(["*signature*", "*sig*"])

        deponent_age = str(data.get("age") or "")
        dob_str = str(data.get("dob") or "")
        if (not deponent_age or not deponent_age.isdigit()) and dob_str:
            calc = calculate_age_from_dob(dob_str)
            deponent_age = str(calc) if calc is not None else "25"
        if not deponent_age:
            deponent_age = "25"

        child_age = str(data.get("child_age") or "")
        child_dob_str = str(data.get("child_dob") or "")
        if (not child_age or not child_age.isdigit()) and child_dob_str:
            calc = calculate_age_from_dob(child_dob_str)
            child_age = str(calc) if calc is not None else "15"
        if not child_age:
            child_age = "15"

        self.fields = [
            FormField("deponent_name", "Deponent / Applicant Name", data.get("deponent_name") or "Applicant Name", is_required=True),
            FormField("age", "Age (Years)", deponent_age, is_required=True),
            FormField("dob", "Date of Birth (DD/MM/YYYY)", dob_str),
            FormField("relation_name", "Father / Spouse Name", data.get("relation_name") or ""),
            FormField("child_name", "Child Name (Child Mode)", data.get("child_name") or ""),
            FormField("child_age", "Child Age (Years)", child_age),
            FormField("child_dob", "Child Date of Birth (DD/MM/YYYY)", child_dob_str),
            FormField("samaj", "OBC Community / Samaj", data.get("samaj") or "Bhandari Naik", is_required=True),
            FormField("village", "Originally From Village", data.get("village") or "Calangute", is_required=True),
            FormField("annual_income", "Annual Family Income (Rs.)", str(data.get("annual_income") or "974800"), is_required=True),
            FormField("address", "Full Residential Address", data.get("address") or "H.No. 123, Goa", is_required=True),
            FormField("taluka", "Taluka Sub-Division", data.get("taluka") or "Bardez"),
            FormField("place", "Place", data.get("place") or "Mapusa"),
            FormField("date", "Date (DD/MM/YYYY)", data.get("date") or datetime.now().strftime("%d/%m/%Y")),
            FormField("photo_path", "Passport Photo Path", photo_path, is_path=True, is_required=True),
            FormField("sig_path", "Signature Path", sig_path, is_path=True)
        ]

    def save_data(self) -> None:
        """Saves obc_form_data.json and updates applicant_dossier.json."""
        if not os.path.isdir(self.target_dir):
            return

        dob_val = self.get_field_val("dob")
        age_str = self.get_field_val("age")
        if (not age_str or not age_str.isdigit()) and dob_val:
            calc = calculate_age_from_dob(dob_val)
            age_val = calc if calc is not None else 25
        else:
            try:
                age_val = int(age_str) if age_str.isdigit() else 25
            except Exception:
                age_val = 25

        child_dob_val = self.get_field_val("child_dob")
        child_age_str = self.get_field_val("child_age")
        if (not child_age_str or not child_age_str.isdigit()) and child_dob_val:
            calc = calculate_age_from_dob(child_dob_val)
            child_age_val = calc if calc is not None else 15
        else:
            try:
                child_age_val = int(child_age_str) if child_age_str.isdigit() else 15
            except Exception:
                child_age_val = 15

        form_data = {
            "serviceType": "obc_certificate",
            "mode": self.mode,
            "applicantName": self.get_field_val("deponent_name"),
            "age": age_val,
            "dob": dob_val,
            "relationName": self.get_field_val("relation_name"),
            "childName": self.get_field_val("child_name") if self.mode == "child" else "",
            "childAge": child_age_val if self.mode == "child" else "",
            "childDob": child_dob_val if self.mode == "child" else "",
            "samaj": self.get_field_val("samaj"),
            "village": self.get_field_val("village"),
            "annualIncome": self.get_field_val("annual_income"),
            "address": self.get_field_val("address"),
            "taluka": self.get_field_val("taluka"),
            "place": self.get_field_val("place"),
            "declarationDate": self.get_field_val("date"),
            "photoPath": self.get_field_val("photo_path"),
            "signaturePath": self.get_field_val("sig_path"),
            "declarationTexPath": self.get_output_tex_path(),
            "declarationPdfPath": self.get_output_pdf_path(),
            "updatedAt": datetime.now().isoformat()
        }

        form_file = os.path.join(self.target_dir, "obc_form_data.json")
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
        if self.mode == "child":
            dossier["child"] = {
                "name": self.get_field_val("child_name"),
                "age": child_age_val,
                "dob": child_dob_val
            }

        dossier_path = os.path.join(self.target_dir, "applicant_dossier.json")
        try:
            with open(dossier_path, "w", encoding="utf-8") as f:
                json.dump(dossier, f, indent=2)
        except Exception:
            pass

    def generate_tex(self) -> tuple[bool, str, str]:
        """Synthesizes obc_declaration.tex reflecting current form state."""
        try:
            is_child = (self.mode == "child")
            template_name = "obc_child.tex" if is_child else "obc_self.tex"
            template_path = self.get_template_path(template_name)

            if not os.path.exists(template_path):
                return False, "", f"Template not found: {template_path}"

            with open(template_path, "r", encoding="utf-8") as f:
                content = f.read()

            deponent_name = escape_latex(self.get_field_val("deponent_name"))
            age_raw = self.get_field_val("age")
            dob_raw = self.get_field_val("dob")
            if (not age_raw or not age_raw.isdigit()) and dob_raw:
                calc = calculate_age_from_dob(dob_raw)
                age_raw = str(calc) if calc is not None else "25"
            age = escape_latex(age_raw or "25")

            rel_name = escape_latex(self.get_field_val("relation_name"))
            child_name = escape_latex(self.get_field_val("child_name"))

            child_age_raw = self.get_field_val("child_age")
            child_dob_raw = self.get_field_val("child_dob")
            if (not child_age_raw or not child_age_raw.isdigit()) and child_dob_raw:
                calc = calculate_age_from_dob(child_dob_raw)
                child_age_raw = str(calc) if calc is not None else "15"
            child_age = escape_latex(child_age_raw or "15")

            samaj = escape_latex(self.get_field_val("samaj"))
            village = escape_latex(self.get_field_val("village"))
            income = escape_latex(self.get_field_val("annual_income"))
            address = escape_latex(self.get_field_val("address"))
            taluka = escape_latex(self.get_field_val("taluka"))
            place = escape_latex(self.get_field_val("place"))
            date_str = escape_latex(self.get_field_val("date"))
            photo_path = self.get_field_val("photo_path")
            sig_path = self.get_field_val("sig_path")

            if not is_child:
                new_decl = f"I, {deponent_name}, aged {age}, Son of {rel_name} residing at {address}, {village}, {taluka}, North Goa"
                content = re.sub(r"I,\s*\[Applicant Name\],\s*aged\s*\[Age\],\s*Son of\s*\[Parent Name\]\s*residing at\s*\[Address\],\s*\[Village\],\s*\[Taluka\],\s*North Goa", lambda m: new_decl, content)
                content = re.sub(r"belong to \[Community/Samaj\]", lambda m: f"belong to {samaj} samaj", content)
                content = re.sub(r"originally hail from \[Village\]", lambda m: f"originally hail from {village}", content)
                content = re.sub(r"originally from \[Village\] prior to", lambda m: f"originally from {village} prior to", content)
                content = re.sub(r"salaries is Rs\. \[Annual Income\]", lambda m: f"salaries is Rs. {income}", content)
                content = re.sub(r"Office of Dy\. Collector and S\.D\.O\. \[Sub-Division\]-Goa", lambda m: f"Office of Dy. Collector and S.D.O. {place}-Goa", content)
                content = re.sub(r"\\textbf\{Identified by: \[Applicant Name\]\}", lambda m: f"\\textbf{{Identified by: {deponent_name}}}", content)
            else:
                new_decl = f"I, {deponent_name}, aged {age}, Father of {child_name} aged {child_age} residing at {address}, {village}, {taluka}, North Goa"
                content = re.sub(r"I,\s*\[Parent Name\],\s*aged\s*\[Parent Age\],\s*Father of\s*\[Child Name\]\s*aged\s*\[Child Age\]\s*residing at\s*\[Address\],\s*\[Village\],\s*\[Taluka\],\s*North Goa", lambda m: new_decl, content)
                content = re.sub(r"My Son \[Child Name\] belongs to", lambda m: f"My Son {child_name} belongs to", content)
                content = re.sub(r"belong to \[Community/Samaj\]", lambda m: f"belong to {samaj} samaj", content)
                content = re.sub(r"My Son, originally hail from \[Village\]", lambda m: f"My Son, originally hail from {village}", content)
                content = re.sub(r"originally from \[Village\] prior to", lambda m: f"originally from {village} prior to", content)
                content = re.sub(r"salaries is Rs\. \[Annual Income\]", lambda m: f"salaries is Rs. {income}", content)
                content = re.sub(r"Office of Dy\. Collector and S\.D\.O\. \[Sub-Division\]-Goa", lambda m: f"Office of Dy. Collector and S.D.O. {place}-Goa", content)
                content = re.sub(r"\\textbf\{Identified by: \[Parent Name\]\}", lambda m: f"\\textbf{{Identified by: {deponent_name}}}", content)

            content = re.sub(r"\\textbf\{Place:\} \[Place\]", lambda m: f"\\textbf{{Place:}} {place}", content)
            content = re.sub(r"\\textbf\{Date:\} \[Date\]", lambda m: f"\\textbf{{Date:}} {date_str}", content)

            content = self.inject_photo_and_sig(content, photo_path, sig_path)

            os.makedirs(self.target_dir, exist_ok=True)
            tex_path = self.get_output_tex_path()
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.save_data()
            return True, tex_path, ""
        except Exception as e:
            return False, "", str(e)
