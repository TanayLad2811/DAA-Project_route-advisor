from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    WALKABLE = "walkable"
    JUNCTION = "junction"
    DEAD_END = "dead_end"
    DOOR = "door"
    EXIT = "exit"
    START = "start"


class DoorType(str, Enum):
    INTERIOR = "interior"
    EXIT = "exit"


class Door(BaseModel):
    id: int
    x: float
    y: float
    width: float = 36.0
    type: DoorType = DoorType.INTERIOR
    confidence: float = 0.85
    nearest_node_id: int | None = None


class Node(BaseModel):
    id: int
    x: float  # pixel coords in original/normalized image
    y: float
    type: NodeType = NodeType.WALKABLE
    clearance: float | None = None  # distance to nearest wall in px
    label: str | None = None


class Edge(BaseModel):
    id: int
    source: int
    target: int
    length_px: float
    polyline: list[tuple[float, float]] | None = None  # actual path shape for skeleton edges
    blocked: bool = False
    min_clearance: float | None = None  # narrowest point along edge
    weight: float | None = None  # computed: length_m + penalties


class SuggestedExit(BaseModel):
    x: float
    y: float
    confidence: float
    nearest_node_id: int | None = None


class Graph(BaseModel):
    plan_id: str
    strategy: Literal["grid", "skeleton"]
    image_width: int
    image_height: int
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    exits: list[int] = Field(default_factory=list)  # node ids
    doors: list[Door] = Field(default_factory=list)
    meters_per_pixel: float | None = None
    warnings: list[str] = Field(default_factory=list)


class GraphBuildRequest(BaseModel):
    strategy: Literal["grid", "skeleton"] = "skeleton"
    wall_threshold: int = 127
    invert: bool = False
    cell_size: int | None = None
    close_kernel: int = 3
    min_clearance_px: float = 2.0
    spur_len: int = 15
    filter_annotations: bool = True
    detect_doors: bool = True


class GraphBuildResponse(BaseModel):
    graph: Graph
    suggested_exits: list[SuggestedExit] = Field(default_factory=list)
    detected_doors: list[Door] = Field(default_factory=list)


class Hazard(BaseModel):
    id: int
    kind: Literal["edge", "region"]
    edge_ids: list[int] = Field(default_factory=list)
    polygon: list[tuple[float, float]] = Field(default_factory=list)
    label: str | None = None


class HazardCreateRequest(BaseModel):
    kind: Literal["edge", "region"]
    edge_ids: list[int] = Field(default_factory=list)
    polygon: list[tuple[float, float]] = Field(default_factory=list)
    label: str | None = None


class ScaleCalibrationRequest(BaseModel):
    point_a: tuple[float, float]
    point_b: tuple[float, float]
    real_distance_m: float
