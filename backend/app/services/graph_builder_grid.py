import math

import numpy as np
from scipy.ndimage import label

from app.schemas.graph import Edge, Graph, Node, NodeType
from app.services.image_processing import ProcessedPlanImage


def bresenham_line_free(
    wall_mask: np.ndarray, x0: int, y0: int, x1: int, y1: int
) -> bool:
    """Checks whether the straight line segment between (x0, y0) and (x1, y1) touches any wall pixel."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    curr_x, curr_y = x0, y0
    h, w = wall_mask.shape

    while True:
        if 0 <= curr_x < w and 0 <= curr_y < h and wall_mask[curr_y, curr_x] > 0:
            return False
        if curr_x == x1 and curr_y == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            curr_x += sx
        if e2 < dx:
            err += dx
            curr_y += sy

    return True


def build_grid_graph(
    processed: ProcessedPlanImage,
    plan_id: str,
    cell_size: int | None = None,
    min_clearance_px: float = 3.0,
    max_nodes: int = 50_000,
) -> Graph:
    """Builds a Grid Occupancy Graph (Strategy A) with 8-neighbor connectivity and corner-cutting prevention."""
    h, w = processed.wall_mask.shape
    warnings: list[str] = []

    # Automatic cell size heuristic
    if cell_size is None or cell_size < 2:
        c_size = max(4, min(20, max(h, w) // 150))
    else:
        c_size = cell_size

    # Check node cap estimate and auto-increase cell size if necessary
    est_nodes = (w // c_size) * (h // c_size)
    if est_nodes > max_nodes:
        c_size = max(c_size, math.ceil(math.sqrt((w * h) / float(max_nodes))))
        warnings.append(
            f"Grid cell size increased to {c_size}px to keep node count below {max_nodes:,} limit."
        )

    grid_cols = w // c_size
    grid_rows = h // c_size

    # Identify walkable grid cells
    cell_node_id = np.full((grid_rows, grid_cols), -1, dtype=np.int32)
    nodes: list[Node] = []
    node_id_counter = 0

    half_c = c_size // 2

    for r in range(grid_rows):
        cy = r * c_size + half_c
        if cy >= h:
            continue
        y_min = max(0, r * c_size)
        y_max = min(h, (r + 1) * c_size)

        for c in range(grid_cols):
            cx = c * c_size + half_c
            if cx >= w:
                continue
            x_min = max(0, c * c_size)
            x_max = min(w, (c + 1) * c_size)

            # Cell center must be free
            if processed.free_mask[cy, cx] == 0:
                continue

            # Fraction of wall pixels in cell bounding box must be < 10%
            cell_box = processed.wall_mask[y_min:y_max, x_min:x_max]
            wall_ratio = np.count_nonzero(cell_box) / float(cell_box.size)
            if wall_ratio >= 0.10:
                continue

            clearance = float(processed.distance_transform[cy, cx])
            if clearance < min_clearance_px:
                continue

            node = Node(
                id=node_id_counter,
                x=float(cx),
                y=float(cy),
                type=NodeType.WALKABLE,
                clearance=round(clearance, 2),
            )
            nodes.append(node)
            cell_node_id[r, c] = node_id_counter
            node_id_counter += 1

    # Connect 8-neighbors with corner-cutting prevention and line-of-sight checks
    edges: list[Edge] = []
    edge_id_counter = 1

    # Relative neighbor offsets: (dr, dc, is_diagonal, orthog1, orthog2)
    moves = [
        # 4 Orthogonal moves
        (0, 1, False, None, None),
        (1, 0, False, None, None),
        # 2 Diagonal moves (to avoid double-adding undirected edges, only positive direction pairs)
        (1, 1, True, (1, 0), (0, 1)),
        (1, -1, True, (1, 0), (0, -1)),
    ]

    diag_dist = c_size * math.sqrt(2.0)
    ortho_dist = float(c_size)

    for r in range(grid_rows):
        for c in range(grid_cols):
            u_id = cell_node_id[r, c]
            if u_id == -1:
                continue

            u_node = nodes[u_id]
            u_x, u_y = int(u_node.x), int(u_node.y)

            for dr, dc, is_diag, o1, o2 in moves:
                nr, nc = r + dr, c + dc
                if not (0 <= nr < grid_rows and 0 <= nc < grid_cols):
                    continue

                v_id = cell_node_id[nr, nc]
                if v_id == -1:
                    continue

                # Diagonal move: Corner-Cutting Prevention
                # Both adjacent orthogonal cells must also be walkable!
                if is_diag and o1 and o2:
                    adj1_r, adj1_c = r + o1[0], c + o1[1]
                    adj2_r, adj2_c = r + o2[0], c + o2[1]
                    if not (0 <= adj1_r < grid_rows and 0 <= adj1_c < grid_cols):
                        continue
                    if not (0 <= adj2_r < grid_rows and 0 <= adj2_c < grid_cols):
                        continue
                    if cell_node_id[adj1_r, adj1_c] == -1 or cell_node_id[adj2_r, adj2_c] == -1:
                        continue

                # Line-of-sight check against wall mask
                v_node = nodes[v_id]
                v_x, v_y = int(v_node.x), int(v_node.y)

                if not bresenham_line_free(processed.wall_mask, u_x, u_y, v_x, v_y):
                    continue

                length = diag_dist if is_diag else ortho_dist
                min_clear = min(u_node.clearance or 0.0, v_node.clearance or 0.0)

                edge = Edge(
                    id=edge_id_counter,
                    source=u_id,
                    target=v_id,
                    length_px=round(length, 2),
                    polyline=[(u_node.x, u_node.y), (v_node.x, v_node.y)],
                    min_clearance=round(min_clear, 2),
                    weight=round(length, 2),
                )
                edges.append(edge)
                edge_id_counter += 1

    # Keep only largest connected component(s)
    if nodes:
        binary_grid = (cell_node_id >= 0).astype(np.int32)
        labeled_grid, num_comp = label(binary_grid)
        if num_comp > 1:
            comp_sizes = [np.count_nonzero(labeled_grid == i) for i in range(1, num_comp + 1)]
            largest_comp_idx = int(np.argmax(comp_sizes)) + 1
            kept_nodes_mask = labeled_grid == largest_comp_idx

            # Filter nodes and re-index
            filtered_nodes = []
            id_mapping = {}
            new_id = 0
            for node in nodes:
                gr = int(node.y) // c_size
                gc = int(node.x) // c_size
                if 0 <= gr < grid_rows and 0 <= gc < grid_cols and kept_nodes_mask[gr, gc]:
                    old_id = node.id
                    node.id = new_id
                    id_mapping[old_id] = new_id
                    filtered_nodes.append(node)
                    new_id += 1

            filtered_edges = []
            for edge in edges:
                if edge.source in id_mapping and edge.target in id_mapping:
                    edge.source = id_mapping[edge.source]
                    edge.target = id_mapping[edge.target]
                    filtered_edges.append(edge)

            nodes = filtered_nodes
            edges = filtered_edges
            warnings.append(f"Dropped {num_comp - 1} isolated grid components; retained largest component.")

    return Graph(
        plan_id=plan_id,
        strategy="grid",
        image_width=w,
        image_height=h,
        nodes=nodes,
        edges=edges,
        exits=[],
        warnings=warnings,
    )
