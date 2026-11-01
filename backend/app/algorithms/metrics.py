import math

from app.algorithms.graph_ds import AdjacencyGraph
from app.schemas.route import RoutePath


def calculate_turn_count(points: list[tuple[float, float]], threshold_deg: float = 30.0) -> int:
    """Counts turns where heading changes by more than threshold_deg."""
    if len(points) < 3:
        return 0

    turns = 0
    rad_threshold = math.radians(threshold_deg)

    for i in range(len(points) - 2):
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[i + 2]

        v1 = (p2[0] - p1[0], p2[1] - p1[1])
        v2 = (p3[0] - p2[0], p3[1] - p2[1])

        len1 = math.hypot(v1[0], v1[1])
        len2 = math.hypot(v2[0], v2[1])

        if len1 < 1e-4 or len2 < 1e-4:
            continue

        # Dot product and cross product for angle
        dot = (v1[0] * v2[0] + v1[1] * v2[1]) / (len1 * len2)
        dot = max(-1.0, min(1.0, dot))
        angle = math.acos(dot)

        if angle > rad_threshold:
            turns += 1

    return turns


def build_route_path(
    ag: AdjacencyGraph,
    node_ids: list[int],
    exit_id: int,
    walking_speed_mps: float = 1.2,
) -> RoutePath:
    """Builds a RoutePath model with geometric metrics, turns, and drawable polyline."""
    if not node_ids:
        return RoutePath(
            exit_id=exit_id,
            node_ids=[],
            points=[],
            distance_px=0.0,
            hops=0,
            turns=0,
        )

    if len(node_ids) == 1:
        pt = ag.node_coords(node_ids[0])
        return RoutePath(
            exit_id=exit_id,
            node_ids=node_ids,
            points=[pt],
            distance_px=0.0,
            distance_m=0.0 if ag.meters_per_pixel else None,
            est_time_s=0.0 if ag.meters_per_pixel else None,
            hops=0,
            turns=0,
            min_clearance_m=None,
        )

    points: list[tuple[float, float]] = []
    total_dist_px = 0.0
    min_clearance: float | None = None

    for i in range(len(node_ids) - 1):
        u = node_ids[i]
        v = node_ids[i + 1]

        u_node = ag.nodes.get(u)
        v_node = ag.nodes.get(v)

        if u_node and u_node.clearance is not None:
            min_clearance = min(min_clearance or float("inf"), u_node.clearance)
        if v_node and v_node.clearance is not None:
            min_clearance = min(min_clearance or float("inf"), v_node.clearance)

        # Look up edge to check for polyline
        edge_id = None
        for nbr, _, eid in ag.neighbors(u):
            if nbr == v:
                edge_id = eid
                break

        polyline = ag.edge_polylines.get(edge_id) if edge_id is not None else None
        if edge_id in ag.edge_min_clearance:
            min_clearance = min(min_clearance or float("inf"), ag.edge_min_clearance[edge_id])

        if edge_id is not None and edge_id in ag.edge_lengths:
            total_dist_px += ag.edge_lengths[edge_id]
        elif u_node and v_node:
            total_dist_px += math.hypot(v_node.x - u_node.x, v_node.y - u_node.y)

        if polyline and len(polyline) >= 2:
            # Check orientation
            start_dist = math.hypot(polyline[0][0] - u_node.x, polyline[0][1] - u_node.y) if u_node else 0
            end_dist = math.hypot(polyline[-1][0] - u_node.x, polyline[-1][1] - u_node.y) if u_node else 0
            oriented_pts = polyline if start_dist <= end_dist else list(reversed(polyline))

            if not points:
                points.extend(oriented_pts)
            else:
                points.extend(oriented_pts[1:])
        else:
            if not points and u_node:
                points.append((u_node.x, u_node.y))
            if v_node:
                points.append((v_node.x, v_node.y))

    hops = len(node_ids) - 1
    turns = calculate_turn_count(points)

    dist_m = total_dist_px * ag.meters_per_pixel if ag.meters_per_pixel is not None else None
    est_time = (dist_m / walking_speed_mps) if dist_m is not None and walking_speed_mps > 0 else None
    min_clear_m = (
        min_clearance * ag.meters_per_pixel
        if min_clearance is not None and ag.meters_per_pixel is not None
        else None
    )

    return RoutePath(
        exit_id=exit_id,
        node_ids=node_ids,
        points=points,
        distance_px=round(total_dist_px, 2),
        distance_m=round(dist_m, 2) if dist_m is not None else None,
        est_time_s=round(est_time, 1) if est_time is not None else None,
        hops=hops,
        turns=turns,
        min_clearance_m=round(min_clear_m, 2) if min_clear_m is not None else None,
    )
