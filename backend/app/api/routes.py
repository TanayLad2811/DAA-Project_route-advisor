from fastapi import APIRouter, HTTPException, status

from app.algorithms.astar import run_astar
from app.algorithms.bfs import run_bfs
from app.algorithms.dfs import run_dfs
from app.algorithms.dijkstra import run_dijkstra
from app.algorithms.graph_ds import AdjacencyGraph
from app.schemas.route import RouteRequest, RouteResult, RouteStats
from app.services.storage import repo
from app.utils.geometry import PointSnapper

router = APIRouter(prefix="/plans", tags=["Routing"])

# In-memory LRU cache for AdjacencyGraph instances
_graph_cache: dict[str, tuple[int, AdjacencyGraph]] = {}


def invalidate_graph_cache(plan_id: str | None = None) -> None:
    if plan_id:
        keys_to_delete = [k for k in _graph_cache if k.startswith(f"{plan_id}:")]
        for k in keys_to_delete:
            del _graph_cache[k]
    else:
        _graph_cache.clear()


def get_cached_adjacency_graph(plan_id: str) -> AdjacencyGraph:
    graph = repo.get_graph(plan_id)
    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph for plan '{plan_id}' has not been built yet.",
        )

    hazards = repo.get_hazards(plan_id)
    blocked_edge_ids = set()
    for h in hazards:
        for eid in h.edge_ids:
            blocked_edge_ids.add(eid)

    cache_key = f"{plan_id}:{graph.strategy}:{len(graph.nodes)}:{len(graph.edges)}:{len(blocked_edge_ids)}"
    if cache_key in _graph_cache:
        return _graph_cache[cache_key][1]

    ag = AdjacencyGraph.from_schema(graph, blocked_edge_ids=blocked_edge_ids)
    _graph_cache[cache_key] = (len(graph.nodes), ag)

    if len(_graph_cache) > 20:
        oldest_key = next(iter(_graph_cache))
        del _graph_cache[oldest_key]

    return ag


@router.post("/{plan_id}/route", response_model=RouteResult)
def compute_route(plan_id: str, req: RouteRequest):
    """Computes evacuation routes using BFS, DFS, or Dijkstra/A* shortest path algorithms."""
    graph = repo.get_graph(plan_id)
    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph for plan '{plan_id}' has not been built yet.",
        )

    # Determine start node ID with dual node + edge-polyline snapping
    start_node_id: int
    if isinstance(req.start, (tuple, list)):
        snapper = PointSnapper(graph.nodes, graph.edges)
        snapped_id, _ = snapper.snap_to_nearest_node((req.start[0], req.start[1]))
        if snapped_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not snap start location to any walkable graph node.",
            )
        start_node_id = snapped_id
    else:
        start_node_id = int(req.start)
        if start_node_id not in {n.id for n in graph.nodes}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Specified start node {start_node_id} does not exist in graph.",
            )

    # Determine exits
    exit_ids: list[int]
    if req.exit_ids:
        exit_ids = req.exit_ids
    elif graph.exits:
        exit_ids = graph.exits
    else:
        # Check if graph has detected exit doors
        door_exits = [
            d.nearest_node_id
            for d in graph.doors
            if d.type.value == "exit" and d.nearest_node_id is not None
        ]
        if door_exits:
            exit_ids = list(set(door_exits))
        else:
            return RouteResult(
                algorithm=req.algorithm,
                routes=[],
                explored_nodes=[],
                stats=RouteStats(nodes_visited=0, runtime_ms=0.0, routes_found=0),
                warnings=["No exits designated. Please mark at least one exit on the floor plan."],
            )

    # Guardrail: DFS "all routes" mode on dense graphs
    if (
        req.algorithm == "dfs"
        and req.options.dfs_mode == "all"
        and len(graph.nodes) > 2000
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"DFS 'all routes' path enumeration is computationally prohibitive on dense graphs "
                f"({len(graph.nodes):,} nodes). Please switch to the Skeleton graph strategy or use 'First route' mode."
            ),
        )

    ag = get_cached_adjacency_graph(plan_id)

    # Execute selected algorithm
    if req.algorithm == "bfs":
        result = run_bfs(ag, start_node=start_node_id, exit_nodes=exit_ids, options=req.options)
    elif req.algorithm == "dfs":
        result = run_dfs(ag, start_node=start_node_id, exit_nodes=exit_ids, options=req.options)
    elif req.algorithm == "shortest_path":
        if req.options.shortest_variant == "astar":
            result = run_astar(ag, start_node=start_node_id, exit_nodes=exit_ids, options=req.options)
        else:
            result = run_dijkstra(ag, start_node=start_node_id, exit_nodes=exit_ids, options=req.options)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown algorithm '{req.algorithm}'. Choose 'bfs', 'dfs', or 'shortest_path'.",
        )

    return result
