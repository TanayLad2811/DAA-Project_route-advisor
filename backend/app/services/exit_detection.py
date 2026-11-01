import cv2

from app.schemas.graph import Graph, NodeType, SuggestedExit
from app.services.image_processing import ProcessedPlanImage


def detect_suggested_exits(
    graph: Graph,
    processed: ProcessedPlanImage,
    search_radius_px: int = 15,
) -> list[SuggestedExit]:
    """Detects candidate exits based on proximity to the exterior boundary mask and perimeter openings."""
    h, w = processed.wall_mask.shape
    candidates: list[SuggestedExit] = []

    # Dilate exterior mask slightly to detect points near building envelope
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (search_radius_px, search_radius_px))
    dilated_exterior = cv2.dilate(processed.exterior_mask, kernel)

    seen_coords: set[tuple[int, int]] = set()

    for node in graph.nodes:
        nx, ny = round(node.x), round(node.y)
        if not (0 <= nx < w and 0 <= ny < h):
            continue

        # Check if node is close to exterior space
        if dilated_exterior[ny, nx] > 0:
            # High confidence if node is DEAD_END endpoint or close to image boundary
            is_endpoint = node.type == NodeType.DEAD_END
            is_boundary = nx < 30 or nx > w - 30 or ny < 30 or ny > h - 30

            confidence = 0.90 if (is_endpoint and is_boundary) else (0.75 if is_endpoint else 0.60)

            # Avoid placing suggestions right next to each other
            grid_bucket = (nx // 25, ny // 25)
            if grid_bucket not in seen_coords:
                seen_coords.add(grid_bucket)
                candidates.append(
                    SuggestedExit(
                        x=node.x,
                        y=node.y,
                        confidence=confidence,
                        nearest_node_id=node.id,
                    )
                )

    # Sort by confidence
    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return candidates[:8]
