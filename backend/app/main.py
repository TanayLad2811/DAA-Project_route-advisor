from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.graph import router as graph_router
from app.api.hazards import router as hazards_router
from app.api.plans import router as plans_router
from app.api.routes import router as routes_router
from app.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Emergency Evacuation Route Analyzer API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(plans_router, prefix=settings.api_v1_prefix)
app.include_router(graph_router, prefix=settings.api_v1_prefix)
app.include_router(hazards_router, prefix=settings.api_v1_prefix)
app.include_router(routes_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["Health"])
@app.get(f"{settings.api_v1_prefix}/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "0.1.0",
    }


# Mount production frontend static files if present
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists() and (static_dir / "index.html").exists():
    if (static_dir / "assets").exists():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend_spa(full_path: str):
        target = static_dir / full_path
        if target.exists() and target.is_file():
            return FileResponse(target)
        return FileResponse(static_dir / "index.html")

