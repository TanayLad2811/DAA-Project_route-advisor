import io
from dataclasses import dataclass
from datetime import UTC, datetime

import cv2
import fitz  # PyMuPDF
import numpy as np
from PIL import Image

from app.config import settings
from app.schemas.plan import PlanMetadata

# Protect against decompression bomb attacks
Image.MAX_IMAGE_PIXELS = 50_000_000


@dataclass
class ProcessedPlanImage:
    original_rgb: np.ndarray
    grayscale: np.ndarray
    wall_mask: np.ndarray  # 255 = wall, 0 = free
    free_mask: np.ndarray  # 255 = walkable free space, 0 = obstacle/wall
    exterior_mask: np.ndarray  # 255 = outside building, 0 = inside or wall
    distance_transform: np.ndarray  # float32 clearance in pixels to nearest wall


def validate_and_normalize_image(
    file_bytes: bytes, filename: str, plan_id: str
) -> tuple[bytes, PlanMetadata]:
    """Validates uploaded image/PDF bytes and normalizes to a standard RGB/Grayscale PNG.

    Downscales proportionally if max dimension exceeds settings.max_image_dimension (4000 px).
    """
    if len(file_bytes) > settings.max_upload_size_bytes:
        raise ValueError(
            f"File size exceeds maximum allowed size of {settings.max_upload_size_bytes // (1024 * 1024)} MB"
        )

    pil_img: Image.Image | None = None

    if file_bytes.startswith(b"%PDF"):
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            if len(doc) == 0:
                raise ValueError("PDF file contains no pages")
            page = doc.load_page(0)
            zoom = 150.0 / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_data = pix.tobytes("png")
            pil_img = Image.open(io.BytesIO(img_data))
            doc.close()
        except Exception as e:
            raise ValueError(f"Failed to rasterize PDF floor plan: {e}") from e
    else:
        try:
            pil_img = Image.open(io.BytesIO(file_bytes))
            pil_img.verify()
            pil_img = Image.open(io.BytesIO(file_bytes))
        except Exception as e:
            raise ValueError(f"Invalid or corrupted image format: {e}") from e

    if pil_img is None:
        raise ValueError("Could not decode image content")

    if pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info):
        alpha_img = pil_img.convert("RGBA")
        background = Image.new("RGBA", alpha_img.size, (255, 255, 255, 255))
        alpha_composite = Image.alpha_composite(background, alpha_img)
        pil_img = alpha_composite.convert("RGB")
    elif pil_img.mode != "RGB" and pil_img.mode != "L":
        pil_img = pil_img.convert("RGB")

    orig_w, orig_h = pil_img.size
    max_dim = settings.max_image_dimension
    scale_factor = 1.0

    if max(orig_w, orig_h) > max_dim:
        scale_factor = max_dim / float(max(orig_w, orig_h))
        new_w = max(1, round(orig_w * scale_factor))
        new_h = max(1, round(orig_h * scale_factor))
        pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    norm_w, norm_h = pil_img.size

    out_buf = io.BytesIO()
    pil_img.save(out_buf, format="PNG", optimize=True)
    norm_bytes = out_buf.getvalue()

    metadata = PlanMetadata(
        plan_id=plan_id,
        filename=filename,
        original_width=orig_w,
        original_height=orig_h,
        normalized_width=norm_w,
        normalized_height=norm_h,
        scale_factor=scale_factor,
        created_at=datetime.now(UTC).isoformat(),
    )

    return norm_bytes, metadata


