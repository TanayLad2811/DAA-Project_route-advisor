import time
from collections import deque

from app.algorithms.graph_ds import AdjacencyGraph
from app.algorithms.metrics import build_route_path
from app.schemas.route import RouteOptions, RouteResult, RouteStats


def run_bfs(
    ag: AdjacencyGraph,
    start_node: int,
    exit_nodes: list[int],
    options: RouteOptions | None = None,
) -> RouteResult:
    """Executes Breadth-First Search (BFS) finding fewest-hop route to the nearest exit."""
    start_time = time.perf_counter()
    options = options or RouteOptions()
    exits_set = set(exit_nodes)
    warnings: list[str] = []

    if start_node not in ag.nodes:
        return RouteResult(
            algorithm="bfs",
            routes=[],
            explored_nodes=[],
            stats=RouteStats(nodes_visited=0, runtime_ms=0.0, routes_found=0),
            warnings=[f"Start node {start_node} does not exist in graph."],
        )

    if not exits_set:
        return RouteResult(
            algorithm="bfs",
            routes=[],
            explored_nodes=[],
            stats=RouteStats(nodes_visited=0, runtime_ms=0.0, routes_found=0),
            warnings=["No exits defined."],
        )

    # Edge Case: Start is already at an exit
    if start_node in exits_set:
        route = build_route_path(ag, [start_node], start_node, options.walking_speed_mps)
        runtime = (time.perf_counter() - start_time) * 1000.0
        return RouteResult(
            algorithm="bfs",
            routes=[route],
            explored_nodes=[start_node],
            stats=RouteStats(nodes_visited=1, runtime_ms=round(runtime, 2), routes_found=1),
            warnings=["Start location is already at an exit."],
        )

    queue = deque([start_node])
    visited: set[int] = {start_node}
    parent: dict[int, int] = {}
    explored_nodes: list[int] = []
    target_exit: int | None = None

    while queue:
        u = queue.popleft()
        explored_nodes.append(u)

        if u in exits_set:
            target_exit = u
            break

        for v, _, _ in ag.neighbors(u):
            if v not in visited:
                visited.add(v)
                parent[v] = u
                queue.append(v)

    runtime = (time.perf_counter() - start_time) * 1000.0

    if target_exit is None:
        warnings.append("No route found: all exits are unreachable or blocked.")
        return RouteResult(
            algorithm="bfs",
            routes=[],
            explored_nodes=explored_nodes,
            stats=RouteStats(
                nodes_visited=len(explored_nodes),
                runtime_ms=round(runtime, 2),
                routes_found=0,
            ),
            warnings=warnings,
        )

    # Reconstruct path from start to target_exit
    curr = target_exit
    path = [curr]
    while curr != start_node:
        curr = parent[curr]
        path.append(curr)
    path.reverse()

    route = build_route_path(ag, path, target_exit, options.walking_speed_mps)

    return RouteResult(
        algorithm="bfs",
        routes=[route],
        explored_nodes=explored_nodes,
        stats=RouteStats(
            nodes_visited=len(explored_nodes),
            runtime_ms=round(runtime, 2),
            routes_found=1,
        ),
        warnings=warnings,
    )
