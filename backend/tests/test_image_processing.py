from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.image_processing import process_floor_plan_image, render_debug_stage_png

client = TestClient(app)
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_corridor_processing():
    img_bytes = (FIXTURES_DIR / "corridor.png").read_bytes()
    processed = process_floor_plan_image(img_bytes, wall_threshold=127)

    # Corridors should have walkable middle region
    assert processed.wall_mask.shape == (100, 300)
    # Check top wall (y=10, x=150) is wall (255)
    assert processed.wall_mask[10, 150] == 255
    # Check center (y=50, x=150) is free (255 in free_mask)
    assert processed.free_mask[50, 150] == 255
    # Clearance at center should be around 30 px
    assert processed.distance_transform[50, 150] > 20.0


def test_office_rooms_doorway_connectivity():
    img_bytes = (FIXTURES_DIR / "office_rooms.png").read_bytes()
    processed = process_floor_plan_image(img_bytes, wall_threshold=127, close_kernel=3)

    # Doorway 1 between room 1 and hallway at (75, 84) must be walkable
    assert processed.free_mask[84, 75] == 255
    # Main exit at (100, 290) must be walkable
    assert processed.free_mask[100, 290] == 255
    # Dividing wall at (45, 154) must be wall
    assert processed.wall_mask[45, 154] == 255


def test_room_with_pillar():
    img_bytes = (FIXTURES_DIR / "room_with_pillar.png").read_bytes()
    processed = process_floor_plan_image(img_bytes, wall_threshold=127)

    # Center pillar at (100, 100) must be wall
    assert processed.wall_mask[100, 100] == 255
    # Walkable area around pillar at (50, 50) must be free
    assert processed.free_mask[50, 50] == 255
    # Exterior boundary at (5, 5) outside building
    assert processed.exterior_mask[5, 5] == 255


def test_debug_stage_rendering():
    img_bytes = (FIXTURES_DIR / "l_shape.png").read_bytes()
    processed = process_floor_plan_image(img_bytes, wall_threshold=127)

    stages = ["gray", "wall_mask", "free_mask", "exterior", "distance_transform"]
    for stage in stages:
        png_bytes = render_debug_stage_png(processed, stage)
        assert len(png_bytes) > 0
        assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")


def test_debug_endpoint():
    img_bytes = (FIXTURES_DIR / "corridor.png").read_bytes()
    upload_res = client.post(
        "/api/v1/plans",
        files={"file": ("corridor.png", img_bytes, "image/png")},
    )
    assert upload_res.status_code == 201
    plan_id = upload_res.json()["plan_id"]

    for stage in ["wall_mask", "free_mask", "distance_transform"]:
        res = client.get(f"/api/v1/plans/{plan_id}/debug/{stage}?wall_threshold=120")
        assert res.status_code == 200
        assert res.headers["content-type"] == "image/png"
        assert res.content.startswith(b"\x89PNG\r\n\x1a\n")
