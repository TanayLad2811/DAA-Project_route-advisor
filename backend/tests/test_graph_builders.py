from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.graph import NodeType
from app.services.graph_builder_grid import build_grid_graph
from app.services.graph_builder_skeleton import build_skeleton_graph
from app.services.image_processing import process_floor_plan_image

client = TestClient(app)
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_t_junction_skeleton_structure():
    """Skeleton builder on 'T' fixture must produce 1 junction and 3 endpoints."""
    img_bytes = (FIXTURES_DIR / "t_junction.png").read_bytes()
    processed = process_floor_plan_image(img_bytes, wall_threshold=127)

    graph = build_skeleton_graph(processed, plan_id="test_t", spur_len=10)

    junctions = [n for n in graph.nodes if n.type == NodeType.JUNCTION]
    endpoints = [n for n in graph.nodes if n.type == NodeType.DEAD_END]

    assert len(junctions) == 1
    assert len(endpoints) == 3
    assert len(graph.edges) == 3


def test_office_grid_graph_connectivity():
    """Grid graph on office rooms must connect across doorways."""
    img_bytes = (FIXTURES_DIR / "office_rooms.png").read_bytes()
    processed = process_floor_plan_image(img_bytes, wall_threshold=127)

    graph = build_grid_graph(processed, plan_id="test_office", cell_size=8)
    assert len(graph.nodes) > 100
    assert len(graph.edges) > 100

    # Ensure nodes exist in rooms (e.g. room 1 at x=50, y=50) and in hallway (x=150, y=100)
    has_room_node = any(20 < n.x < 100 and 20 < n.y < 80 for n in graph.nodes)
    has_hallway_node = any(50 < n.x < 250 and 90 < n.y < 110 for n in graph.nodes)
    assert has_room_node
    assert has_hallway_node


def test_grid_builder_auto_increases_cell_size_on_cap():
    """When node limit is low, grid builder must auto-increase cell size and warn."""
    img_bytes = (FIXTURES_DIR / "office_rooms.png").read_bytes()
    processed = process_floor_plan_image(img_bytes, wall_threshold=127)

    # Force a tiny node limit of 50 nodes
    graph = build_grid_graph(processed, plan_id="test_cap", cell_size=2, max_nodes=50)
    assert len(graph.nodes) <= 150
    assert any("limit" in w.lower() for w in graph.warnings)


def test_api_build_graph_and_calibrate():
    """Tests POST /plans/{id}/graph and PATCH /plans/{id}/scale via REST API."""
    img_bytes = (FIXTURES_DIR / "corridor.png").read_bytes()
    upload_res = client.post(
        "/api/v1/plans",
        files={"file": ("corridor.png", img_bytes, "image/png")},
    )
    plan_id = upload_res.json()["plan_id"]

    # Build grid graph
    build_res = client.post(
        f"/api/v1/plans/{plan_id}/graph",
        json={"strategy": "grid", "wall_threshold": 127, "cell_size": 10},
    )
    assert build_res.status_code == 201
    data = build_res.json()
    assert "graph" in data
    assert "suggested_exits" in data
    assert data["graph"]["strategy"] == "grid"
    assert len(data["graph"]["nodes"]) > 0

    # Calibrate scale: (0, 50) to (300, 50) is 300 px = 30 meters
    scale_res = client.patch(
        f"/api/v1/plans/{plan_id}/scale",
        json={"point_a": [0, 50], "point_b": [300, 50], "real_distance_m": 30.0},
    )
    assert scale_res.status_code == 200
    calibrated = scale_res.json()
    assert calibrated["meters_per_pixel"] is not None
    assert 0.09 <= calibrated["meters_per_pixel"] <= 0.11


def test_api_update_graph_validation():
    """Tests PUT /plans/{id}/graph validates consistency (rejects self loops & dangling edges)."""
    img_bytes = (FIXTURES_DIR / "corridor.png").read_bytes()
    upload_res = client.post(
        "/api/v1/plans",
        files={"file": ("corridor.png", img_bytes, "image/png")},
    )
    plan_id = upload_res.json()["plan_id"]
    client.post(f"/api/v1/plans/{plan_id}/graph", json={"strategy": "skeleton"})

    # Self-loop
    invalid_graph = {
        "plan_id": plan_id,
        "strategy": "skeleton",
        "image_width": 100,
        "image_height": 100,
        "nodes": [{"id": 1, "x": 10, "y": 10, "type": "walkable"}],
        "edges": [{"id": 1, "source": 1, "target": 1, "length_px": 5.0, "blocked": False}],
        "exits": [],
    }
    res = client.put(f"/api/v1/plans/{plan_id}/graph", json=invalid_graph)
    assert res.status_code == 422
    assert "Self-loop" in res.json()["detail"]
