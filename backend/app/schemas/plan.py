from pydantic import BaseModel


class PlanMetadata(BaseModel):
    plan_id: str
    filename: str
    original_width: int
    original_height: int
    normalized_width: int
    normalized_height: int
    scale_factor: float = 1.0  # normalized / original (<= 1.0 if downscaled)
    meters_per_pixel: float | None = None
    created_at: str


class PlanUploadResponse(BaseModel):
    plan_id: str
    width: int
    height: int
    image_url: str
    scale_factor: float = 1.0

