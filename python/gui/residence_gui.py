"""
GoaOnAuto Residence Certificate Automation GUI.
Backward-compatible entrypoint forwarding to the modular Declaration App.
"""
import sys
import os
import argparse

# Ensure project root is in sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from python.gui.declaration_app import run_app

def main():
    parser = argparse.ArgumentParser(description="GoaOnAuto Residence Certificate Automation GUI")
    parser.add_argument("--dir", default="", help="Applicant folder directory path")
    parser.add_argument("--no-prompt", action="store_true", help="Do not prompt for missing files on launch")
    args = parser.parse_args()

    run_app(declaration_type="residence", target_dir=args.dir, no_prompt=args.no_prompt)

if __name__ == "__main__":
    main()
