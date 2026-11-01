from pathlib import Path

import cv2
import numpy as np


def generate_all_fixtures(output_dir: Path | None = None) -> dict[str, Path]:
    out = output_dir or Path(__file__).parent
    out.mkdir(parents=True, exist_ok=True)
    generated = {}

    # 1. Straight Corridor: 300x100, white floor with black walls top and bottom
    img_corridor = np.ones((100, 300, 3), dtype=np.uint8) * 255
    cv2.rectangle(img_corridor, (0, 0), (300, 20), (0, 0, 0), -1)  # Top wall
    cv2.rectangle(img_corridor, (0, 80), (300, 100), (0, 0, 0), -1)  # Bottom wall
    path_corridor = out / "corridor.png"
    cv2.imwrite(str(path_corridor), img_corridor)
    generated["corridor"] = path_corridor

    # 2. L-Shape Corridor: 200x200
    img_l = np.zeros((200, 200, 3), dtype=np.uint8)  # Black walls everywhere
    # Carve white walkable L-corridor
    cv2.rectangle(img_l, (20, 20), (180, 70), (255, 255, 255), -1)  # Horizontal leg
    cv2.rectangle(img_l, (130, 20), (180, 180), (255, 255, 255), -1)  # Vertical leg
    path_l = out / "l_shape.png"
    cv2.imwrite(str(path_l), img_l)
    generated["l_shape"] = path_l

    # 3. T-Junction Corridor: 200x200
    img_t = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.rectangle(img_t, (20, 20), (180, 60), (255, 255, 255), -1)  # Top bar
    cv2.rectangle(img_t, (80, 60), (120, 180), (255, 255, 255), -1)  # Vertical stem
    path_t = out / "t_junction.png"
    cv2.imwrite(str(path_t), img_t)
    generated["t_junction"] = path_t

    # 4. Room with Central Pillar: 200x200
    img_pillar = np.ones((200, 200, 3), dtype=np.uint8) * 255
    # Outer walls with margin so border is exterior
    cv2.rectangle(img_pillar, (20, 20), (180, 180), (0, 0, 0), 8)
    # Doorway at left
    cv2.rectangle(img_pillar, (20, 80), (28, 120), (255, 255, 255), -1)
    # Center pillar
    cv2.rectangle(img_pillar, (80, 80), (120, 120), (0, 0, 0), -1)
    path_pillar = out / "room_with_pillar.png"
    cv2.imwrite(str(path_pillar), img_pillar)
    generated["room_with_pillar"] = path_pillar

    # 5. Office with 4 Rooms & Corridor: 300x200
    img_office = np.ones((200, 300, 3), dtype=np.uint8) * 255
    # Outer boundary wall
    cv2.rectangle(img_office, (10, 10), (290, 190), (0, 0, 0), 8)
    # Central horizontal hallway walls
    cv2.rectangle(img_office, (10, 80), (290, 88), (0, 0, 0), -1)
    cv2.rectangle(img_office, (10, 112), (290, 120), (0, 0, 0), -1)
    # Room dividers (top rooms)
    cv2.rectangle(img_office, (150, 10), (158, 80), (0, 0, 0), -1)
    # Room dividers (bottom rooms)
    cv2.rectangle(img_office, (150, 120), (158, 190), (0, 0, 0), -1)
    # Door openings for Room 1, 2, 3, 4 into hallway
    cv2.rectangle(img_office, (60, 80), (90, 88), (255, 255, 255), -1)
    cv2.rectangle(img_office, (210, 80), (240, 88), (255, 255, 255), -1)
    cv2.rectangle(img_office, (60, 112), (90, 120), (255, 255, 255), -1)
    cv2.rectangle(img_office, (210, 112), (240, 120), (255, 255, 255), -1)
    # Building main exit on right border
    cv2.rectangle(img_office, (285, 90), (295, 110), (255, 255, 255), -1)

    path_office = out / "office_rooms.png"
    cv2.imwrite(str(path_office), img_office)
    generated["office_rooms"] = path_office

    return generated


if __name__ == "__main__":
    generated = generate_all_fixtures()
    for name, p in generated.items():
        print(f"Generated fixture '{name}': {p}")
