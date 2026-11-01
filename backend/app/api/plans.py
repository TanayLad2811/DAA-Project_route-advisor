import uuid

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.config import settings
from app.schemas.plan import PlanMetadata, PlanUploadResponse
from app.services.image_processing import (
    process_floor_plan_image,
    render_debug_stage_png,
    validate_and_normalize_image,
)
from app.services.storage import repo

router = APIRouter(prefix="/plans", tags=["Plans"])


@router.get("/samples/list", response_model=list[dict])
def list_sample_plans():
    """Returns available built-in synthetic sample plans for immediate evaluation."""
    fixtures_dir = settings.base_dir / "tests" / "fixtures"
    samples = []
    sample_info = {
        "office_rooms": {"name": "Office Complex (4 Rooms + Corridor)", "desc": "Standard office layout with 4 rooms, hallway doors, and building exit"},
        "corridor": {"name": "Straight Corridor", "desc": "Simple dual-wall linear hallway"},
        "l_shape": {"name": "L-Shape Hallway", "desc": "Right-angle corridor intersection"},
        "t_junction": {"name": "T-Junction Corridor", "desc": "3-way corridor junction"},
        "room_with_pillar": {"name": "Hall with Central Pillar", "desc": "Open room with center obstacle and exterior envelope"},
    }

    for key, info in sample_info.items():
        sample_file = fixtures_dir / f"{key}.png"
        if sample_file.exists():
            samples.append({
                "id": key,
                "name": info["name"],
                "description": info["desc"],
            })
    return samples


@router.post("/samples/{name}", response_model=PlanUploadResponse, status_code=status.HTTP_201_CREATED)
def load_sample_plan(name: str):
    """Loads a built-in synthetic sample floor plan."""
    fixtures_dir = settings.base_dir / "tests" / "fixtures"
    sample_file = fixtures_dir / f"{name}.png"
    if not sample_file.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sample plan '{name}' not found")

    file_bytes = sample_file.read_bytes()
    plan_id = str(uuid.uuid4())
    norm_bytes, metadata = validate_and_normalize_image(file_bytes, f"{name}.png", plan_id)
    repo.save_plan(plan_id, norm_bytes, metadata)

    return PlanUploadResponse(
        plan_id=plan_id,
        width=metadata.normalized_width,
        height=metadata.normalized_height,
        image_url=f"/api/v1/plans/{plan_id}/image",
        scale_factor=metadata.scale_factor,
    )


@router.post("", response_model=PlanUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_plan(file: UploadFile = File(...)):
    """Upload a floor plan image (PNG, JPG, PDF up to 10MB)."""
    file_bytes = await file.read()
    if len(file_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds size limit of {settings.max_upload_size_bytes // (1024 * 1024)} MB",
        )

    plan_id = str(uuid.uuid4())
    filename = file.filename or "uploaded_plan.png"

    try:
        norm_bytes, metadata = validate_and_normalize_image(file_bytes, filename, plan_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    repo.save_plan(plan_id, norm_bytes, metadata)

    return PlanUploadResponse(
        plan_id=plan_id,
        width=metadata.normalized_width,
        height=metadata.normalized_height,
        image_url=f"/api/v1/plans/{plan_id}/image",
        scale_factor=metadata.scale_factor,
    )


@router.get("/{plan_id}", response_model=PlanMetadata)
def get_plan(plan_id: str):
    """Retrieve metadata for a floor plan."""
    meta = repo.get_plan_metadata(plan_id)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Floor plan '{plan_id}' not found",
        )
    return meta


@router.get("/{plan_id}/image")
def get_plan_image(plan_id: str):
    """Fetch the normalized floor plan image."""
    img_path = repo.get_plan_image_path(plan_id)
    if not img_path or not img_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Floor plan image for '{plan_id}' not found",
        )
    return FileResponse(img_path, media_type="image/png")


@router.get("/{plan_id}/debug/{stage}")
def get_debug_stage(
    plan_id: str,
    stage: str,
    wall_threshold: int = Query(127, ge=-1, le=255),
    invert: bool = Query(False),
    close_kernel: int = Query(3, ge=1, le=15),
    min_clearance_px: float = Query(3.0, ge=0.0, le=50.0),
):
    """Returns a PNG representation of an intermediate image processing stage."""
    img_path = repo.get_plan_image_path(plan_id)
    if not img_path or not img_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Floor plan '{plan_id}' not found",
        )

    image_bytes = img_path.read_bytes()
    try:
        processed = process_floor_plan_image(
            image_bytes=image_bytes,
            wall_threshold=wall_threshold,
            invert=invert,
            close_kernel=close_kernel,
            min_clearance_px=min_clearance_px,
        )
        png_bytes = render_debug_stage_png(processed, stage)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rendering debug stage: {e}",
        ) from e

    return Response(content=png_bytes, media_type="image/png")


@router.delete("/{plan_id}", status_code=status.HTTP_200_OK)
def delete_plan(plan_id: str):
    """Delete a plan and all its associated data."""
    deleted = repo.delete_plan(plan_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Floor plan '{plan_id}' not found",
        )
    return {"status": "deleted", "plan_id": plan_id}
