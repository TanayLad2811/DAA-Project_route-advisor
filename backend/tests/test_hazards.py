from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def setup_office_plan():
    img_bytes = (FIXTURES_DIR / "office_rooms.png").read_bytes()
    upload_res = client.post(
        "/api/v1/plans",
        files={"file": ("office.png", img_bytes, "image/png")},
    )
    plan_id = upload_res.json()["plan_id"]
    client.post(f"/api/v1/plans/{plan_id}/graph", json={"strategy": "skeleton"})

    # Fetch graph
    graph_res = client.get(f"/api/v1/plans/{plan_id}/graph")
    graph = graph_res.json()

    # Designate exit
    exit_node = min(graph["nodes"], key=lambda n: (n["x"] - 285) ** 2 + (n["y"] - 100) ** 2)
    client.patch(f"/api/v1/plans/{plan_id}/graph/exits", json={"exit_ids": [exit_node["id"]]})

    return plan_id, graph, exit_node["id"]


def test_edge_hazard_blocking_and_reroute():
    plan_id, graph, exit_id = setup_office_plan()
    start_node = min(graph["nodes"], key=lambda n: n["x"])

    # Compute baseline route
    base_res = client.post(
        f"/api/v1/plans/{plan_id}/route",
        json={"algorithm": "shortest_path", "start": start_node["id"], "exit_ids": [exit_id]},
    )
    assert base_res.status_code == 200
    base_route = base_res.json()["routes"][0]
    base_dist = base_route["distance_px"]

    # Identify first edge on the baseline path
    u, v = base_route["node_ids"][0], base_route["node_ids"][1]
    edge_to_block = None
    for e in graph["edges"]:
        if (e["source"] == u and e["target"] == v) or (e["source"] == v and e["target"] == u):
            edge_to_block = e["id"]
            break

    assert edge_to_block is not None

    # Add hazard on this edge
    haz_res = client.post(
        f"/api/v1/plans/{plan_id}/hazards",
        json={"kind": "edge", "edge_ids": [edge_to_block], "label": "Fire Corridor"},
    )
    assert haz_res.status_code == 201
    hazard_id = haz_res.json()["id"]

    # Recompute route - must now reroute around the blocked edge or have different path
    reroute_res = client.post(
        f"/api/v1/plans/{plan_id}/route",
        json={"algorithm": "shortest_path", "start": start_node["id"], "exit_ids": [exit_id]},
    )
    assert reroute_res.status_code == 200
    new_route_data = reroute_res.json()

    # If route exists, it must not use the blocked edge
    if new_route_data["routes"]:
        new_path = new_route_data["routes"][0]["node_ids"]
        for i in range(len(new_path) - 1):
            assert not (
                (new_path[i] == u and new_path[i + 1] == v)
                or (new_path[i] == v and new_path[i + 1] == u)
            )

    # Delete hazard
    del_res = client.delete(f"/api/v1/plans/{plan_id}/hazards/{hazard_id}")
    assert del_res.status_code == 200

    # Route returns to baseline
    restored_res = client.post(
        f"/api/v1/plans/{plan_id}/route",
        json={"algorithm": "shortest_path", "start": start_node["id"], "exit_ids": [exit_id]},
    )
    assert restored_res.status_code == 200
    assert restored_res.json()["routes"][0]["distance_px"] == base_dist
