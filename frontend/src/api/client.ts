import { PlanMetadata, PlanUploadResponse } from '../types/plan'
import { Graph, GraphBuildRequest, GraphBuildResponse, Hazard, HazardCreateRequest, ScaleCalibrationRequest } from '../types/graph'
import { RouteRequest, RouteResult } from '../types/route'

const rawBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || ''
const API_HOST = rawBase.startsWith('http') ? rawBase : rawBase ? `https://${rawBase}` : ''
const API_BASE = `${API_HOST}/api/v1`

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`
  const response = await fetch(url, options)

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`
    try {
      const data = await response.json()
      if (data.detail) errorDetail = data.detail
    } catch {
      // Non-JSON response
    }
    throw new ApiError(response.status, errorDetail)
  }

  return response.json() as Promise<T>
}

export const apiClient = {
  // Health
  checkHealth: () => request<{ status: string; app: string; version: string }>('/health'),

  // Plans
  uploadPlan: async (file: File): Promise<PlanUploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    return request<PlanUploadResponse>('/plans', {
      method: 'POST',
      body: formData,
    })
  },

  listSamples: (): Promise<{ id: string; name: string; description: string }[]> => {
    return request<{ id: string; name: string; description: string }[]>('/plans/samples/list')
  },

  loadSample: (sampleId: string): Promise<PlanUploadResponse> => {
    return request<PlanUploadResponse>(`/plans/samples/${sampleId}`, {
      method: 'POST',
    })
  },

  getPlan: (planId: string): Promise<PlanMetadata> => {
    return request<PlanMetadata>(`/plans/${planId}`)
  },

  deletePlan: (planId: string): Promise<{ status: string; plan_id: string }> => {
    return request<{ status: string; plan_id: string }>(`/plans/${planId}`, {
      method: 'DELETE',
    })
  },

  getPlanImageUrl: (planId: string): string => {
    return `${API_BASE}/plans/${planId}/image`
  },

  // Graphs
  buildGraph: (planId: string, req: GraphBuildRequest): Promise<GraphBuildResponse> => {
    return request<GraphBuildResponse>(`/plans/${planId}/graph`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    })
  },

  getGraph: (planId: string): Promise<Graph> => {
    return request<Graph>(`/plans/${planId}/graph`)
  },

  updateGraph: (planId: string, graph: Graph): Promise<Graph> => {
    return request<Graph>(`/plans/${planId}/graph`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(graph),
    })
  },

  updateExits: (planId: string, exitIds: number[]): Promise<Graph> => {
    return request<Graph>(`/plans/${planId}/graph/exits`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ exit_ids: exitIds }),
    })
  },

  calibrateScale: (planId: string, req: ScaleCalibrationRequest): Promise<Graph> => {
    return request<Graph>(`/plans/${planId}/scale`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    })
  },

  // Hazards
  addHazard: (planId: string, req: HazardCreateRequest): Promise<Hazard> => {
    return request<Hazard>(`/plans/${planId}/hazards`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    })
  },

  deleteHazard: (planId: string, hazardId: number): Promise<{ status: string }> => {
    return request<{ status: string }>(`/plans/${planId}/hazards/${hazardId}`, {
      method: 'DELETE',
    })
  },

  toggleEdgesBlock: (planId: string, edgeIds: number[]): Promise<Graph> => {
    return request<Graph>(`/plans/${planId}/hazards/toggle-edges`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ edge_ids: edgeIds }),
    })
  },

  unblockEdges: (planId: string, edgeIds: number[]): Promise<Graph> => {
    return request<Graph>(`/plans/${planId}/hazards/unblock-edges`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ edge_ids: edgeIds }),
    })
  },

  clearAllHazards: (planId: string): Promise<Graph> => {
    return request<Graph>(`/plans/${planId}/hazards/clear-all`, {
      method: 'POST',
    })
  },

  // Routing
  computeRoute: (planId: string, req: RouteRequest): Promise<RouteResult> => {
    return request<RouteResult>(`/plans/${planId}/route`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    })
  },

  // Debug views
  getDebugImageUrl: (planId: string, stage: string): string => {
    return `${API_BASE}/plans/${planId}/debug/${stage}`
  },
}
