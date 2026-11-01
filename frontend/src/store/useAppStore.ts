import { create } from 'zustand'
import { Graph, Hazard, SuggestedExit } from '../types/graph'
import { AlgorithmType, RouteOptions, RouteResult } from '../types/route'
import { PlanUploadResponse } from '../types/plan'

export type ActiveTool =
  | 'select'
  | 'pan'
  | 'set_start'
  | 'mark_exit'
  | 'add_node'
  | 'add_edge'
  | 'erase'
  | 'block_corridor'
  | 'unblock_corridor'
  | 'hazard_zone'
  | 'calibrate'

export interface LayerVisibility {
  image: boolean
  graph: boolean
  doors: boolean
  routes: boolean
  hazards: boolean
  exploredNodes: boolean
  clearanceHeatmap: boolean
}

export interface AppState {
  // Plan state
  planId: string | null
  imageUrl: string | null
  imageWidth: number
  imageHeight: number
  scaleFactor: number

  // Graph state
  graph: Graph | null
  suggestedExits: SuggestedExit[]
  startPoint: [number, number] | number | null
  exits: number[]
  hazards: Hazard[]

  // Algorithm & options
  algorithm: AlgorithmType
  options: RouteOptions
  routeResult: RouteResult | null
  selectedRouteIndex: number

  // UI state
  activeTool: ActiveTool
  layers: LayerVisibility
  loading: boolean
  loadingMessage: string | null
  error: string | null

  // Actions
  setPlan: (upload: PlanUploadResponse) => void
  clearPlan: () => void
  setGraph: (graph: Graph, suggestedExits?: SuggestedExit[]) => void
  setStartPoint: (start: [number, number] | number | null) => void
  setExits: (exits: number[]) => void
  toggleExit: (nodeId: number) => void
  setHazards: (hazards: Hazard[]) => void
  addHazard: (hazard: Hazard) => void
  removeHazard: (hazardId: number) => void
  setAlgorithm: (algo: AlgorithmType) => void
  setOptions: (options: Partial<RouteOptions>) => void
  setRouteResult: (result: RouteResult | null) => void
  setSelectedRouteIndex: (idx: number) => void
  setActiveTool: (tool: ActiveTool) => void
  toggleLayer: (layer: keyof LayerVisibility) => void
  setLoading: (loading: boolean, message?: string | null) => void
  setError: (error: string | null) => void
}

export const useAppStore = create<AppState>((set) => ({
  planId: null,
  imageUrl: null,
  imageWidth: 0,
  imageHeight: 0,
  scaleFactor: 1.0,

  graph: null,
  suggestedExits: [],
  startPoint: null,
  exits: [],
  hazards: [],

  algorithm: 'shortest_path',
  options: {
    dfs_mode: 'first',
    max_paths: 50,
    max_depth: 500,
    shortest_variant: 'dijkstra',
    alternatives: 3,
    walking_speed_mps: 1.2,
  },
  routeResult: null,
  selectedRouteIndex: 0,

  activeTool: 'select',
  layers: {
    image: true,
    graph: true,
    doors: true,
    routes: true,
    hazards: true,
    exploredNodes: true,
    clearanceHeatmap: false,
  },
  loading: false,
  loadingMessage: null,
  error: null,

  setPlan: (upload) =>
    set({
      planId: upload.plan_id,
      imageUrl: upload.image_url,
      imageWidth: upload.width,
      imageHeight: upload.height,
      scaleFactor: upload.scale_factor,
      graph: null,
      suggestedExits: [],
      startPoint: null,
      exits: [],
      hazards: [],
      routeResult: null,
      error: null,
    }),

  clearPlan: () =>
    set({
      planId: null,
      imageUrl: null,
      imageWidth: 0,
      imageHeight: 0,
      scaleFactor: 1.0,
      graph: null,
      suggestedExits: [],
      startPoint: null,
      exits: [],
      hazards: [],
      routeResult: null,
      error: null,
    }),

  setGraph: (graph, suggestedExits = []) =>
    set({
      graph,
      suggestedExits,
      exits: graph.exits || [],
      error: null,
    }),

  setStartPoint: (start) => set({ startPoint: start }),

  setExits: (exits) => set({ exits }),

  toggleExit: (nodeId) =>
    set((state) => {
      const exits = state.exits.includes(nodeId)
        ? state.exits.filter((id) => id !== nodeId)
        : [...state.exits, nodeId]
      return { exits }
    }),

  setHazards: (hazards) => set({ hazards }),

  addHazard: (hazard) =>
    set((state) => ({ hazards: [...state.hazards, hazard] })),

  removeHazard: (hazardId) =>
    set((state) => ({
      hazards: state.hazards.filter((h) => h.id !== hazardId),
    })),

  setAlgorithm: (algo) => set({ algorithm: algo }),

  setOptions: (newOpts) =>
    set((state) => ({ options: { ...state.options, ...newOpts } })),

  setRouteResult: (result) =>
    set({ routeResult: result, selectedRouteIndex: 0 }),

  setSelectedRouteIndex: (idx) => set({ selectedRouteIndex: idx }),

  setActiveTool: (tool) => set({ activeTool: tool }),

  toggleLayer: (layer) =>
    set((state) => ({
      layers: { ...state.layers, [layer]: !state.layers[layer] },
    })),

  setLoading: (loading, message = null) =>
    set({ loading, loadingMessage: message }),

  setError: (error) => set({ error }),
}))

