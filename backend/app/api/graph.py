import math

from fastapi import APIRouter, HTTPException, status

from app.api.routes import invalidate_graph_cache
from app.schemas.graph import (
    Graph,
    GraphBuildRequest,
    GraphBuildResponse,
    ScaleCalibrationRequest,
    SuggestedExit,
)
from app.services.door_detection import detect_building_doors_and_exits
from app.services.exit_detection import detect_suggested_exits
from app.services.graph_builder_grid import build_grid_graph
from app.services.graph_builder_skeleton import build_skeleton_graph
from app.services.image_processing import process_floor_plan_image
from app.services.storage import repo

router = APIRouter(prefix="/plans", tags=["Graph"])


@router.post("/{plan_id}/graph", response_model=GraphBuildResponse, status_code=status.HTTP_201_CREATED)
def build_graph(plan_id: str, req: GraphBuildRequest):
    """Builds a walkable graph from the floor plan with automatic door and exit detection."""
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
            wall_threshold=req.wall_threshold,
            invert=req.invert,
            close_kernel=req.close_kernel,
            min_clearance_px=req.min_clearance_px,
            filter_annotations=req.filter_annotations,
        )

        # Detect doors and building envelope exits
        detected_doors = []
        if req.detect_doors:
            detected_doors, _, _ = detect_building_doors_and_exits(processed.original_rgb)

        if req.strategy == "skeleton":
            graph = build_skeleton_graph(
                processed, plan_id, spur_len=req.spur_len, doors=detected_doors
            )
        else:
            graph = build_grid_graph(
                processed,
                plan_id,
                cell_size=req.cell_size,
                min_clearance_px=req.min_clearance_px,
            )

        # Connect detected doors to their nearest graph nodes
        if graph.nodes:
            for door in detected_doors:
                nearest_n = min(
                    graph.nodes, key=lambda n: math.hypot(n.x - door.x, n.y - door.y)
                )
                door.nearest_node_id = nearest_n.id

        graph.doors = detected_doors

        # Detect suggested exits: prioritize exterior building doors!
        suggested_exits: list[SuggestedExit] = []
        for door in detected_doors:
            if door.type.value == "exit" and door.nearest_node_id is not None:
                suggested_exits.append(
                    SuggestedExit(
                        x=door.x,
                        y=door.y,
                        confidence=door.confidence,
                        nearest_node_id=door.nearest_node_id,
                    )
                )

        # Also run boundary proximity exit detector
        perimeter_exits = detect_suggested_exits(graph, processed)
        for pe in perimeter_exits:
            if not any(math.hypot(pe.x - se.x, pe.y - se.y) < 30 for se in suggested_exits):
                suggested_exits.append(pe)

        # Automatically mark detected exterior exits on the graph if no exits were set yet
        existing_graph = repo.get_graph(plan_id)
        if existing_graph and existing_graph.exits:
            node_ids = {n.id for n in graph.nodes}
            graph.exits = [e for e in existing_graph.exits if e in node_ids]
            graph.meters_per_pixel = existing_graph.meters_per_pixel
        elif suggested_exits:
            # Auto-designate top detected exit doors
            auto_exit_ids = [se.nearest_node_id for se in suggested_exits[:3] if se.nearest_node_id is not None]
            graph.exits = list(set(auto_exit_ids))

        repo.save_graph(plan_id, graph)
        invalidate_graph_cache(plan_id)

        return GraphBuildResponse(
            graph=graph,
            suggested_exits=suggested_exits,
            detected_doors=detected_doors,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error building graph: {e}",
        ) from e


@router.get("/{plan_id}/graph", response_model=Graph)
def get_graph(plan_id: str):
    """Fetches the current graph for a plan."""
    graph = repo.get_graph(plan_id)
    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph for floor plan '{plan_id}' has not been built yet.",
        )
    return graph


@router.put("/{plan_id}/graph", response_model=Graph)
def update_graph(plan_id: str, new_graph: Graph):
    """Replaces the graph with user edits, validating graph consistency."""
    node_ids = set()
    for n in new_graph.nodes:
        if n.id in node_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Duplicate node ID detected: {n.id}",
            )
        node_ids.add(n.id)

    edge_ids = set()
    for e in new_graph.edges:
        if e.id in edge_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Duplicate edge ID detected: {e.id}",
            )
        edge_ids.add(e.id)
        if e.source == e.target:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Self-loop detected on edge {e.id} (node {e.source})",
            )
        if e.source not in node_ids or e.target not in node_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Dangling edge {e.id} connecting unknown node(s): ({e.source}, {e.target})",
            )

    repo.save_graph(plan_id, new_graph)
    invalidate_graph_cache(plan_id)
    return new_graph


@router.patch("/{plan_id}/graph/exits", response_model=Graph)
def update_exits(plan_id: str, payload: dict):
    """Updates the list of designated exit node IDs."""
    graph = repo.get_graph(plan_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")

    exit_ids = payload.get("exit_ids", [])
    valid_node_ids = {n.id for n in graph.nodes}
    for eid in exit_ids:
        if eid not in valid_node_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Exit node {eid} does not exist in graph",
            )

    graph.exits = exit_ids
    repo.save_graph(plan_id, graph)
    invalidate_graph_cache(plan_id)
    return graph


@router.patch("/{plan_id}/scale", response_model=Graph)
def calibrate_scale(plan_id: str, req: ScaleCalibrationRequest):
    """Calibrates meters-per-pixel using two clicked points and real-world distance."""
    graph = repo.get_graph(plan_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")

    dx = req.point_b[0] - req.point_a[0]
    dy = req.point_b[1] - req.point_a[1]
    pixel_dist = math.hypot(dx, dy)

    if pixel_dist < 1.0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Calibration points are too close together.",
        )
    if req.real_distance_m <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Real distance must be positive.",
        )

    graph.meters_per_pixel = round(req.real_distance_m / pixel_dist, 5)
    repo.save_graph(plan_id, graph)
    invalidate_graph_cache(plan_id)
    return graph