def process_floor_plan_image(
    image_bytes: bytes,
    wall_threshold: int = 127,
    invert: bool = False,
    close_kernel: int = 3,
    min_wall_area: int | None = None,
    min_clearance_px: float = 2.0,
    filter_annotations: bool = True,
) -> ProcessedPlanImage:
    """Extracts wall mask, free walkable space, exterior flood fill, and Euclidean distance transform."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("Failed to decode image buffer into OpenCV array")

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    if invert:
        gray = cv2.bitwise_not(gray)

    # 1. Filter blue dimension lines and annotations if requested
    if filter_annotations:
        b_chan = bgr[:, :, 0].astype(int)
        r_chan = bgr[:, :, 2].astype(int)
        blue_mask = (b_chan - r_chan > 20) & (b_chan > 110)
        gray[blue_mask] = 255

    blurred = cv2.medianBlur(gray, 3)

    # Thresholding: 0 = Otsu's threshold, else manual threshold
    if wall_threshold <= 0:
        _, raw_bin = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    else:
        _, raw_bin = cv2.threshold(blurred, wall_threshold, 255, cv2.THRESH_BINARY_INV)

    # Strip thin lines (1-2 px door swing arcs, text, dimension ticks) so doorways remain open
    k_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    walls_stripped = cv2.morphologyEx(raw_bin, cv2.MORPH_OPEN, k_open)

    h, w = gray.shape
    total_pixels = h * w
    min_area = min_wall_area if min_wall_area is not None else max(15, int(total_pixels * 0.0001))

    # Remove small specks
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(walls_stripped, connectivity=8)
    cleaned_walls = np.zeros_like(walls_stripped)
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area >= min_area:
            cleaned_walls[labels == i] = 255

    # Controlled morphological closing to seal tiny gaps without bridging doorways
    k_size = max(1, close_kernel)
    if k_size > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k_size, k_size))
        cleaned_walls = cv2.morphologyEx(cleaned_walls, cv2.MORPH_CLOSE, kernel)

    # Free mask is inverse of wall mask (255 = free, 0 = wall)
    free_mask = cv2.bitwise_not(cleaned_walls)

    # Exterior flood fill from borders
    exterior_mask = np.zeros((h + 2, w + 2), np.uint8)
    flood_copy = free_mask.copy()

    for x in range(w):
        if flood_copy[0, x] == 255:
            cv2.floodFill(flood_copy, exterior_mask, (x, 0), 0)
        if flood_copy[h - 1, x] == 255:
            cv2.floodFill(flood_copy, exterior_mask, (x, h - 1), 0)
    for y in range(h):
        if flood_copy[y, 0] == 255:
            cv2.floodFill(flood_copy, exterior_mask, (0, y), 0)
        if flood_copy[y, w - 1] == 255:
            cv2.floodFill(flood_copy, exterior_mask, (w - 1, y), 0)

    final_exterior = (exterior_mask[1 : h + 1, 1 : w + 1] * 255).astype(np.uint8)

    # Distance transform
    dist_transform = cv2.distanceTransform(free_mask, cv2.DIST_L2, 5)

    if min_clearance_px > 0:
        walkable_mask = np.where(dist_transform >= min_clearance_px, np.uint8(255), np.uint8(0))
    else:
        walkable_mask = free_mask

    return ProcessedPlanImage(
        original_rgb=rgb,
        grayscale=gray,
        wall_mask=cleaned_walls,
        free_mask=walkable_mask,
        exterior_mask=final_exterior,
        distance_transform=dist_transform,
    )


def render_debug_stage_png(processed: ProcessedPlanImage, stage: str) -> bytes:
    """Renders a specific pipeline stage as PNG bytes for visual inspection."""
    out_img: np.ndarray

    if stage == "gray":
        out_img = processed.grayscale
    elif stage in ("wall_mask", "binary"):
        out_img = processed.wall_mask
    elif stage == "free_mask":
        out_img = processed.free_mask
    elif stage == "exterior":
        out_img = processed.exterior_mask
    elif stage == "distance_transform":
        dt = processed.distance_transform
        max_val = np.max(dt) if np.max(dt) > 0 else 1.0
        normalized = np.uint8(np.clip((dt / max_val) * 255.0, 0, 255))
        out_img = cv2.applyColorMap(normalized, cv2.COLORMAP_VIRIDIS)
    else:
        raise ValueError(f"Unknown debug stage '{stage}'")

    success, encoded = cv2.imencode(".png", out_img)
    if not success:
        raise RuntimeError("Failed to encode debug image to PNG")
    return encoded.tobytes()
