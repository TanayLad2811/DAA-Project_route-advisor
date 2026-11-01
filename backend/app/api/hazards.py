from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.routes import invalidate_graph_cache
from app.schemas.graph import Graph, Hazard, HazardCreateRequest
from app.services.storage import repo

router = APIRouter(prefix="/plans", tags=["Hazards"])


class ToggleEdgesRequest(BaseModel):
    edge_ids: list[int]


def line_segments_intersect(
    p1: tuple[float, float],
    p2: tuple[float, float],
    q1: tuple[float, float],
    q2: tuple[float, float],
) -> bool:
    """Checks whether line segment p1-p2 intersects segment q1-q2 using cross products."""
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])

    return ccw(p1, q1, q2) != ccw(p2, q1, q2) and ccw(p1, p2, q1) != ccw(p1, p2, q2)


def point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    """Ray casting algorithm to determine if point is inside a polygon."""
    x, y = point
    n = len(polygon)
    inside = False
    p1x, p1y = polygon[0]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
            if p1y != p2y:
                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
            if p1x == p2x or x <= xinters:
                inside = not inside
        p1x, p1y = p2x, p2y
    return inside


@router.get("/{plan_id}/hazards", response_model=list[Hazard])
def list_hazards(plan_id: str):
    """Lists all active hazards for a floor plan."""
    return repo.get_hazards(plan_id)


