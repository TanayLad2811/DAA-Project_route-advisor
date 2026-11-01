import heapq
import math
import time

from app.algorithms.graph_ds import AdjacencyGraph
from app.algorithms.metrics import build_route_path
from app.schemas.route import RouteOptions, RouteResult, RouteStats


def _euclidean_heuristic(
    ag: AdjacencyGraph,
    node: int,
    exit_coords: list[tuple[float, float]],
) -> float:
    """Computes minimum Euclidean distance from node to any exit (admissible heuristic)."""
    node_obj = ag.nodes.get(node)
    if not node_obj:
        return 0.0

    min_h = float("inf")
    for ex_x, ex_y in exit_coords:
        dist = math.hypot(node_obj.x - ex_x, node_obj.y - ex_y)
        min_h = min(min_h, dist)

    return min_h if min_h != float("inf") else 0.0


def _astar_single(
    ag: AdjacencyGraph,
    start_node: int,
    exit_nodes: set[int],
    exit_coords: list[tuple[float, float]],
    edge_penalties: dict[tuple[int, int], float] | None = None,
) -> tuple[list[int] | None, int | None, list[int]]:
    """A* search with Euclidean heuristic. Returns (path, target_exit, explored_nodes)."""
    penalties = edge_penalties or {}
    g_scores: dict[int, float] = {start_node: 0.0}
    parent: dict[int, int] = {}
    explored_nodes: list[int] = []

    h_start = _euclidean_heuristic(ag, start_node, exit_coords)
    # (f_score, g_score, node)
    open_set = [(h_start, 0.0, start_node)]
    closed_set: set[int] = set()
    target_exit: int | None = None

    while open_set:
        _, g_curr, u = heapq.heappop(open_set)

        if u in closed_set:
            continue
        closed_set.add(u)
        explored_nodes.append(u)

        if u in exit_nodes:
            target_exit = u
            break

        for v, base_w, _ in ag.neighbors(u):
            if v in closed_set:
                continue

            penalty = penalties.get((min(u, v), max(u, v)), 1.0)
            tentative_g = g_curr + (base_w * penalty)

            if tentative_g < g_scores.get(v, float("inf")):
                g_scores[v] = tentative_g
                parent[v] = u
                h = _euclidean_heuristic(ag, v, exit_coords)
                f_score = tentative_g + h
                heapq.heappush(open_set, (f_score, tentative_g, v))

    if target_exit is None:
        return None, None, explored_nodes

    curr = target_exit
    path = [curr]
    while curr != start_node:
        curr = parent[curr]
        path.append(curr)
    path.reverse()

    return path, target_exit, explored_nodes


def run_astar(
    ag: AdjacencyGraph,
    start_node: int,
    exit_nodes: list[int],
    options: RouteOptions | None = None,
) -> RouteResult:
    """Executes A* search using Euclidean distance to nearest exit as an admissible heuristic."""
    start_time = time.perf_counter()
    options = options or RouteOptions()
    exits_set = set(exit_nodes)
    warnings: list[str] = []

    if start_node not in ag.nodes:
        return RouteResult(
            algorithm="astar",
            routes=[],
            explored_nodes=[],
            stats=RouteStats(nodes_visited=0, runtime_ms=0.0, routes_found=0),
            warnings=[f"Start node {start_node} does not exist in graph."],
        )

    if not exits_set:
        return RouteResult(
            algorithm="astar",
            routes=[],
            explored_nodes=[],
            stats=RouteStats(nodes_visited=0, runtime_ms=0.0, routes_found=0),
            warnings=["No exits defined."],
        )

    # Edge Case: Start is at an exit
    if start_node in exits_set:
        route = build_route_path(ag, [start_node], start_node, options.walking_speed_mps)
        runtime = (time.perf_counter() - start_time) * 1000.0
        return RouteResult(
            algorithm="astar",
            routes=[route],
            explored_nodes=[start_node],
            stats=RouteStats(nodes_visited=1, runtime_ms=round(runtime, 2), routes_found=1),
            warnings=["Start location is already at an exit."],
        )

    exit_coords = [ag.node_coords(e) for e in exits_set if e in ag.nodes]

    primary_path, target_exit, all_explored = _astar_single(
        ag, start_node, exits_set, exit_coords
    )

    if not primary_path or target_exit is None:
        runtime = (time.perf_counter() - start_time) * 1000.0
        return RouteResult(
            algorithm="astar",
            routes=[],
            explored_nodes=all_explored,
            stats=RouteStats(
                nodes_visited=len(all_explored),
                runtime_ms=round(runtime, 2),
                routes_found=0,
            ),
            warnings=["No route found: all exits are unreachable or blocked."],
        )

    routes_found = [primary_path]
    k_alternatives = max(1, options.alternatives or 1)
    edge_penalties: dict[tuple[int, int], float] = {}

    for _ in range(1, k_alternatives):
        last_route = routes_found[-1]
        for i in range(len(last_route) - 1):
            e_pair = (min(last_route[i], last_route[i + 1]), max(last_route[i], last_route[i + 1]))
            edge_penalties[e_pair] = edge_penalties.get(e_pair, 1.0) * 1.6

        alt_path, _alt_exit, _ = _astar_single(
            ag, start_node, exits_set, exit_coords, edge_penalties
        )
        if alt_path and alt_path not in routes_found:
            routes_found.append(alt_path)
        else:
            break

    runtime = (time.perf_counter() - start_time) * 1000.0

    routes = [
        build_route_path(ag, p, p[-1], options.walking_speed_mps)
        for p in routes_found
    ]

    return RouteResult(
        algorithm="astar",
        routes=routes,
        explored_nodes=all_explored,
        stats=RouteStats(
            nodes_visited=len(all_explored),
            runtime_ms=round(runtime, 2),
            routes_found=len(routes),
        ),
        warnings=warnings,
    )
