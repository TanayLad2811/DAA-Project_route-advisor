import math

import cv2
import numpy as np
from scipy.ndimage import convolve
from skimage.morphology import skeletonize

from app.schemas.graph import Door, Edge, Graph, Node, NodeType
from app.services.image_processing import ProcessedPlanImage


def build_skeleton_graph(
    processed: ProcessedPlanImage,
    plan_id: str,
    spur_len: int = 15,
    doors: list[Door] | None = None,
) -> Graph:
    """Builds a Topological Skeleton Centerline Graph (Strategy B) with door preserving pruning."""
    h, w = processed.wall_mask.shape
    warnings: list[str] = []

    # 1. Skeletonize the free space mask
    binary_free = processed.free_mask > 0
    skel = skeletonize(binary_free)
    skel_uint8 = skel.astype(np.uint8)

    if np.count_nonzero(skel_uint8) == 0:
        return Graph(
            plan_id=plan_id,
            strategy="skeleton",
            image_width=w,
            image_height=h,
            nodes=[],
            edges=[],
            exits=[],
            warnings=["No walkable skeleton extracted. Try adjusting the wall threshold."],
        )

    # 2. Count 8-neighbors
    kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], dtype=np.uint8)
    neighbor_count = convolve(skel_uint8, kernel, mode="constant", cval=0) * skel_uint8

    junction_mask = (neighbor_count >= 3).astype(np.uint8)
    endpoint_mask = (neighbor_count == 1).astype(np.uint8)

    # 3. Cluster adjacent junction pixels into single nodes
    num_junc, junc_labels = cv2.connectedComponents(junction_mask, connectivity=8)

    nodes: list[Node] = []
    pixel_to_node: dict[tuple[int, int], int] = {}
    node_id_counter = 0

    # Create Junction Nodes
    for j_id in range(1, num_junc):
        pts = np.argwhere(junc_labels == j_id)
        if len(pts) == 0:
            continue
        mean_y = float(np.mean(pts[:, 0]))
        mean_x = float(np.mean(pts[:, 1]))
        clearance = float(processed.distance_transform[int(mean_y), int(mean_x)])

        node = Node(
            id=node_id_counter,
            x=round(mean_x, 1),
            y=round(mean_y, 1),
            type=NodeType.JUNCTION,
            clearance=round(clearance, 2),
        )
        nodes.append(node)

        for py, px in pts:
            pixel_to_node[(int(py), int(px))] = node_id_counter

        node_id_counter += 1

    # Create Endpoint Nodes
    end_pts = np.argwhere(endpoint_mask > 0)
    for py, px in end_pts:
        clearance = float(processed.distance_transform[py, px])
        node = Node(
            id=node_id_counter,
            x=float(px),
            y=float(py),
            type=NodeType.DEAD_END,
            clearance=round(clearance, 2),
        )
        nodes.append(node)
        pixel_to_node[(int(py), int(px))] = node_id_counter
        node_id_counter += 1

    # 4. Trace corridor segments (edges) along path pixels (neighbor_count == 2)
    visited_pixels: set[tuple[int, int]] = set()
    raw_edges: list[dict] = []

    def get_skel_neighbors(y: int, x: int) -> list[tuple[int, int]]:
        nbrs = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and skel_uint8[ny, nx] > 0:
                    nbrs.append((ny, nx))
        return nbrs

    for (start_y, start_x), start_node_id in list(pixel_to_node.items()):
        start_nbrs = get_skel_neighbors(start_y, start_x)

        for n_y, n_x in start_nbrs:
            if (n_y, n_x) in pixel_to_node and pixel_to_node[(n_y, n_x)] == start_node_id:
                continue

            path_key = tuple(sorted([(start_y, start_x), (n_y, n_x)]))
            if path_key in visited_pixels:
                continue
            visited_pixels.add(path_key)

            polyline = [(float(start_x), float(start_y)), (float(n_x), float(n_y))]
            curr_y, curr_x = n_y, n_x
            prev_y, prev_x = start_y, start_x
            target_node_id = None

            while True:
                if (curr_y, curr_x) in pixel_to_node and (curr_y, curr_x) != (start_y, start_x):
                    target_node_id = pixel_to_node[(curr_y, curr_x)]
                    break

                nbrs = [
                    (ny, nx)
                    for (ny, nx) in get_skel_neighbors(curr_y, curr_x)
                    if (ny, nx) != (prev_y, prev_x)
                ]

                if not nbrs:
                    break

                next_y, next_x = nbrs[0]
                visited_pixels.add(tuple(sorted([(curr_y, curr_x), (next_y, next_x)])))
                polyline.append((float(next_x), float(next_y)))
                prev_y, prev_x = curr_y, curr_x
                curr_y, curr_x = next_y, next_x

            if target_node_id is not None and start_node_id != target_node_id:
                length = sum(
                    math.hypot(polyline[k + 1][0] - polyline[k][0], polyline[k + 1][1] - polyline[k][1])
                    for k in range(len(polyline) - 1)
                )
                min_clear = min(
                    float(processed.distance_transform[int(pt[1]), int(pt[0])])
                    for pt in polyline
                    if 0 <= int(pt[1]) < h and 0 <= int(pt[0]) < w
                )

                raw_edges.append(
                    {
                        "source": min(start_node_id, target_node_id),
                        "target": max(start_node_id, target_node_id),
                        "length_px": round(length, 2),
                        "polyline": polyline,
                        "min_clearance": round(min_clear, 2),
                    }
                )

    # Remove duplicate edges
    unique_edges_map: dict[tuple[int, int], dict] = {}
    for e in raw_edges:
        pair = (e["source"], e["target"])
        if pair not in unique_edges_map or e["length_px"] < unique_edges_map[pair]["length_px"]:
            unique_edges_map[pair] = e

    edges_list = list(unique_edges_map.values())

    # Door positions to protect from spur pruning
    protected_node_ids = set()
    if doors:
        for d in doors:
            closest_n = min(nodes, key=lambda n: math.hypot(n.x - d.x, n.y - d.y), default=None)
            if closest_n and math.hypot(closest_n.x - d.x, closest_n.y - d.y) < 50:
                protected_node_ids.add(closest_n.id)

    # 5. Iterative Spur Pruning with protection for door nodes
    if spur_len > 0:
        changed = True
        while changed:
            changed = False
            degree: dict[int, int] = {n.id: 0 for n in nodes}
            for e in edges_list:
                degree[e["source"]] += 1
                degree[e["target"]] += 1

            new_edges = []
            for e in edges_list:
                u, v = e["source"], e["target"]
                # A dead-end spur has degree 1 on one end and length < spur_len, and neither end is protected
                is_spur_u = degree[u] == 1 and u not in protected_node_ids
                is_spur_v = degree[v] == 1 and v not in protected_node_ids
                is_spur = (is_spur_u or is_spur_v) and e["length_px"] < spur_len

                if is_spur and len(edges_list) > 1:
                    changed = True
                else:
                    new_edges.append(e)

            edges_list = new_edges

    # 6. Simplify polylines with Douglas-Peucker
    edges: list[Edge] = []
    for idx, e in enumerate(edges_list, start=1):
        poly = e["polyline"]
        if len(poly) > 4:
            pts_arr = np.array([[pt[0], pt[1]] for pt in poly], dtype=np.float32).reshape(-1, 1, 2)
            simplified = cv2.approxPolyDP(pts_arr, epsilon=1.5, closed=False)
            simplified_pts = [(float(pt[0][0]), float(pt[0][1])) for pt in simplified]
            simplified_pts[0] = poly[0]
            simplified_pts[-1] = poly[-1]
            poly = simplified_pts

        edges.append(
            Edge(
                id=idx,
                source=e["source"],
                target=e["target"],
                length_px=e["length_px"],
                polyline=poly,
                min_clearance=e["min_clearance"],
                weight=e["length_px"],
            )
        )

    connected_node_ids = set()
    for e in edges:
        connected_node_ids.add(e.source)
        connected_node_ids.add(e.target)

    active_nodes = [n for n in nodes if n.id in connected_node_ids]

    return Graph(
        plan_id=plan_id,
        strategy="skeleton",
        image_width=w,
        image_height=h,
        nodes=active_nodes,
        edges=edges,
        exits=[],
        warnings=warnings,
    )
