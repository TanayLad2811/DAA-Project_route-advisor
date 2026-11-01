export type AlgorithmType = 'bfs' | 'dfs' | 'shortest_path'
export type DfsMode = 'first' | 'all'
export type ShortestVariant = 'dijkstra' | 'astar'

export interface RouteOptions {
  dfs_mode?: DfsMode
  max_paths?: number
  max_depth?: number
  shortest_variant?: ShortestVariant
  alternatives?: number
  avoid_narrow_below_m?: number | null
  walking_speed_mps?: number
}

export interface RouteRequest {
  algorithm: AlgorithmType
  start: [number, number] | number
  exit_ids?: number[] | null
  options?: RouteOptions
}

export interface RoutePath {
  exit_id: number
  node_ids: number[]
  points: [number, number][]
  distance_px: number
  distance_m?: number | null
  est_time_s?: number | null
  hops: number
  turns: number
  min_clearance_m?: number | null
}

export interface RouteStats {
  nodes_visited: number
  runtime_ms: number
  routes_found: number
}

export interface RouteResult {
  algorithm: string
  routes: RoutePath[]
  explored_nodes: number[]
  stats: RouteStats
  warnings: string[]
}

