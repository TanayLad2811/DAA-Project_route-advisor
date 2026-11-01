import React from 'react'
import {
  Clock,
  Milestone,
  CornerDownRight,
  Shield,
  Download,
  AlertTriangle,
} from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { getRouteColor, getRouteSpectrumName } from '../utils/routeColors'

export const RouteResultsPanel: React.FC = () => {
  const { routeResult, selectedRouteIndex, setSelectedRouteIndex } = useAppStore()

  if (!routeResult) return null

  const handleExportJson = () => {
    const dataStr =
      'data:text/json;charset=utf-8,' +
      encodeURIComponent(JSON.stringify(routeResult, null, 2))
    const downloadAnchor = document.createElement('a')
    downloadAnchor.setAttribute('href', dataStr)
    downloadAnchor.setAttribute('download', `evacuation_route_${Date.now()}.json`)
    document.body.appendChild(downloadAnchor)
    downloadAnchor.click()
    downloadAnchor.remove()
  }

  return (
    <div className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-4 shadow-lg backdrop-blur-sm space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <Milestone className="w-4 h-4 text-emerald-400" />
          Evacuation Results
        </h2>
        <span className="text-[11px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-700">
          {routeResult.stats.runtime_ms} ms
        </span>
      </div>

      {/* Warnings & Alerts */}
      {routeResult.warnings && routeResult.warnings.length > 0 && (
        <div className="space-y-1.5">
          {routeResult.warnings.map((w, idx) => (
            <div
              key={idx}
              className="p-2.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start gap-2"
            >
              <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}

      {/* Routes List */}
      {routeResult.routes.length === 0 ? (
        <div className="p-4 bg-slate-900/60 rounded-lg text-center text-slate-400 text-xs">
          No evacuation routes found to the designated exits.
        </div>
      ) : (
        <div className="space-y-2">
          {routeResult.routes.map((route, idx) => {
            const isSelected = selectedRouteIndex === idx
            const isPrimary = idx === 0
            const color = getRouteColor(idx, routeResult.routes.length)
            const spectrumName = getRouteSpectrumName(idx)

            return (
              <div
                key={idx}
                onClick={() => setSelectedRouteIndex(idx)}
                style={{
                  borderColor: isSelected ? color : undefined,
                  backgroundColor: isSelected ? `${color}18` : undefined,
                }}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  isSelected
                    ? 'shadow-lg shadow-black/40'
                    : 'bg-slate-900/50 border-slate-700/70 hover:border-slate-600'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-3 h-3 rounded-full shrink-0 shadow-sm transition-transform"
                      style={{
                        backgroundColor: color,
                        boxShadow: `0 0 8px ${color}80`,
                        transform: isSelected ? 'scale(1.2)' : 'scale(1)',
                      }}
                    />
                    <div>
                      <span className="text-xs font-semibold text-slate-200 block">
                        {isPrimary ? 'Primary Evacuation Route' : `Alternative Route #${idx}`}
                      </span>
                      {!isPrimary && (
                        <span className="text-[10px] font-medium" style={{ color }}>
                          Visible Spectrum: {spectrumName}
                        </span>
                      )}
                    </div>
                  </div>
                  <span className="text-[11px] font-mono text-slate-400 bg-slate-950/70 px-2 py-0.5 rounded border border-slate-800">
                    Exit #{route.exit_id}
                  </span>
                </div>

                {/* Metrics Grid */}
                <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-300">
                  <div className="flex items-center gap-1.5 bg-slate-950/60 p-1.5 rounded">
                    <Milestone className="w-3.5 h-3.5 text-slate-400" />
                    <span>
                      {route.distance_m !== null && route.distance_m !== undefined ? (
                        <>
                          <strong className="text-slate-100">{route.distance_m}</strong> m
                        </>
                      ) : (
                        <>
                          <strong className="text-slate-100">{route.distance_px}</strong> px
                        </>
                      )}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 bg-slate-950/60 p-1.5 rounded">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    <span>
                      {route.est_time_s !== null && route.est_time_s !== undefined ? (
                        <>
                          <strong className="text-slate-100">{route.est_time_s}</strong> sec
                        </>
                      ) : (
                        <span className="text-slate-500">Uncalibrated</span>
                      )}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 bg-slate-950/60 p-1.5 rounded">
                    <CornerDownRight className="w-3.5 h-3.5 text-slate-400" />
                    <span>
                      <strong className="text-slate-100">{route.turns}</strong> turns (
                      {route.hops} hops)
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 bg-slate-950/60 p-1.5 rounded">
                    <Shield className="w-3.5 h-3.5 text-slate-400" />
                    <span>
                      Clearance:{' '}
                      <strong className="text-slate-100">
                        {route.min_clearance_m !== null && route.min_clearance_m !== undefined
                          ? `${route.min_clearance_m} m`
                          : 'Optimal'}
                      </strong>
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* JSON Export Button */}
      {routeResult.routes.length > 0 && (
        <button
          type="button"
          onClick={handleExportJson}
          className="w-full py-2 px-3 rounded-lg border border-slate-700 bg-slate-900/60 hover:bg-slate-900 text-slate-300 hover:text-slate-100 text-xs font-medium flex items-center justify-center gap-2 transition-colors"
        >
          <Download className="w-3.5 h-3.5 text-slate-400" />
          Export Route Scenario (JSON)
        </button>
      )}
    </div>
  )
}
