"""
FastAPI application entrypoint for DragmeTolabel.
Serves REST API, OpenCV renderer, material assets, and frontend application.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.routes_materials import router as materials_router
from .api.routes_presets import router as presets_router
from .api.routes_preview import router as preview_router
from .cv.materials import ensure_material_textures


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure default texture assets exist on startup
    ensure_material_textures()
    yield


app = FastAPI(
    title="DragmeTolabel API",
    description="Computer Vision & Polygon Surface Replacement Web Backend for Sales Reps",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for cross-origin frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(presets_router, prefix="/api/v1")
app.include_router(materials_router, prefix="/api/v1")
app.include_router(preview_router, prefix="/api/v1")


# Mount static texture directory
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Mount frontend directory for easy standalone single-server serving
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"
FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


def run() -> None:
    """Entrypoint function to run the application with uvicorn."""
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()
