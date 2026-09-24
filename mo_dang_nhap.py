import os
import sys

# Prepend src directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import mo_dang_nhap

if __name__ == "__main__":
    if hasattr(mo_dang_nhap, "main"):
        mo_dang_nhap.main()
