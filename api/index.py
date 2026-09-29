import os
import sys

_root = os.path.join(os.path.dirname(__file__), '..')
if _root not in sys.path:
    sys.path.insert(0, _root)

from backend.server import app  # noqa: E402,F401
