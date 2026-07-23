import sys
import os

os.environ.setdefault("SOCCERDATA_DIR", "/tmp/soccerdata")

_root = os.path.join(os.path.dirname(__file__), '..')
if _root not in sys.path:
    sys.path.insert(0, _root)

from backend.server import app
