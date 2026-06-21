"""PyInstaller / standalone entry point.

Lets the project run both as a module (`python -m src.bridge`) during dev and as
a frozen single-file exe (built from this script) for distribution.
"""

import sys

from src.bridge import main

if __name__ == "__main__":
    sys.exit(main())
