import cv2
import numpy as np

from app.schemas.graph import Door, DoorType


def detect_building_doors_and_exits(
    rgb_image: np.ndarray,
    min_door_width_px: int = 15,
    max_door_width_px: int = 70,
) -> tuple[list[Door], np.ndarray, np.ndarray]:
    """Detects interior doors and exterior building exits using wall openings and door-swing arc analysis.

    Returns:
        (doors, structural_walls_mask, building_envelope_mask)
    """
    h, w, _ = rgb_image.shape
    gray = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)

    # 1. Filter blue dimension lines and annotations common in architectural CAD plans
    r = rgb_image[:, :, 0].astype(int)
    b = rgb_image[:, :, 2].astype(int)
    blue_annotations = (b - r > 20) & (b > 110)

    clean_gray = gray.copy()
    clean_gray[blue_annotations] = 255

    # 2. Extract raw walls
    _, raw_binary = cv2.threshold(clean_gray, 215, 255, cv2.THRESH_BINARY_INV)

    # 3. Structural walls vs thin door swing arcs / annotations
    # Morphological opening removes 1-2 px thin lines (door arcs, text), preserving structural walls
    k3 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    thick_walls = cv2.morphologyEx(raw_binary, cv2.MORPH_OPEN, k3)

    # Remove small noise specks
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(thick_walls)
    structural_walls = np.zeros_like(thick_walls)
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] >= 30:
            structural_walls[labels == i] = 255

    # 4. Compute building envelope perimeter bounds
    ys, xs = np.where(structural_walls > 0)
    if len(xs) > 0 and len(ys) > 0:
        min_x, max_x = int(np.min(xs)), int(np.max(xs))
        min_y, max_y = int(np.min(ys)), int(np.max(ys))
    else:
        min_x, max_x = 0, w
        min_y, max_y = 0, h

    envelope_mask = np.zeros((h, w), dtype=np.uint8)
    envelope_mask[min_y:max_y, min_x:max_x] = 255

    # 5. Extract thin lines (door swing arcs and doorway leaves)
    thin_lines = cv2.bitwise_and(raw_binary, cv2.bitwise_not(thick_walls))
    num_cc, _, cc_stats, centroids = cv2.connectedComponentsWithStats(thin_lines)

    doors: list[Door] = []
    seen_positions: list[tuple[float, float]] = []
    door_id = 1

    for i in range(1, num_cc):
        cw = int(cc_stats[i, cv2.CC_STAT_WIDTH])
        ch = int(cc_stats[i, cv2.CC_STAT_HEIGHT])
        area = int(cc_stats[i, cv2.CC_STAT_AREA])
        cx = float(centroids[i][0])
        cy = float(centroids[i][1])

        max_dim = max(cw, ch)
        min_dim = min(cw, ch)

        # Realistic architectural door swing dimensions
        if min_door_width_px <= max_dim <= max_door_width_px and min_dim >= 8 and 20 <= area <= 450:
            # Avoid duplicate doors placed close to each other
            if any(np.hypot(cx - px, cy - py) < 22 for px, py in seen_positions):
                continue

            # Classify exterior building exit vs interior door
            is_exit = (
                cy <= min_y + 15
                or cy >= max_y - 15
                or cx <= min_x + 15
                or cx >= max_x - 15
            )

            door = Door(
                id=door_id,
                x=round(cx, 1),
                y=round(cy, 1),
                width=round(float(max_dim), 1),
                type=DoorType.EXIT if is_exit else DoorType.INTERIOR,
                confidence=0.92 if is_exit else 0.85,
            )
            doors.append(door)
            seen_positions.append((cx, cy))
            door_id += 1

    return doors, structural_walls, envelope_mask
