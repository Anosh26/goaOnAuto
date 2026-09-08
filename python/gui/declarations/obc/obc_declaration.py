"""
OBC Certificate Declaration Module.
Single Responsibility: Handles OBC declaration fields, data loading/saving, and LaTeX synthesis.
"""
from __future__ import annotations
import os
import json
import re
from datetime import datetime
from ..base import BaseDeclaration
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

            data = {
                "mode": "child" if child_name else "self",
                "deponent_name": dossier.get("name", {}).get("value", ""),
                "age": str(dossier.get("age", {}).get("value", "25")),
                "relation_name": rel_name,
                "child_name": child_name,
                "child_age": "15",
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

        self.fields = [
            FormField("deponent_name", "Deponent / Applicant Name", data.get("deponent_name") or "Applicant Name", is_required=True),
            FormField("age", "Age (Years)", str(data.get("age") or "25"), is_required=True),
            FormField("relation_name", "Father / Spouse Name", data.get("relation_name") or ""),
            FormField("child_name", "Child Name (Child Mode)", data.get("child_name") or ""),
            FormField("child_age", "Child Age (Years)", str(data.get("child_age") or "15")),
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

        form_data = {
            "serviceType": "obc_certificate",
            "mode": self.mode,
            "applicantName": self.get_field_val("deponent_name"),
            "age": self.get_field_val("age"),
            "relationName": self.get_field_val("relation_name"),
            "childName": self.get_field_val("child_name") if self.mode == "child" else "",
            "childAge": self.get_field_val("child_age") if self.mode == "child" else "",
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
            age = escape_latex(self.get_field_val("age"))
            rel_name = escape_latex(self.get_field_val("relation_name"))
            child_name = escape_latex(self.get_field_val("child_name"))
            child_age = escape_latex(self.get_field_val("child_age"))
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
                content = re.sub(r"I, \[Applicant Name\], aged \[Age\], Son of \[Parent Name\] residing at \[Address\], \[Village\], \[Taluka\], North Goa", lambda m: new_decl, content)
                content = re.sub(r"belong to \[Community/Samaj\]", lambda m: f"belong to {samaj} samaj", content)
                content = re.sub(r"originally hail from \[Village\]", lambda m: f"originally hail from {village}", content)
                content = re.sub(r"originally from \[Village\] prior to", lambda m: f"originally from {village} prior to", content)
                content = re.sub(r"salaries is Rs\. \[Annual Income\]", lambda m: f"salaries is Rs. {income}", content)
                content = re.sub(r"Office of Dy\. Collector and S\.D\.O\. \[Sub-Division\]-Goa", lambda m: f"Office of Dy. Collector and S.D.O. {place}-Goa", content)
                content = re.sub(r"\\textbf\{Identified by: \[Applicant Name\]\}", lambda m: f"\\textbf{{Identified by: {deponent_name}}}", content)
            else:
                new_decl = f"I, {deponent_name}, aged {age}, Father of {child_name} aged {child_age} residing at {address}, {village}, {taluka}, North Goa"
                content = re.sub(r"I, \[Parent Name\], aged \[Parent Age\], Father of \[Child Name\] aged \[Child Age\] residing at \[Address\], \[Village\], \[Taluka\], North Goa", lambda m: new_decl, content)
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
