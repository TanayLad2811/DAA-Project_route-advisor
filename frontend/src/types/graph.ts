export type NodeType = 'walkable' | 'junction' | 'dead_end' | 'exit' | 'start' | 'door'

export type DoorType = 'interior' | 'exit'

export interface Door {
  id: number
  x: number
  y: number
  width: number
  type: DoorType
  confidence: number
  nearest_node_id?: number | null
}

export interface Node {
  id: number
  x: number
  y: number
  type: NodeType
  clearance?: number | null
  label?: string | null
}

export interface Edge {
  id: number
  source: number
  target: number
  length_px: number
  polyline?: [number, number][] | null
  blocked: boolean
  min_clearance?: number | null
  weight?: number | null
}

export interface SuggestedExit {
  x: number
  y: number
  confidence: number
  nearest_node_id?: number | null
}

export interface Graph {
  plan_id: string
  strategy: 'grid' | 'skeleton'
  image_width: number
  image_height: number
  nodes: Node[]
  edges: Edge[]
  exits: number[]
  doors?: Door[]
  meters_per_pixel?: number | null
  warnings?: string[]
}

export interface GraphBuildRequest {
  strategy?: 'grid' | 'skeleton'
  wall_threshold?: number
  invert?: boolean
  cell_size?: number | null
  close_kernel?: number
  min_clearance_px?: number
  spur_len?: number
  filter_annotations?: boolean
  detect_doors?: boolean
}

export interface GraphBuildResponse {
  graph: Graph
  suggested_exits: SuggestedExit[]
  detected_doors?: Door[]
}

export interface Hazard {
  id: number
  kind: 'edge' | 'region'
  edge_ids: number[]
  polygon: [number, number][]
  label?: string | null
}

export interface HazardCreateRequest {
  kind: 'edge' | 'region'
  edge_ids?: number[]
  polygon?: [number, number][]
  label?: string | null
}

export interface ScaleCalibrationRequest {
  point_a: [number, number]
  point_b: [number, number]
  real_distance_m: number
}

