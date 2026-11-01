import math

import numpy as np
from scipy.spatial import cKDTree

from app.schemas.graph import Edge, Node


def point_to_segment_distance(
    px: float, py: float, x1: float, y1: float, x2: float, y2: float
) -> tuple[float, float, float]:
    """Calculates shortest distance from point (px, py) to line segment (x1, y1)-(x2, y2).

    Returns (distance, closest_x, closest_y).
    """
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1), x1, y1

    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    dist = math.hypot(px - closest_x, py - closest_y)
    return dist, closest_x, closest_y


class PointSnapper:
    def __init__(self, nodes: list[Node], edges: list[Edge] | None = None):
        self.nodes = nodes
        self.node_map = {n.id: n for n in nodes}
        self.edges = edges or []
        if nodes:
            coords = np.array([[n.x, n.y] for n in nodes], dtype=np.float32)
            self.kdtree = cKDTree(coords)
        else:
            self.kdtree = None

    def snap_to_nearest_node(
        self, point: tuple[float, float], max_dist: float | None = None
    ) -> tuple[int | None, float]:
        """Snaps a point (x, y) to the nearest graph node, checking both nodes and corridor edges."""
        if not self.kdtree or not self.nodes:
            return None, float("inf")

        # 1. Direct node query
        node_dist, idx = self.kdtree.query([point[0], point[1]])
        best_node_id = self.nodes[idx].id
        best_dist = float(node_dist)

        # 2. Check edges: if point is closer to a corridor edge, snap to the closer endpoint of that edge
        px, py = point[0], point[1]
        for edge in self.edges:
            pts = edge.polyline if edge.polyline and len(edge.polyline) >= 2 else None
            if not pts:
                u = self.node_map.get(edge.source)
                v = self.node_map.get(edge.target)
                if u and v:
                    pts = [(u.x, u.y), (v.x, v.y)]

            if pts:
                for k in range(len(pts) - 1):
                    seg_dist, cx, cy = point_to_segment_distance(
                        px, py, pts[k][0], pts[k][1], pts[k + 1][0], pts[k + 1][1]
                    )
                    if seg_dist < best_dist:
                        # Closer to this edge segment: pick closer endpoint of this edge
                        u = self.node_map.get(edge.source)
                        v = self.node_map.get(edge.target)
                        if u and v:
                            d_u = math.hypot(cx - u.x, cy - u.y)
                            d_v = math.hypot(cx - v.x, cy - v.y)
                            chosen_node = u.id if d_u <= d_v else v.id
                            best_node_id = chosen_node
                            best_dist = seg_dist

        if max_dist is not None and best_dist > max_dist:
            return None, float(best_dist)

        return best_node_id, float(best_dist)


def euclidean_distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])
