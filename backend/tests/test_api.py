import io

from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings
from app.main import app

client = TestClient(app)


def create_test_image(width: int = 100, height: int = 80, color: str = "white") -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_upload_valid_png():
    img_bytes = create_test_image(200, 150)
    response = client.post(
        "/api/v1/plans",
        files={"file": ("floorplan.png", img_bytes, "image/png")},
    )
    assert response.status_code == 201
    data = response.json()
    assert "plan_id" in data
    assert data["width"] == 200
    assert data["height"] == 150
    assert data["scale_factor"] == 1.0
    assert data["image_url"].endswith(f"/api/v1/plans/{data['plan_id']}/image")

    # Fetch uploaded image
    plan_id = data["plan_id"]
    img_res = client.get(f"/api/v1/plans/{plan_id}/image")
    assert img_res.status_code == 200
    assert img_res.headers["content-type"] == "image/png"

    # Fetch metadata
    meta_res = client.get(f"/api/v1/plans/{plan_id}")
    assert meta_res.status_code == 200
    meta = meta_res.json()
    assert meta["plan_id"] == plan_id
    assert meta["original_width"] == 200

    # Delete
    del_res = client.delete(f"/api/v1/plans/{plan_id}")
    assert del_res.status_code == 200
    assert client.get(f"/api/v1/plans/{plan_id}").status_code == 404


def test_upload_corrupted_file():
    corrupted_bytes = b"NOT_A_VALID_IMAGE_DATA_1234567890"
    response = client.post(
        "/api/v1/plans",
        files={"file": ("corrupt.png", corrupted_bytes, "image/png")},
    )
    assert response.status_code == 400
    assert "Invalid or corrupted" in response.json()["detail"]


def test_upload_oversized_file():
    # 10 MB + 1 byte
    oversized_bytes = b"0" * (settings.max_upload_size_bytes + 1)
    response = client.post(
        "/api/v1/plans",
        files={"file": ("big.png", oversized_bytes, "image/png")},
    )
    assert response.status_code == 413
    assert "exceeds size limit" in response.json()["detail"]


def test_get_nonexistent_plan():
    response = client.get("/api/v1/plans/non-existent-uuid")
    assert response.status_code == 404


def test_downscale_large_dimension():
    # Image with dimension 4500x1000 (> 4000)
    img_bytes = create_test_image(4500, 1000)
    response = client.post(
        "/api/v1/plans",
        files={"file": ("large.png", img_bytes, "image/png")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["width"] == 4000
    assert data["height"] == round(1000 * (4000 / 4500))
    assert data["scale_factor"] < 1.0
