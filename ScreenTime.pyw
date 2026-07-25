"""Windowless launcher — what the desktop icon and the login entry point at."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import main  # noqa: E402

raise SystemExit(main())
