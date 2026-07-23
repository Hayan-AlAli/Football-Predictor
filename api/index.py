import sys
import os

os.environ.setdefault("SOCCERDATA_DIR", "/tmp/soccerdata")

_root = os.path.join(os.path.dirname(__file__), '..')
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    from backend.server import app
except Exception as e:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    app = FastAPI(title="Football Predictor API (fallback)")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    @app.get("/api/health")
    async def health():
        return {
            "status": "degraded",
            "message": f"Backend failed to load: {str(e)}",
            "version": "1.0.0",
        }
