from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def setup_office_plan():
    """Helper that uploads office fixture, builds skeleton graph, and designates exit."""
    img_bytes = (FIXTURES_DIR / "office_rooms.png").read_bytes()
    upload_res = client.post(
        "/api/v1/plans",
        files={"file": ("office.png", img_bytes, "image/png")},
    )
    plan_id = upload_res.json()["plan_id"]

    # Build skeleton graph
    build_res = client.post(
        f"/api/v1/plans/{plan_id}/graph",
        json={"strategy": "skeleton", "wall_threshold": 127},
    )
    data = build_res.json()
    graph = data["graph"]

    # Pick exit (e.g. node closest to right exit at x=285, y=100)
    best_exit_node = min(
        graph["nodes"], key=lambda n: (n["x"] - 285) ** 2 + (n["y"] - 100) ** 2
    )
    client.patch(
        f"/api/v1/plans/{plan_id}/graph/exits",
        json={"exit_ids": [best_exit_node["id"]]},
    )

    return plan_id, graph, best_exit_node["id"]


def test_routing_api_bfs():
    plan_id, graph, exit_id = setup_office_plan()
    # Pick start node in room 1 (left side)
    start_node = min(graph["nodes"], key=lambda n: n["x"])

    res = client.post(
        f"/api/v1/plans/{plan_id}/route",
        json={
            "algorithm": "bfs",
            "start": start_node["id"],
            "exit_ids": [exit_id],
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["algorithm"] == "bfs"
    assert len(data["routes"]) == 1
    assert data["routes"][0]["exit_id"] == exit_id
    assert len(data["routes"][0]["points"]) >= 2
    assert data["stats"]["nodes_visited"] > 0


def test_routing_api_dijkstra_and_alternatives():
    plan_id, graph, exit_id = setup_office_plan()
    start_node = min(graph["nodes"], key=lambda n: n["x"])

    res = client.post(
        f"/api/v1/plans/{plan_id}/route",
        json={
            "algorithm": "shortest_path",
            "start": [start_node["x"], start_node["y"]],  # Test coordinate snapping
            "exit_ids": [exit_id],
            "options": {"shortest_variant": "dijkstra", "alternatives": 2},
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["algorithm"] == "dijkstra"
    assert len(data["routes"]) >= 1
    assert data["routes"][0]["distance_px"] > 0


def test_routing_api_astar():
    plan_id, graph, exit_id = setup_office_plan()
    start_node = min(graph["nodes"], key=lambda n: n["x"])

    res = client.post(
        f"/api/v1/plans/{plan_id}/route",
        json={
            "algorithm": "shortest_path",
            "start": start_node["id"],
            "exit_ids": [exit_id],
            "options": {"shortest_variant": "astar"},
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["algorithm"] == "astar"
    assert len(data["routes"]) == 1


def test_routing_api_dfs_first_and_all():
    plan_id, graph, exit_id = setup_office_plan()
    start_node = min(graph["nodes"], key=lambda n: n["x"])

    # DFS First
    res_first = client.post(
        f"/api/v1/plans/{plan_id}/route",
        json={
            "algorithm": "dfs",
            "start": start_node["id"],
            "exit_ids": [exit_id],
            "options": {"dfs_mode": "first"},
        },
    )
    assert res_first.status_code == 200
    assert len(res_first.json()["routes"]) == 1

    # DFS All
    res_all = client.post(
        f"/api/v1/plans/{plan_id}/route",
        json={
            "algorithm": "dfs",
            "start": start_node["id"],
            "exit_ids": [exit_id],
            "options": {"dfs_mode": "all", "max_paths": 10},
        },
    )
    assert res_all.status_code == 200
    assert len(res_all.json()["routes"]) >= 1


def test_dfs_guardrail_on_dense_grid_graph():
    """DFS all paths on grid graph with > 2000 nodes must return 422 with guardrail explanation."""
    img_bytes = (FIXTURES_DIR / "office_rooms.png").read_bytes()
    upload_res = client.post(
        "/api/v1/plans",
        files={"file": ("office_dense.png", img_bytes, "image/png")},
    )
    plan_id = upload_res.json()["plan_id"]

    # Build dense grid graph with cell size 3
    client.post(
        f"/api/v1/plans/{plan_id}/graph",
        json={"strategy": "grid", "cell_size": 3, "wall_threshold": 127},
    )

    res = client.post(
        f"/api/v1/plans/{plan_id}/route",
        json={
            "algorithm": "dfs",
            "start": [50, 50],
            "exit_ids": [1],
            "options": {"dfs_mode": "all"},
        },
    )
    assert res.status_code == 422
    assert "prohibitive" in res.json()["detail"].lower()
