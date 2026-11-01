from typing import Literal

from pydantic import BaseModel, Field


class RouteOptions(BaseModel):
    dfs_mode: Literal["first", "all"] = "first"
    max_paths: int = 50  # cap for DFS "all"
    max_depth: int = 500
    shortest_variant: Literal["dijkstra", "astar"] = "dijkstra"
    alternatives: int = 3  # k alternative routes
    avoid_narrow_below_m: float | None = None
    walking_speed_mps: float = 1.2


class RouteRequest(BaseModel):
    algorithm: Literal["bfs", "dfs", "shortest_path"]
    start: tuple[float, float] | int  # pixel coords (x, y) OR node id
    exit_ids: list[int] | None = None  # None = all available exits
    options: RouteOptions = Field(default_factory=RouteOptions)


class RoutePath(BaseModel):
    exit_id: int
    node_ids: list[int]
    points: list[tuple[float, float]]  # drawable polyline
    distance_px: float
    distance_m: float | None = None
    est_time_s: float | None = None
    hops: int
    turns: int
    min_clearance_m: float | None = None


class RouteStats(BaseModel):
    nodes_visited: int
    runtime_ms: float
    routes_found: int = 0


class RouteResult(BaseModel):
    algorithm: str
    routes: list[RoutePath] = Field(default_factory=list)  # ranked
    explored_nodes: list[int] = Field(default_factory=list)  # for search wavefront animation
    stats: RouteStats
    warnings: list[str] = Field(default_factory=list)
