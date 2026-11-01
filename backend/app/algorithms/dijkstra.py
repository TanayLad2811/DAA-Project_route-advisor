import heapq
import time

from app.algorithms.graph_ds import AdjacencyGraph
from app.algorithms.metrics import build_route_path
from app.schemas.route import RouteOptions, RouteResult, RouteStats


def _dijkstra_single(
    ag: AdjacencyGraph,
    start_node: int,
    exit_nodes: set[int],
    edge_penalties: dict[tuple[int, int], float] | None = None,
) -> tuple[list[int] | None, int | None, list[int]]:
    """Single-source multi-target Dijkstra. Returns (path, target_exit, explored_nodes)."""
    penalties = edge_penalties or {}
    distances: dict[int, float] = {start_node: 0.0}
    parent: dict[int, int] = {}
    explored_nodes: list[int] = []
    # (distance, node)
    pq = [(0.0, start_node)]
    visited: set[int] = set()
    target_exit: int | None = None

    while pq:
        d, u = heapq.heappop(pq)

        if u in visited:
            continue
        visited.add(u)
        explored_nodes.append(u)

        if u in exit_nodes:
            target_exit = u
            break

        for v, base_w, _ in ag.neighbors(u):
            if v in visited:
                continue

            penalty = penalties.get((min(u, v), max(u, v)), 1.0)
            edge_w = base_w * penalty
            new_dist = d + edge_w

            if new_dist < distances.get(v, float("inf")):
                distances[v] = new_dist
                parent[v] = u
                heapq.heappush(pq, (new_dist, v))

    if target_exit is None:
        return None, None, explored_nodes

    curr = target_exit
    path = [curr]
    while curr != start_node:
        curr = parent[curr]
        path.append(curr)
    path.reverse()

    return path, target_exit, explored_nodes


def run_dijkstra(
    ag: AdjacencyGraph,
    start_node: int,
    exit_nodes: list[int],
    options: RouteOptions | None = None,
) -> RouteResult:
    """Executes Dijkstra's algorithm to find shortest evacuation route(s) with k-alternatives."""
    start_time = time.perf_counter()
    options = options or RouteOptions()
    exits_set = set(exit_nodes)
    warnings: list[str] = []

    if start_node not in ag.nodes:
        return RouteResult(
            algorithm="dijkstra",
            routes=[],
            explored_nodes=[],
            stats=RouteStats(nodes_visited=0, runtime_ms=0.0, routes_found=0),
            warnings=[f"Start node {start_node} does not exist in graph."],
        )

    if not exits_set:
        return RouteResult(
            algorithm="dijkstra",
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
            algorithm="dijkstra",
            routes=[route],
            explored_nodes=[start_node],
            stats=RouteStats(nodes_visited=1, runtime_ms=round(runtime, 2), routes_found=1),
            warnings=["Start location is already at an exit."],
        )

    # Find primary shortest path
    primary_path, target_exit, all_explored = _dijkstra_single(ag, start_node, exits_set)

    if not primary_path or target_exit is None:
        runtime = (time.perf_counter() - start_time) * 1000.0
        return RouteResult(
            algorithm="dijkstra",
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

    # Penalty-method for k-alternative routes
    for _ in range(1, k_alternatives):
        # Penalize edges in the most recently found route
        last_route = routes_found[-1]
        for i in range(len(last_route) - 1):
            e_pair = (min(last_route[i], last_route[i + 1]), max(last_route[i], last_route[i + 1]))
            edge_penalties[e_pair] = edge_penalties.get(e_pair, 1.0) * 1.6

        alt_path, _alt_exit, _ = _dijkstra_single(ag, start_node, exits_set, edge_penalties)
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
        algorithm="dijkstra",
        routes=routes,
        explored_nodes=all_explored,
        stats=RouteStats(
            nodes_visited=len(all_explored),
            runtime_ms=round(runtime, 2),
            routes_found=len(routes),
        ),
        warnings=warnings,
    )
