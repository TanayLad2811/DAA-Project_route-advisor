import React, { useEffect, useRef, useState, useCallback } from 'react'
import { ZoomIn, ZoomOut, Maximize2, Move, Network, Eye, EyeOff, DoorOpen } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import {
  ViewTransform,
  calculateFitTransform,
  zoomAtPoint,
  screenToImageCoords,
} from '../utils/coords'
import { NodeType } from '../types/graph'
import { getRouteColor } from '../utils/routeColors'

interface FloorPlanCanvasProps {
  onImageClick?: (imagePoint: [number, number]) => void
  onNodeClick?: (nodeId: number) => void
  onEdgeClick?: (edgeId: number) => void
}

export const FloorPlanCanvas: React.FC<FloorPlanCanvasProps> = ({
  onImageClick,
  onNodeClick,
  onEdgeClick,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const gridCanvasRef = useRef<HTMLCanvasElement>(null)
  const [transform, setTransform] = useState<ViewTransform>({ scale: 1, offsetX: 0, offsetY: 0 })
  const [isPanning, setIsPanning] = useState(false)
  const [cursorCoords, setCursorCoords] = useState<[number, number] | null>(null)
  const [hoveredNodeId, setHoveredNodeId] = useState<number | null>(null)

  // Navigation drag tracking refs to distinguish clicks from drags
  const isMouseDownRef = useRef(false)
  const isDraggingRef = useRef(false)
  const isPanningRef = useRef(false)
  const startMousePosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 })
  const startOffsetRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 })

  const {
    imageUrl,
    imageWidth,
    imageHeight,
    graph,
    layers,
    activeTool,
    toggleLayer,
    startPoint,
    exits,
    suggestedExits,
    routeResult,
    selectedRouteIndex,
  } = useAppStore()

  // Auto-fit image when loaded
  const fitToScreen = useCallback(() => {
    if (!containerRef.current || imageWidth <= 0 || imageHeight <= 0) return
    const rect = containerRef.current.getBoundingClientRect()
    const fit = calculateFitTransform(rect.width, rect.height, imageWidth, imageHeight, 32)
    setTransform(fit)
  }, [imageWidth, imageHeight])

  useEffect(() => {
    if (imageUrl && imageWidth > 0 && imageHeight > 0) {
      fitToScreen()
    }
  }, [imageUrl, imageWidth, imageHeight, fitToScreen])

  // Mouse wheel zoom
  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    e.preventDefault()
    if (!containerRef.current || !imageUrl) return

    const rect = containerRef.current.getBoundingClientRect()
    const focalX = e.clientX - rect.left
    const focalY = e.clientY - rect.top
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85

    setTransform((prev) => zoomAtPoint(prev, zoomFactor, focalX, focalY))
  }

  // Mouse down: start tracking navigation or drag
  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    // Determine whether this mousedown should activate canvas panning
    const shouldPan =
      e.button === 1 || // Middle-click
      e.button === 2 || // Right-click
      (e.button === 0 && (activeTool === 'select' || activeTool === 'pan' || e.altKey || e.shiftKey))

    isMouseDownRef.current = true
    isDraggingRef.current = false
    startMousePosRef.current = { x: e.clientX, y: e.clientY }
    startOffsetRef.current = { x: transform.offsetX, y: transform.offsetY }

    if (shouldPan) {
      isPanningRef.current = true
      setIsPanning(true)
    }
  }

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    const screenX = e.clientX - rect.left
    const screenY = e.clientY - rect.top

    if (imageWidth > 0 && imageHeight > 0) {
      const [imgX, imgY] = screenToImageCoords(screenX, screenY, transform)
      if (imgX >= 0 && imgX <= imageWidth && imgY >= 0 && imgY <= imageHeight) {
        setCursorCoords([Math.round(imgX), Math.round(imgY)])
      } else {
        setCursorCoords(null)
      }
    }

    if (isMouseDownRef.current) {
      const dx = e.clientX - startMousePosRef.current.x
      const dy = e.clientY - startMousePosRef.current.y

      if (Math.hypot(dx, dy) > 4) {
        isDraggingRef.current = true
      }

      if (isPanningRef.current) {
        setTransform((prev) => ({
          ...prev,
          offsetX: startOffsetRef.current.x + dx,
          offsetY: startOffsetRef.current.y + dy,
        }))
      }
    }
  }

  const handleMouseUp = (e: React.MouseEvent<HTMLDivElement>) => {
    const wasDragging = isDraggingRef.current
    const wasPanning = isPanningRef.current

    isMouseDownRef.current = false
    isDraggingRef.current = false
    isPanningRef.current = false
    setIsPanning(false)

    // If mouse was dragged or panned, do not register as a click
    if (wasDragging || wasPanning) {
      return
    }

    // Only left clicks trigger tool actions
    if (e.button === 0 && onImageClick && containerRef.current && imageUrl) {
      const rect = containerRef.current.getBoundingClientRect()
      const screenX = e.clientX - rect.left
      const screenY = e.clientY - rect.top
      const [imgX, imgY] = screenToImageCoords(screenX, screenY, transform)

      if (imgX >= 0 && imgX <= imageWidth && imgY >= 0 && imgY <= imageHeight) {
        onImageClick([imgX, imgY])
      }
    }
  }

  // Prevent browser context menu so right-click drag pans smoothly
  const handleContextMenu = (e: React.MouseEvent<HTMLDivElement>) => {
    e.preventDefault()
  }

  // Render Grid Graph on HTML5 canvas for maximum performance
  useEffect(() => {
    if (!gridCanvasRef.current || !graph || graph.strategy !== 'grid' || !layers.graph) {
      return
    }

    const canvas = gridCanvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.clearRect(0, 0, imageWidth, imageHeight)

    // Draw Edges
    ctx.lineWidth = 1.0
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.25)' // sky blue
    ctx.beginPath()

    const nodeMap = new Map(graph.nodes.map((n) => [n.id, n]))
    for (const edge of graph.edges) {
      if (edge.blocked) continue
      const u = nodeMap.get(edge.source)
      const v = nodeMap.get(edge.target)
      if (u && v) {
        ctx.moveTo(u.x, u.y)
        ctx.lineTo(v.x, v.y)
      }
    }
    ctx.stroke()

    // Draw Nodes
    ctx.fillStyle = 'rgba(14, 165, 233, 0.65)'
    for (const node of graph.nodes) {
      ctx.beginPath()
      ctx.arc(node.x, node.y, 2.0, 0, 2 * Math.PI)
      ctx.fill()
    }
  }, [graph, layers.graph, imageWidth, imageHeight])

  // Get color for node type
  const getNodeColor = (type: NodeType, id: number) => {
    if (exits.includes(id)) return '#22c55e' // Green for exits
    if (type === 'junction') return '#06b6d4' // Cyan for junctions
    if (type === 'dead_end') return '#a855f7' // Purple for dead ends
    if (type === 'door') return '#10b981' // Green for door
    return '#38bdf8' // Blue
  }

  const cursorClass = isPanning
    ? 'cursor-grabbing'
    : activeTool === 'select' || activeTool === 'pan'
    ? 'cursor-grab'
    : activeTool === 'block_corridor' || activeTool === 'unblock_corridor'
    ? 'cursor-pointer'
    : 'cursor-crosshair'

  return (
    <div
      ref={containerRef}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={() => {
        isMouseDownRef.current = false
        isPanningRef.current = false
        setIsPanning(false)
      }}
      onContextMenu={handleContextMenu}
      className={`relative w-full h-full min-h-[500px] bg-slate-950 overflow-hidden select-none border border-slate-800 rounded-xl flex items-center justify-center ${cursorClass}`}
    >
      {/* Background blueprint grid pattern */}
      <div
        className="absolute inset-0 pointer-events-none opacity-20"
        style={{
          backgroundImage:
            'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.15) 1px, transparent 0)',
          backgroundSize: '24px 24px',
        }}
      />

      {imageUrl ? (
        <div
          style={{
            transform: `translate(${transform.offsetX}px, ${transform.offsetY}px) scale(${transform.scale})`,
            transformOrigin: '0 0',
          }}
          className="absolute top-0 left-0 transition-transform duration-75 will-change-transform"
        >
          {/* Main Floor Plan Image */}
          {layers.image && (
            <img
              src={imageUrl}
              alt="Floor Plan"
              draggable={false}
              className="pointer-events-none shadow-2xl rounded-sm max-w-none"
              style={{
                width: `${imageWidth}px`,
                height: `${imageHeight}px`,
              }}
            />
          )}

          {/* Grid Graph HTML5 Canvas (high-speed rendering) */}
          {graph && graph.strategy === 'grid' && layers.graph && (
            <canvas
              ref={gridCanvasRef}
              width={imageWidth}
              height={imageHeight}
              className="absolute top-0 left-0 pointer-events-none"
            />
          )}

          {/* SVG Overlay Container for Skeleton Graph, Doors, Routes & Hazards */}
          <svg
            className="absolute top-0 left-0 pointer-events-none"
            width={imageWidth}
            height={imageHeight}
            viewBox={`0 0 ${imageWidth} ${imageHeight}`}
          >
            {/* Graph Edges (Rendered for skeleton or whenever graph layer is enabled) */}
            {graph && layers.graph && (
              <g className="edges-group">
                {graph.edges.map((edge) => {
                  const pointsStr =
                    edge.polyline && edge.polyline.length >= 2
                      ? edge.polyline.map((p) => `${p[0]},${p[1]}`).join(' ')
                      : (() => {
                          const u = graph.nodes.find((n) => n.id === edge.source)
                          const v = graph.nodes.find((n) => n.id === edge.target)
                          return u && v ? `${u.x},${u.y} ${v.x},${v.y}` : undefined
                        })()

                  if (!pointsStr) return null

                  // Calculate midpoint for hazard badge
                  const midPt =
                    edge.polyline && edge.polyline.length >= 2
                      ? edge.polyline[Math.floor(edge.polyline.length / 2)]
                      : (() => {
                          const u = graph.nodes.find((n) => n.id === edge.source)
                          const v = graph.nodes.find((n) => n.id === edge.target)
                          return u && v ? [Math.round((u.x + v.x) / 2), Math.round((u.y + v.y) / 2)] : null
                        })()

                  return (
                    <g key={`edge-${edge.id}`} className="edge-item">
                      {/* Visual Edge */}
                      <polyline
                        points={pointsStr}
                        fill="none"
                        stroke={edge.blocked ? '#f43f5e' : '#38bdf8'}
                        strokeWidth={edge.blocked ? 4 : 2}
                        strokeDasharray={edge.blocked ? '6 4' : undefined}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        opacity={edge.blocked ? 0.95 : 0.75}
                        filter={
                          edge.blocked
                            ? 'drop-shadow(0 0 4px rgba(244, 63, 94, 0.7))'
                            : undefined
                        }
                      />
                      {/* Invisible wide hit-box for fast clicking & multiple toggling */}
                      <polyline
                        points={pointsStr}
                        fill="none"
                        stroke="transparent"
                        strokeWidth={18}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="cursor-pointer pointer-events-auto hover:stroke-amber-400/35 transition-colors"
                        onClick={(e) => {
                          e.stopPropagation()
                          if (onEdgeClick) onEdgeClick(edge.id)
                        }}
                      >
                        <title>
                          {edge.blocked
                            ? `Corridor #${edge.id} (BLOCKED - Click to unblock)`
                            : `Corridor #${edge.id} (Click to block)`}
                        </title>
                      </polyline>

                      {/* Clickable Unblock Badge on blocked corridors */}
                      {edge.blocked && midPt && (
                        <g
                          className="cursor-pointer pointer-events-auto transition-transform hover:scale-125"
                          onClick={(e) => {
                            e.stopPropagation()
                            if (onEdgeClick) onEdgeClick(edge.id)
                          }}
                        >
                          <rect
                            x={midPt[0] - 13}
                            y={midPt[1] - 8}
                            width={26}
                            height={16}
                            rx={4}
                            fill="#881337"
                            stroke="#f43f5e"
                            strokeWidth={1.5}
                            filter="drop-shadow(0 0 5px rgba(244, 63, 94, 0.8))"
                          />
                          <text
                            x={midPt[0]}
                            y={midPt[1] + 3.5}
                            textAnchor="middle"
                            fill="#ffffff"
                            fontSize={10}
                            fontWeight="bold"
                            pointerEvents="none"
                          >
                            ✕
                          </text>
                          <title>Blocked Corridor #{edge.id} (Click to remove block)</title>
                        </g>
                      )}
                    </g>
                  )
                })}
              </g>
            )}

            {/* Skeleton Graph Nodes */}
            {graph && graph.strategy === 'skeleton' && layers.graph && (
              <g className="nodes-group">
                {graph.nodes.map((node) => {
                  const isExit = exits.includes(node.id)
                  const isHovered = hoveredNodeId === node.id
                  const radius = isExit ? 6.5 : node.type === 'junction' ? 4.5 : 3.5

                  return (
                    <circle
                      key={`node-${node.id}`}
                      cx={node.x}
                      cy={node.y}
                      r={isHovered ? radius + 2 : radius}
                      fill={getNodeColor(node.type, node.id)}
                      stroke="#0f172a"
                      strokeWidth={1.5}
                      className="cursor-pointer pointer-events-auto transition-transform hover:scale-125"
                      onMouseEnter={() => setHoveredNodeId(node.id)}
                      onMouseLeave={() => setHoveredNodeId(null)}
                      onClick={(e) => {
                        e.stopPropagation()
                        if (onNodeClick) onNodeClick(node.id)
                      }}
                    >
                      <title>
                        Node #{node.id} ({node.type}) - Clearance:{' '}
                        {node.clearance !== null ? `${node.clearance}px` : 'N/A'}
                      </title>
                    </circle>
                  )
                })}
              </g>
            )}

            {/* Detected Doors Overlay */}
            {layers.doors &&
              graph?.doors &&
              graph.doors.map((door) => {
                const isExitDoor = door.type === 'exit'
                const isMarkedExit =
                  door.nearest_node_id !== null &&
                  door.nearest_node_id !== undefined &&
                  exits.includes(door.nearest_node_id)

                return (
                  <g
                    key={`door-${door.id}`}
                    className="cursor-pointer pointer-events-auto transition-transform hover:scale-110"
                    onClick={(e) => {
                      e.stopPropagation()
                      if (
                        door.nearest_node_id !== null &&
                        door.nearest_node_id !== undefined &&
                        onNodeClick
                      ) {
                        onNodeClick(door.nearest_node_id)
                      }
                    }}
                  >
                    <circle
                      cx={door.x}
                      cy={door.y}
                      r={isExitDoor ? 9 : 6}
                      fill={isExitDoor ? (isMarkedExit ? '#10b981' : '#059669') : '#06b6d4'}
                      fillOpacity={0.85}
                      stroke="#ffffff"
                      strokeWidth={1.5}
                      filter={
                        isExitDoor ? 'drop-shadow(0 0 6px rgba(16, 185, 129, 0.8))' : undefined
                      }
                    />
                    {isExitDoor && (
                      <text
                        x={door.x}
                        y={door.y + 3}
                        textAnchor="middle"
                        fill="#ffffff"
                        fontSize={7}
                        fontWeight="bold"
                        pointerEvents="none"
                      >
                        EXIT
                      </text>
                    )}
                    <title>
                      {isExitDoor
                        ? `Exit Door #${door.id} (${isMarkedExit ? 'Active Emergency Exit' : 'Click to toggle exit'})`
                        : `Doorway #${door.id} (Confidence: ${Math.round(door.confidence * 100)}%)`}
                    </title>
                  </g>
                )
              })}

            {/* Suggested Exits (pulsating rings) */}
            {suggestedExits &&
              suggestedExits.map((ex, idx) => (
                <g
                  key={`sugg-ex-${idx}`}
                  className="cursor-pointer pointer-events-auto"
                  onClick={(e) => {
                    e.stopPropagation()
                    if (
                      ex.nearest_node_id !== undefined &&
                      ex.nearest_node_id !== null &&
                      onNodeClick
                    ) {
                      onNodeClick(ex.nearest_node_id)
                    }
                  }}
                >
                  <circle
                    cx={ex.x}
                    cy={ex.y}
                    r={10}
                    fill="none"
                    stroke="#22c55e"
                    strokeWidth={2}
                    strokeDasharray="3 2"
                    className="animate-spin"
                    style={{ animationDuration: '6s' }}
                  />
                  <circle cx={ex.x} cy={ex.y} r={4} fill="#22c55e" />
                  <title>Suggested Exit (Click to confirm)</title>
                </g>
              ))}

            {/* Start Marker */}
            {startPoint && (
              <g>
                {Array.isArray(startPoint) ? (
                  <circle
                    cx={startPoint[0]}
                    cy={startPoint[1]}
                    r={8}
                    fill="#3b82f6"
                    stroke="#ffffff"
                    strokeWidth={2}
                    className="animate-pulse"
                  />
                ) : null}
              </g>
            )}

            {/* Drawn Evacuation Routes */}
            {layers.routes &&
              routeResult &&
              routeResult.routes.map((route, idx) => {
                const pointsStr = route.points.map((p) => `${p[0]},${p[1]}`).join(' ')
                const isPrimary = idx === 0
                const isSelected = selectedRouteIndex === idx
                const color = getRouteColor(idx, routeResult.routes.length)

                return (
                  <g key={`route-${idx}`} className="route-layer">
                    {/* Soft halo glow under the route */}
                    <polyline
                      points={pointsStr}
                      fill="none"
                      stroke={color}
                      strokeWidth={isSelected ? 9 : isPrimary ? 7 : 5}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      opacity={isSelected ? 0.45 : 0.25}
                      filter={`drop-shadow(0 0 6px ${color})`}
                    />
                    {/* Main crisp visible spectrum line */}
                    <polyline
                      points={pointsStr}
                      fill="none"
                      stroke={color}
                      strokeWidth={isSelected ? 5.5 : isPrimary ? 4.2 : 3}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeDasharray={isPrimary ? '8 4' : `${6 + (idx % 3) * 2} 4`}
                      opacity={isSelected ? 1.0 : isPrimary ? 0.95 : 0.85}
                    />
                  </g>
                )
              })}
          </svg>
        </div>
      ) : (
        <div className="text-center p-8 text-slate-500">
          <Move className="w-10 h-10 mx-auto mb-2 text-slate-600 animate-pulse" />
          <p className="text-sm font-medium">No floor plan active</p>
          <p className="text-xs text-slate-600 mt-1">Upload a plan to view and analyze routes</p>
        </div>
      )}

      {/* Top Canvas Layer Controls & Graph Info */}
      {imageUrl && (
        <div className="absolute top-4 left-4 flex items-center gap-2">
          {/* Layer toggles */}
          <div className="flex items-center gap-1 bg-slate-900/90 border border-slate-700/80 rounded-lg p-1 shadow-xl backdrop-blur-md">
            <button
              onClick={() => toggleLayer('image')}
              className={`px-2 py-1 text-xs rounded font-medium flex items-center gap-1 transition-colors ${
                layers.image
                  ? 'bg-slate-800 text-slate-200'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
              title="Toggle Floor Plan Image"
            >
              {layers.image ? (
                <Eye className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <EyeOff className="w-3.5 h-3.5" />
              )}
              Plan
            </button>
            <button
              onClick={() => toggleLayer('graph')}
              className={`px-2 py-1 text-xs rounded font-medium flex items-center gap-1 transition-colors ${
                layers.graph
                  ? 'bg-slate-800 text-slate-200'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
              title="Toggle Graph Overlay"
            >
              <Network className="w-3.5 h-3.5 text-sky-400" />
              Graph
            </button>
            <button
              onClick={() => toggleLayer('doors')}
              className={`px-2 py-1 text-xs rounded font-medium flex items-center gap-1 transition-colors ${
                layers.doors
                  ? 'bg-slate-800 text-slate-200'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
              title="Toggle Doors Overlay"
            >
              <DoorOpen className="w-3.5 h-3.5 text-emerald-400" />
              Doors
            </button>
          </div>

          {/* Graph status pills */}
          {graph && (
            <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-700/80 rounded-lg px-3 py-1.5 shadow-xl backdrop-blur-md text-xs font-mono">
              <span className="capitalize text-emerald-400 font-semibold">{graph.strategy}</span>
              <span className="text-slate-500">•</span>
              <span className="text-slate-300">{graph.nodes.length.toLocaleString()} nodes</span>
              <span className="text-slate-500">•</span>
              <span className="text-slate-300">{graph.edges.length.toLocaleString()} edges</span>
              {graph.doors && graph.doors.length > 0 && (
                <>
                  <span className="text-slate-500">•</span>
                  <span className="text-cyan-400">{graph.doors.length} doors</span>
                </>
              )}
              {graph.exits.length > 0 && (
                <>
                  <span className="text-slate-500">•</span>
                  <span className="text-emerald-400">{graph.exits.length} exits</span>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* Floating Canvas Controls */}
      {imageUrl && (
        <div className="absolute bottom-4 right-4 flex items-center gap-1.5 bg-slate-900/90 border border-slate-700/80 rounded-lg p-1.5 shadow-xl backdrop-blur-md">
          <span className="text-xs font-mono text-slate-400 px-2 select-none">
            {Math.round(transform.scale * 100)}%
          </span>
          <div className="h-4 w-px bg-slate-700" />
          <button
            onClick={() => {
              if (!containerRef.current) return
              const rect = containerRef.current.getBoundingClientRect()
              setTransform((prev) => zoomAtPoint(prev, 1.25, rect.width / 2, rect.height / 2))
            }}
            className="p-1.5 text-slate-300 hover:text-emerald-400 hover:bg-slate-800 rounded transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              if (!containerRef.current) return
              const rect = containerRef.current.getBoundingClientRect()
              setTransform((prev) => zoomAtPoint(prev, 0.8, rect.width / 2, rect.height / 2))
            }}
            className="p-1.5 text-slate-300 hover:text-emerald-400 hover:bg-slate-800 rounded transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={fitToScreen}
            className="p-1.5 text-slate-300 hover:text-emerald-400 hover:bg-slate-800 rounded transition-colors"
            title="Fit to Screen"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Cursor coordinates indicator */}
      {cursorCoords && (
        <div className="absolute bottom-4 left-4 bg-slate-900/80 border border-slate-700/70 rounded px-2.5 py-1 text-[11px] font-mono text-slate-400 backdrop-blur-sm select-none">
          X: {cursorCoords[0]} px | Y: {cursorCoords[1]} px
        </div>
      )}
    </div>
  )
}