@router.post("/{plan_id}/hazards", response_model=Hazard, status_code=status.HTTP_201_CREATED)
def add_hazard(plan_id: str, req: HazardCreateRequest):
    """Creates a corridor or polygon region hazard and blocks all affected graph edges."""
    graph = repo.get_graph(plan_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")

    hazards = repo.get_hazards(plan_id)
    new_id = max([h.id for h in hazards], default=0) + 1

    blocked_edge_ids = list(req.edge_ids or [])

    # If polygon hazard, find all intersecting graph edges
    if req.kind == "region" and req.polygon and len(req.polygon) >= 3:
        node_map = {n.id: (n.x, n.y) for n in graph.nodes}
        poly = req.polygon
        n_poly = len(poly)

        for edge in graph.edges:
            if edge.id in blocked_edge_ids:
                continue
            if edge.source not in node_map or edge.target not in node_map:
                continue

            u_pt = node_map[edge.source]
            v_pt = node_map[edge.target]

            # Check if either endpoint is inside polygon
            if point_in_polygon(u_pt, poly) or point_in_polygon(v_pt, poly):
                blocked_edge_ids.append(edge.id)
                continue

            # Check if edge line segment intersects any polygon boundary edge
            edge_pts = edge.polyline if edge.polyline and len(edge.polyline) >= 2 else [u_pt, v_pt]
            intersects = False
            for k in range(len(edge_pts) - 1):
                seg_a = edge_pts[k]
                seg_b = edge_pts[k + 1]
                for j in range(n_poly):
                    poly_a = poly[j]
                    poly_b = poly[(j + 1) % n_poly]
                    if line_segments_intersect(seg_a, seg_b, poly_a, poly_b):
                        intersects = True
                        break
                if intersects:
                    break

            if intersects:
                blocked_edge_ids.append(edge.id)

    # Mark edges in graph
    blocked_set = set(blocked_edge_ids)
    for edge in graph.edges:
        if edge.id in blocked_set:
            edge.blocked = True

    repo.save_graph(plan_id, graph)

    hazard = Hazard(
        id=new_id,
        kind=req.kind,
        edge_ids=blocked_edge_ids,
        polygon=req.polygon or [],
        label=req.label,
    )
    hazards.append(hazard)
    repo.save_hazards(plan_id, hazards)
    invalidate_graph_cache(plan_id)

    return hazard


@router.delete("/{plan_id}/hazards/{hazard_id}", status_code=status.HTTP_200_OK)
def remove_hazard(plan_id: str, hazard_id: int):
    """Removes a hazard and unblocks its affected edges if no other hazard blocks them."""
    graph = repo.get_graph(plan_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")

    hazards = repo.get_hazards(plan_id)
    target_hazard = next((h for h in hazards if h.id == hazard_id), None)
    if not target_hazard:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hazard not found")

    remaining_hazards = [h for h in hazards if h.id != hazard_id]
    repo.save_hazards(plan_id, remaining_hazards)

    # Re-evaluate blocked edges
    still_blocked = set()
    for h in remaining_hazards:
        for eid in h.edge_ids:
            still_blocked.add(eid)

    for edge in graph.edges:
        if edge.id in target_hazard.edge_ids and edge.id not in still_blocked:
            edge.blocked = False

    repo.save_graph(plan_id, graph)
    invalidate_graph_cache(plan_id)

    return {"status": "removed", "hazard_id": hazard_id}


@router.post("/{plan_id}/hazards/toggle-edges", response_model=Graph)
def toggle_edges(plan_id: str, req: ToggleEdgesRequest):
    """Toggles the blocked state for one or more edges and persists hazards."""
    graph = repo.get_graph(plan_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")

    hazards = repo.get_hazards(plan_id)
    target_ids = set(req.edge_ids)

    # Toggle blocked attribute on the graph edges
    for edge in graph.edges:
        if edge.id in target_ids:
            edge.blocked = not edge.blocked

    # Re-synchronize hazards list
    blocked_edge_ids_now = {e.id for e in graph.edges if e.blocked}
    new_hazards: list[Hazard] = []
    for h in hazards:
        updated_eids = [eid for eid in h.edge_ids if eid in blocked_edge_ids_now]
        if updated_eids or (h.kind == "region" and h.polygon):
            h.edge_ids = updated_eids
            new_hazards.append(h)

    # If any edge is newly blocked and not covered by an existing hazard, create an edge hazard
    accounted_for = {eid for h in new_hazards for eid in h.edge_ids}
    newly_blocked = blocked_edge_ids_now - accounted_for
    if newly_blocked:
        new_id = max([h.id for h in new_hazards], default=0) + 1
        new_hazards.append(
            Hazard(
                id=new_id,
                kind="edge",
                edge_ids=list(newly_blocked),
                polygon=[],
                label="Corridor Hazard",
            )
        )

    repo.save_graph(plan_id, graph)
    repo.save_hazards(plan_id, new_hazards)
    invalidate_graph_cache(plan_id)

    return graph


@router.post("/{plan_id}/hazards/clear-all", response_model=Graph)
def clear_all_hazards(plan_id: str):
    """Unblocks all corridor edges and deletes all hazards for the floor plan."""
    graph = repo.get_graph(plan_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")

    for edge in graph.edges:
        edge.blocked = False

    repo.save_hazards(plan_id, [])
    repo.save_graph(plan_id, graph)
    invalidate_graph_cache(plan_id)

    return graph


@router.post("/{plan_id}/hazards/unblock-edges", response_model=Graph)
def unblock_edges(plan_id: str, req: ToggleEdgesRequest):
    """Explicitly unblocks the specified edges and removes them from hazards."""
    graph = repo.get_graph(plan_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")

    target_ids = set(req.edge_ids)
    for edge in graph.edges:
        if edge.id in target_ids:
            edge.blocked = False

    hazards = repo.get_hazards(plan_id)
    blocked_edge_ids_now = {e.id for e in graph.edges if e.blocked}
    new_hazards: list[Hazard] = []
    for h in hazards:
        updated_eids = [eid for eid in h.edge_ids if eid in blocked_edge_ids_now]
        if updated_eids or (h.kind == "region" and h.polygon):
            h.edge_ids = updated_eids
            new_hazards.append(h)

    repo.save_hazards(plan_id, new_hazards)
    repo.save_graph(plan_id, graph)
    invalidate_graph_cache(plan_id)

    return graph


