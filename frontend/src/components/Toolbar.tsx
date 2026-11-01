import React from 'react'
import {
  MousePointer,
  MapPin,
  DoorOpen,
  Flame,
  ShieldCheck,
  Ruler,
  RotateCcw,
  Trash2,
} from 'lucide-react'
import { useAppStore, ActiveTool } from '../store/useAppStore'

interface ToolbarProps {
  onResetPoints?: () => void
  onOpenCalibration?: () => void
  onClearAllHazards?: () => void
}

export const Toolbar: React.FC<ToolbarProps> = ({
  onResetPoints,
  onOpenCalibration,
  onClearAllHazards,
}) => {
  const { activeTool, setActiveTool, startPoint, exits, graph } = useAppStore()

  const blockedCount = graph ? graph.edges.filter((e) => e.blocked).length : 0

  const tools: { id: ActiveTool; label: string; icon: React.ReactNode; tooltip: string }[] = [
    {
      id: 'select',
      label: 'Select / Pan',
      icon: <MousePointer className="w-4 h-4" />,
      tooltip: 'Pan and inspect elements',
    },
    {
      id: 'set_start',
      label: 'Set Start',
      icon: <MapPin className="w-4 h-4 text-blue-400" />,
      tooltip: 'Click anywhere to place start point',
    },
    {
      id: 'mark_exit',
      label: 'Mark Exit',
      icon: <DoorOpen className="w-4 h-4 text-emerald-400" />,
      tooltip: 'Click a node or door to toggle emergency exit',
    },
    {
      id: 'block_corridor',
      label: 'Block Corridor',
      icon: <Flame className="w-4 h-4 text-rose-400" />,
      tooltip: 'Click an edge to block with hazard/debris',
    },
    {
      id: 'unblock_corridor',
      label: 'Unblock Corridor',
      icon: <ShieldCheck className="w-4 h-4 text-emerald-400" />,
      tooltip: 'Click a blocked corridor to clear the hazard',
    },
    {
      id: 'calibrate',
      label: 'Calibrate Scale',
      icon: <Ruler className="w-4 h-4 text-amber-400" />,
      tooltip: 'Calibrate pixels to real-world meters',
    },
  ]

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-1.5 shadow-xl backdrop-blur-md flex items-center justify-between gap-2 flex-wrap">
      <div className="flex items-center gap-1">
        {tools.map((t) => {
          const isActive = activeTool === t.id
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => {
                if (t.id === 'calibrate' && onOpenCalibration) {
                  onOpenCalibration()
                } else {
                  setActiveTool(t.id)
                }
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                isActive
                  ? 'bg-slate-800 text-white shadow-sm border border-slate-700'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
              title={t.tooltip}
            >
              {t.icon}
              <span className="hidden sm:inline">{t.label}</span>
            </button>
          )
        })}
      </div>

      <div className="flex items-center gap-2">
        {/* Unblock All Hazards Button */}
        {blockedCount > 0 && onClearAllHazards && (
          <button
            type="button"
            onClick={onClearAllHazards}
            className="px-2.5 py-1.5 rounded-lg text-xs font-medium bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-300 flex items-center gap-1.5 transition-colors shadow-sm animate-pulse"
            title="Unblock and clear all corridor hazards"
          >
            <Trash2 className="w-3.5 h-3.5 text-rose-400" />
            <span>Unblock All ({blockedCount})</span>
          </button>
        )}

        {/* Markers info and reset */}
        <div className="flex items-center gap-2 pl-2 border-l border-slate-800 text-xs">
          <span className="text-slate-400 text-[11px]">
            Start: {startPoint ? '✓ Set' : 'None'} | Exits: {exits.length}
          </span>
          {onResetPoints && (startPoint || exits.length > 0) && (
            <button
              onClick={onResetPoints}
              className="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors"
              title="Clear start and exit points"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
