import os
from pathlib import Path

from pydantic import BaseModel


def get_cors_origins() -> list[str]:
    env_cors = os.getenv("CORS_ORIGINS")
    if env_cors:
        return [o.strip() for o in env_cors.split(",") if o.strip()]
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "*",
    ]


class Settings(BaseModel):
    app_name: str = "Emergency Evacuation Route Analyzer"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = get_cors_origins()
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10 MB
    max_image_dimension: int = 4000
    base_dir: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = base_dir / "data"
    upload_dir: Path = data_dir / "uploads"
    graph_dir: Path = data_dir / "graphs"


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.graph_dir.mkdir(parents=True, exist_ok=True)

