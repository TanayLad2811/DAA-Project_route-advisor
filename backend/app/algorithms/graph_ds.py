from dataclasses import dataclass, field

from app.schemas.graph import Graph, Node


@dataclass
class AdjacencyGraph:
    nodes: dict[int, Node] = field(default_factory=dict)
    # node_id -> list of (neighbor_id, weight, edge_id)
    adj: dict[int, list[tuple[int, float, int]]] = field(default_factory=dict)
    # edge_id -> length in pixels
    edge_lengths: dict[int, float] = field(default_factory=dict)
    # edge_id -> polyline coordinates
    edge_polylines: dict[int, list[tuple[float, float]]] = field(default_factory=dict)
    # edge_id -> min clearance
    edge_min_clearance: dict[int, float] = field(default_factory=dict)
    # plan scaling
    meters_per_pixel: float | None = None

    @classmethod
    def from_schema(cls, graph: Graph, blocked_edge_ids: set[int] | None = None) -> "AdjacencyGraph":
        blocked = set(blocked_edge_ids or set())
        for e in graph.edges:
            if e.blocked:
                blocked.add(e.id)

        ag = cls(
            nodes={n.id: n for n in graph.nodes},
            adj={n.id: [] for n in graph.nodes},
            meters_per_pixel=graph.meters_per_pixel,
        )

        for edge in graph.edges:
            if edge.id in blocked:
                continue

            u = edge.source
            v = edge.target
            w = edge.weight if edge.weight is not None else edge.length_px

            if u in ag.nodes and v in ag.nodes:
                ag.adj[u].append((v, w, edge.id))
                ag.adj[v].append((u, w, edge.id))

            ag.edge_lengths[edge.id] = edge.length_px

            if edge.polyline:
                ag.edge_polylines[edge.id] = edge.polyline
            if edge.min_clearance is not None:
                ag.edge_min_clearance[edge.id] = edge.min_clearance

        # Sort neighbor lists deterministically by neighbor_id for reproducible traversal
        for u in ag.adj:
            ag.adj[u].sort(key=lambda item: item[0])

        return ag

    def neighbors(self, node_id: int) -> list[tuple[int, float, int]]:
        return self.adj.get(node_id, [])

    def node_coords(self, node_id: int) -> tuple[float, float]:
        node = self.nodes.get(node_id)
        if node:
            return (node.x, node.y)
        return (0.0, 0.0)
