"""
LaTeX Compilation & Escaping Service.
Single Responsibility: Discovers pdflatex, compiles LaTeX files to PDF, and manages build artifacts.
"""
import os
import subprocess

def escape_latex(text: str) -> str:
    """Escapes special LaTeX characters in user input strings."""
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

def find_pdflatex_binary() -> str:
    """Locates pdflatex executable in local MiKTeX installation or system PATH."""
    local_miktex = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Programs", "MiKTeX", "miktex", "bin", "x64", "pdflatex.exe"
    )
    if os.path.exists(local_miktex):
        return local_miktex

    program_files_miktex = r"C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe"
    if os.path.exists(program_files_miktex):
        return program_files_miktex

    return "pdflatex"

def compile_latex_to_pdf(tex_path: str, output_dir: str) -> tuple[bool, str]:
    """
    Compiles a .tex file into .pdf using pdflatex.
    Cleans up intermediate .aux, .log, and .out artifacts on completion.
    Returns (success, pdf_path_or_error_message).
    """
    if not os.path.exists(tex_path):
        return False, f"TeX source file does not exist: {tex_path}"

    abs_output_dir = os.path.abspath(output_dir)
    abs_tex_path = os.path.abspath(tex_path)
    os.makedirs(abs_output_dir, exist_ok=True)

    pdflatex_exe = find_pdflatex_binary()
    base_name = os.path.splitext(os.path.basename(abs_tex_path))[0]
    expected_pdf = os.path.join(abs_output_dir, f"{base_name}.pdf")

    cmd = [
        pdflatex_exe,
        "-interaction=nonstopmode",
        f"-output-directory={abs_output_dir}",
        abs_tex_path
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=abs_output_dir)

        if os.path.exists(expected_pdf):
            # Clean up intermediate build artifacts
            for ext in [".aux", ".log", ".out"]:
                tmp_file = os.path.join(output_dir, f"{base_name}{ext}")
                if os.path.exists(tmp_file):
                    try:
                        os.remove(tmp_file)
                    except Exception:
                        pass
            return True, expected_pdf
        else:
            err_snippet = proc.stderr[:300] if proc.stderr else (proc.stdout[-300:] if proc.stdout else "Unknown error")
            return False, f"Compilation failed (exit code {proc.returncode}): {err_snippet}"
    except Exception as e:
        return False, f"pdflatex execution error: {str(e)}"
