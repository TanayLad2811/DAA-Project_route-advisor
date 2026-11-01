import React, { useEffect, useState } from 'react'
import { Sliders, Eye, EyeOff, Layers, Sparkles } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { apiClient } from '../api/client'
import { GraphBuildRequest } from '../types/graph'

interface ProcessingOptionsProps {
  onBuildGraph?: (req: GraphBuildRequest) => void
}

export const ProcessingOptions: React.FC<ProcessingOptionsProps> = ({ onBuildGraph }) => {
  const { planId, loading, setGraph, setLoading, setError } = useAppStore()

  const [strategy, setStrategy] = useState<'grid' | 'skeleton'>('grid')
  const [threshold, setThreshold] = useState<number>(127)
  const [autoThreshold, setAutoThreshold] = useState<boolean>(false)
  const [invert, setInvert] = useState<boolean>(false)
  const [closeKernel, setCloseKernel] = useState<number>(3)
  const [minClearancePx, setMinClearancePx] = useState<number>(3.0)
  const [filterAnnotations, setFilterAnnotations] = useState<boolean>(true)
  const [detectDoors, setDetectDoors] = useState<boolean>(true)

  // Live debug preview stage
  const [debugStage, setDebugStage] = useState<'none' | 'wall_mask' | 'distance_transform'>('none')
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  // Debounced live preview generation
  useEffect(() => {
    if (!planId || debugStage === 'none') {
      setPreviewUrl(null)
      return
    }

    const handler = setTimeout(() => {
      const effThresh = autoThreshold ? 0 : threshold
      const url = `${apiClient.getDebugImageUrl(planId, debugStage)}?wall_threshold=${effThresh}&invert=${invert}&close_kernel=${closeKernel}&min_clearance_px=${minClearancePx}&t=${Date.now()}`
      setPreviewUrl(url)
    }, 250)

    return () => clearTimeout(handler)
  }, [planId, debugStage, threshold, autoThreshold, invert, closeKernel, minClearancePx])

  const handleBuild = async () => {
    if (!planId) return
    const effThresh = autoThreshold ? 0 : threshold
    const req: GraphBuildRequest = {
      strategy,
      wall_threshold: effThresh,
      invert,
      close_kernel: closeKernel,
      min_clearance_px: minClearancePx,
      filter_annotations: filterAnnotations,
      detect_doors: detectDoors,
    }

    if (onBuildGraph) {
      onBuildGraph(req)
      return
    }

    try {
      setLoading(true, `Building ${strategy} graph...`)
      const res = await apiClient.buildGraph(planId, req)
      setGraph(res.graph, res.suggested_exits)
      setLoading(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to build graph'
      setError(msg)
      setLoading(false)
    }
  }

  if (!planId) return null

  return (
    <div className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-4 shadow-lg backdrop-blur-sm space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <Sliders className="w-4 h-4 text-emerald-400" />
          Processing & Graph
        </h2>
      </div>

      {/* Strategy selector */}
      <div>
        <label className="text-xs font-medium text-slate-400 block mb-1.5">
          Graph Strategy
        </label>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => setStrategy('grid')}
            className={`px-3 py-2 text-xs font-medium rounded-lg border text-left transition-all ${
              strategy === 'grid'
                ? 'bg-emerald-500/15 border-emerald-500/60 text-emerald-300'
                : 'bg-slate-900/60 border-slate-700 text-slate-400 hover:border-slate-600'
            }`}
          >
            <div className="font-semibold text-slate-200">Grid Occupancy</div>
            <div className="text-[10px] text-slate-400 mt-0.5">Robust, open areas</div>
          </button>
          <button
            type="button"
            onClick={() => setStrategy('skeleton')}
            className={`px-3 py-2 text-xs font-medium rounded-lg border text-left transition-all ${
              strategy === 'skeleton'
                ? 'bg-emerald-500/15 border-emerald-500/60 text-emerald-300'
                : 'bg-slate-900/60 border-slate-700 text-slate-400 hover:border-slate-600'
            }`}
          >
            <div className="font-semibold text-slate-200">Skeleton Graph</div>
            <div className="text-[10px] text-slate-400 mt-0.5">Corridor centerlines</div>
          </button>
        </div>
      </div>

      {/* Wall Threshold Slider */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <label className="font-medium text-slate-300">Wall Threshold</label>
          <span className="font-mono text-slate-400">
            {autoThreshold ? 'Otsu (Auto)' : threshold}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="range"
            min={1}
            max={254}
            disabled={autoThreshold}
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
            className="flex-1 accent-emerald-400 cursor-pointer disabled:opacity-40"
          />
          <button
            type="button"
            onClick={() => setAutoThreshold(!autoThreshold)}
            className={`px-2 py-1 text-[11px] rounded border font-medium transition-colors ${
              autoThreshold
                ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300'
                : 'bg-slate-900 border-slate-700 text-slate-400 hover:border-slate-600'
            }`}
          >
            Auto
          </button>
        </div>
      </div>

      {/* Invert, Morphological Closing & Clearance */}
      <div className="space-y-3 pt-1">
        <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={invert}
            onChange={(e) => setInvert(e.target.checked)}
            className="rounded border-slate-600 bg-slate-900 text-emerald-500 focus:ring-emerald-400"
          />
          <span>Invert (Blueprint)</span>
        </label>

        <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={filterAnnotations}
            onChange={(e) => setFilterAnnotations(e.target.checked)}
            className="rounded border-slate-600 bg-slate-900 text-emerald-500 focus:ring-emerald-400"
          />
          <span>Filter Dimensions / Annotations</span>
        </label>

        <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={detectDoors}
            onChange={(e) => setDetectDoors(e.target.checked)}
            className="rounded border-slate-600 bg-slate-900 text-emerald-500 focus:ring-emerald-400"
          />
          <span>Auto-detect Doors & Exits</span>
        </label>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>Close Gap</span>
              <span className="font-mono">{closeKernel}px</span>
            </div>
            <input
              type="range"
              min={1}
              max={9}
              step={2}
              value={closeKernel}
              onChange={(e) => setCloseKernel(Number(e.target.value))}
              className="w-full accent-emerald-400 cursor-pointer"
            />
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>Min Clearance</span>
              <span className="font-mono">{minClearancePx}px</span>
            </div>
            <input
              type="range"
              min={0}
              max={15}
              step={1}
              value={minClearancePx}
              onChange={(e) => setMinClearancePx(Number(e.target.value))}
              className="w-full accent-emerald-400 cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* Live Preview Toggle */}
      <div className="pt-2 border-t border-slate-700/60">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-slate-400 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-slate-400" />
            Live Mask Preview
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setDebugStage(debugStage === 'wall_mask' ? 'none' : 'wall_mask')}
              className={`px-2 py-0.5 text-[11px] rounded flex items-center gap-1 border transition-colors ${
                debugStage === 'wall_mask'
                  ? 'bg-amber-500/20 border-amber-500/50 text-amber-300'
                  : 'bg-slate-900 border-slate-700 text-slate-400 hover:border-slate-600'
              }`}
            >
              {debugStage === 'wall_mask' ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
              Wall Mask
            </button>
            <button
              type="button"
              onClick={() =>
                setDebugStage(debugStage === 'distance_transform' ? 'none' : 'distance_transform')
              }
              className={`px-2 py-0.5 text-[11px] rounded flex items-center gap-1 border transition-colors ${
                debugStage === 'distance_transform'
                  ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300'
                  : 'bg-slate-900 border-slate-700 text-slate-400 hover:border-slate-600'
              }`}
            >
              Clearance
            </button>
          </div>
        </div>

        {previewUrl && (
          <div className="relative w-full h-24 bg-slate-950 rounded-lg overflow-hidden border border-slate-700/80 mb-2 flex items-center justify-center">
            <img
              src={previewUrl}
              alt="Live Mask Preview"
              className="max-h-full max-w-full object-contain"
            />
            <span className="absolute bottom-1 right-2 text-[9px] bg-slate-900/80 px-1 rounded text-slate-400">
              Live Preview
            </span>
          </div>
        )}
      </div>

      {/* Build Graph Action Button */}
      <button
        type="button"
        onClick={handleBuild}
        disabled={loading}
        className="w-full py-2.5 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium text-xs flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/40 transition-colors"
      >
        <Sparkles className="w-4 h-4" />
        {loading ? 'Processing...' : `Build ${strategy === 'grid' ? 'Grid' : 'Skeleton'} Graph`}
      </button>
    </div>
  )
}
