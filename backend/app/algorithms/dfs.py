import time
from collections import deque

from app.algorithms.graph_ds import AdjacencyGraph
from app.algorithms.metrics import build_route_path
from app.schemas.route import RouteOptions, RouteResult, RouteStats


def compute_exit_reachability(ag: AdjacencyGraph, exit_nodes: set[int]) -> set[int]:
    """Computes all nodes that can reach at least one exit using reverse BFS."""
    # Since graph is undirected, reverse reachability is equivalent to forward reachability from exits
    reachable: set[int] = set(exit_nodes)
    queue = deque(exit_nodes)

    while queue:
        u = queue.popleft()
        for v, _, _ in ag.neighbors(u):
            if v not in reachable:
                reachable.add(v)
                queue.append(v)

    return reachable


def run_dfs(
    ag: AdjacencyGraph,
    start_node: int,
    exit_nodes: list[int],
    options: RouteOptions | None = None,
) -> RouteResult:
    """Executes iterative Depth-First Search (DFS) in either 'first' or 'all' paths mode."""
    start_time = time.perf_counter()
    options = options or RouteOptions()
    exits_set = set(exit_nodes)
    warnings: list[str] = []

    if start_node not in ag.nodes:
        return RouteResult(
            algorithm="dfs",
            routes=[],
            explored_nodes=[],
            stats=RouteStats(nodes_visited=0, runtime_ms=0.0, routes_found=0),
            warnings=[f"Start node {start_node} does not exist in graph."],
        )

    if not exits_set:
        return RouteResult(
            algorithm="dfs",
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
            algorithm="dfs",
            routes=[route],
            explored_nodes=[start_node],
            stats=RouteStats(nodes_visited=1, runtime_ms=round(runtime, 2), routes_found=1),
            warnings=["Start location is already at an exit."],
        )

    # Pruning: precompute which nodes can reach an exit
    can_reach = compute_exit_reachability(ag, exits_set)
    if start_node not in can_reach:
        runtime = (time.perf_counter() - start_time) * 1000.0
        return RouteResult(
            algorithm="dfs",
            routes=[],
            explored_nodes=[start_node],
            stats=RouteStats(nodes_visited=1, runtime_ms=round(runtime, 2), routes_found=0),
            warnings=["Start is not connected to any exit."],
        )

    explored_nodes: list[int] = []
    found_paths: list[list[int]] = []
    max_paths = options.max_paths or 50
    max_depth = options.max_depth or 500
    timeout_s = 5.0

    if options.dfs_mode == "first":
        warnings.append("Note: DFS 'first' mode returns the first path encountered, which may not be the shortest.")
        # Standard iterative DFS with visited set
        stack = [(start_node, [start_node])]
        visited: set[int] = set()

        while stack:
            u, path = stack.pop()
            if u not in visited:
                visited.add(u)
                explored_nodes.append(u)

                if u in exits_set:
                    found_paths.append(path)
                    break

                for v, _, _ in reversed(ag.neighbors(u)):
                    if v not in visited and v in can_reach:
                        stack.append((v, path + [v]))

    else:
        # 'all' paths mode: Backtracking simple paths with explicit call-stack simulation
        # Each frame: (node, neighbor_index)
        stack: list[int] = [start_node]
        nbr_indices: list[int] = [0]
        on_path: set[int] = {start_node}
        visited_nodes_seen: set[int] = {start_node}
        explored_nodes.append(start_node)

        while stack:
            if time.perf_counter() - start_time > timeout_s:
                warnings.append(f"Search timed out after {timeout_s}s. Route list truncated.")
                break

            if len(found_paths) >= max_paths:
                warnings.append(f"Reached maximum path count limit ({max_paths}). Route list truncated.")
                break

            curr = stack[-1]
            idx = nbr_indices[-1]
            neighbors = [n[0] for n in ag.neighbors(curr)]

            if idx < len(neighbors) and len(stack) <= max_depth:
                nbr_indices[-1] += 1
                nxt = neighbors[idx]

                if nxt not in on_path and nxt in can_reach:
                    if nxt not in visited_nodes_seen:
                        visited_nodes_seen.add(nxt)
                        explored_nodes.append(nxt)

                    if nxt in exits_set:
                        # Found a path to exit
                        found_paths.append(list(stack) + [nxt])
                    else:
                        # Descend deeper
                        stack.append(nxt)
                        nbr_indices.append(0)
                        on_path.add(nxt)
            else:
                # Backtrack
                popped = stack.pop()
                nbr_indices.pop()
                on_path.remove(popped)

    runtime = (time.perf_counter() - start_time) * 1000.0

    if not found_paths:
        warnings.append("No route found: all exits are unreachable or blocked.")
        return RouteResult(
            algorithm="dfs",
            routes=[],
            explored_nodes=explored_nodes,
            stats=RouteStats(
                nodes_visited=len(explored_nodes),
                runtime_ms=round(runtime, 2),
                routes_found=0,
            ),
            warnings=warnings,
        )

    routes = [
        build_route_path(ag, p, p[-1], options.walking_speed_mps)
        for p in found_paths
    ]
    # Rank paths by distance
    routes.sort(key=lambda r: r.distance_px)

    return RouteResult(
        algorithm="dfs",
        routes=routes,
        explored_nodes=explored_nodes,
        stats=RouteStats(
            nodes_visited=len(explored_nodes),
            runtime_ms=round(runtime, 2),
            routes_found=len(routes),
        ),
        warnings=warnings,
    )
