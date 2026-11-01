import React, { useState } from 'react'
import { Compass } from 'lucide-react'
import { UploadPanel } from './components/UploadPanel'
import { ProcessingOptions } from './components/ProcessingOptions'
import { AlgorithmSelector } from './components/AlgorithmSelector'
import { RouteResultsPanel } from './components/RouteResultsPanel'
import { LegendAndDisclaimer } from './components/LegendAndDisclaimer'
import { FloorPlanCanvas } from './components/FloorPlanCanvas'
import { Toolbar } from './components/Toolbar'
import { ScaleCalibrationModal } from './components/ScaleCalibrationModal'
import { useAppStore } from './store/useAppStore'
import { apiClient } from './api/client'
import { Graph } from './types/graph'

export const App: React.FC = () => {
  const [isCalibrating, setIsCalibrating] = useState(false)

  const {
    planId,
    graph,
    activeTool,
    exits,
    startPoint,
    algorithm,
    options,
    setStartPoint,
    setExits,
    setGraph,
    setRouteResult,
    setError,
  } = useAppStore()

  // Helper to recompute route dynamically
  const recomputeRoute = async (
    currentGraph: Graph,
    start: [number, number] | number | null,
    exitList: number[]
  ) => {
    if (!planId || !currentGraph || !start || exitList.length === 0) {
      setRouteResult(null)
      return
    }
    try {
      const result = await apiClient.computeRoute(planId, {
        algorithm,
        start,
        exit_ids: exitList,
        options,
      })
      setRouteResult(result)
    } catch {
      setRouteResult(null)
    }
  }

  // Handle direct corridor edge toggling / unblocking
  const handleEdgeClick = async (edgeId: number) => {
    if (!planId || !graph) return
    try {
      let updatedGraph: Graph
      if (activeTool === 'unblock_corridor') {
        const edge = graph.edges.find((e) => e.id === edgeId)
        if (edge && !edge.blocked) return
        updatedGraph = await apiClient.unblockEdges(planId, [edgeId])
      } else {
        updatedGraph = await apiClient.toggleEdgesBlock(planId, [edgeId])
      }

      setGraph(updatedGraph)
      if (startPoint && updatedGraph.exits.length > 0) {
        await recomputeRoute(updatedGraph, startPoint, updatedGraph.exits)
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update corridor block'
      setError(msg)
    }
  }

  // Clear all blocked corridor hazards
  const handleClearAllHazards = async () => {
    if (!planId || !graph) return
    try {
      const updatedGraph = await apiClient.clearAllHazards(planId)
      setGraph(updatedGraph)
      if (startPoint && updatedGraph.exits.length > 0) {
        await recomputeRoute(updatedGraph, startPoint, updatedGraph.exits)
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to clear hazards'
      setError(msg)
    }
  }

  // Handle canvas clicks based on currently active toolbar tool
  const handleImageClick = async (point: [number, number]) => {
    if (!graph || !planId) return

    if (activeTool === 'set_start') {
      setStartPoint(point)
      if (exits.length > 0) {
        await recomputeRoute(graph, point, exits)
      } else {
        setRouteResult(null)
      }
    } else if (activeTool === 'mark_exit') {
      // Find nearest node within 40px
      const nearest = graph.nodes
        .map((n) => ({
          node: n,
          dist: Math.hypot(n.x - point[0], n.y - point[1]),
        }))
        .filter((item) => item.dist <= 40)
        .sort((a, b) => a.dist - b.dist)[0]

      if (nearest) {
        await handleNodeClick(nearest.node.id)
      }
    } else if (activeTool === 'block_corridor' || activeTool === 'unblock_corridor') {
      // Find nearest edge polyline segment within 35px
      let nearestEdgeId: number | null = null
      let minDist = 35.0

      const edgesToTest =
        activeTool === 'unblock_corridor'
          ? graph.edges.filter((e) => e.blocked)
          : graph.edges

      for (const e of edgesToTest) {
        const pts: [number, number][] =
          e.polyline && e.polyline.length >= 2
            ? e.polyline
            : (() => {
                const u = graph.nodes.find((n) => n.id === e.source)
                const v = graph.nodes.find((n) => n.id === e.target)
                return u && v ? [[u.x, u.y] as [number, number], [v.x, v.y] as [number, number]] : []
              })()

        for (let i = 0; i < pts.length - 1; i++) {
          const [x1, y1] = pts[i]
          const [x2, y2] = pts[i + 1]
          const dx = x2 - x1
          const dy = y2 - y1
          const lenSq = dx * dx + dy * dy
          let t = lenSq === 0 ? 0 : ((point[0] - x1) * dx + (point[1] - y1) * dy) / lenSq
          t = Math.max(0, Math.min(1, t))
          const projX = x1 + t * dx
          const projY = y1 + t * dy
          const d = Math.hypot(point[0] - projX, point[1] - projY)
          if (d < minDist) {
            minDist = d
            nearestEdgeId = e.id
          }
        }
      }

      if (nearestEdgeId !== null) {
        await handleEdgeClick(nearestEdgeId)
      }
    }
  }

  const handleNodeClick = async (nodeId: number) => {
    if (!planId || !graph) return
    const nextExits = exits.includes(nodeId)
      ? exits.filter((id) => id !== nodeId)
      : [...exits, nodeId]

    try {
      const updatedGraph = await apiClient.updateExits(planId, nextExits)
      setExits(nextExits)
      setGraph(updatedGraph)
      if (startPoint && nextExits.length > 0) {
        await recomputeRoute(updatedGraph, startPoint, nextExits)
      } else {
        setRouteResult(null)
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update exits'
      setError(msg)
    }
  }

  const handleResetPoints = () => {
    setStartPoint(null)
    setRouteResult(null)
  }

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 overflow-hidden">
      {/* Top Header */}
      <header className="h-14 border-b border-slate-800 bg-slate-900/90 px-6 flex items-center justify-between shrink-0 backdrop-blur-md z-10">
        <div className="flex items-center gap-3">
          <div className="p-1.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-400">
            <Compass className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight text-slate-100">
              Emergency Evacuation Route Analyzer
            </h1>
            <p className="text-[11px] text-slate-400">
              Graph-based building evacuation modeling & corridor hazard rerouting
            </p>
          </div>
        </div>
      </header>

      {/* Main Workspace Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <aside className="w-80 border-r border-slate-800 bg-slate-900/60 p-4 flex flex-col gap-4 overflow-y-auto shrink-0">
          <UploadPanel />
          <ProcessingOptions />
          <AlgorithmSelector />
        </aside>

        {/* Center Canvas Area */}
        <main className="flex-1 p-4 bg-slate-950 overflow-hidden flex flex-col gap-3">
          {/* Top Interactive Toolbar */}
          {planId && (
            <Toolbar
              onResetPoints={handleResetPoints}
              onOpenCalibration={() => setIsCalibrating(true)}
              onClearAllHazards={handleClearAllHazards}
            />
          )}

          <div className="flex-1 relative overflow-hidden">
            <FloorPlanCanvas
              onImageClick={handleImageClick}
              onNodeClick={handleNodeClick}
              onEdgeClick={handleEdgeClick}
            />
          </div>
        </main>

        {/* Right Sidebar */}
        <aside className="w-80 border-l border-slate-800 bg-slate-900/60 p-4 flex flex-col gap-4 overflow-y-auto shrink-0">
          <RouteResultsPanel />
          <LegendAndDisclaimer />
        </aside>
      </div>

      {/* Scale Calibration Modal */}
      <ScaleCalibrationModal
        isOpen={isCalibrating}
        onClose={() => setIsCalibrating(false)}
      />
    </div>
  )
}

export default App
