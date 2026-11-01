import React, { useState } from 'react'
import { Ruler, X, Check } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { apiClient } from '../api/client'

interface ScaleCalibrationModalProps {
  isOpen: boolean
  onClose: () => void
}

export const ScaleCalibrationModal: React.FC<ScaleCalibrationModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { planId, graph, setGraph, setLoading, setError } = useAppStore()

  const [ptAX, setPtAX] = useState<number>(0)
  const [ptAY, setPtAY] = useState<number>(0)
  const [ptBX, setPtBX] = useState<number>(100)
  const [ptBY, setPtBY] = useState<number>(0)
  const [realDistanceM, setRealDistanceM] = useState<number>(10.0)

  if (!isOpen || !planId) return null

  const pixelDistance = Math.hypot(ptBX - ptAX, ptBY - ptAY)

  const handleCalibrate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (realDistanceM <= 0) {
      setError('Real-world distance must be greater than 0 meters.')
      return
    }

    try {
      setLoading(true, 'Calibrating floor plan scale...')
      const updatedGraph = await apiClient.calibrateScale(planId, {
        point_a: [ptAX, ptAY],
        point_b: [ptBX, ptBY],
        real_distance_m: realDistanceM,
      })
      setGraph(updatedGraph)
      setLoading(false)
      onClose()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Scale calibration failed'
      setError(msg)
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-md w-full p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2 mb-4 text-emerald-400">
          <Ruler className="w-5 h-5" />
          <h2 className="text-base font-bold text-slate-100">Scale Calibration</h2>
        </div>

        <p className="text-xs text-slate-400 mb-4">
          Enter coordinates for a known dimension (e.g. door width, corridor span, or wall length) to calculate real-world meters per pixel.
        </p>

        <form onSubmit={handleCalibrate} className="space-y-4 text-xs">
          {/* Point A */}
          <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
            <span className="font-semibold text-slate-300">Point A (Reference Origin)</span>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] text-slate-500 block">X (pixels)</label>
                <input
                  type="number"
                  value={ptAX}
                  onChange={(e) => setPtAX(Number(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200"
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-500 block">Y (pixels)</label>
                <input
                  type="number"
                  value={ptAY}
                  onChange={(e) => setPtAY(Number(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200"
                />
              </div>
            </div>
          </div>

          {/* Point B */}
          <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
            <span className="font-semibold text-slate-300">Point B (Reference Target)</span>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] text-slate-500 block">X (pixels)</label>
                <input
                  type="number"
                  value={ptBX}
                  onChange={(e) => setPtBX(Number(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200"
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-500 block">Y (pixels)</label>
                <input
                  type="number"
                  value={ptBY}
                  onChange={(e) => setPtBY(Number(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200"
                />
              </div>
            </div>
          </div>

          {/* Real Distance */}
          <div>
            <label className="text-slate-300 font-medium block mb-1">
              Known Real Distance (Meters)
            </label>
            <input
              type="number"
              step="0.1"
              min="0.1"
              value={realDistanceM}
              onChange={(e) => setRealDistanceM(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 font-medium"
            />
          </div>

          {/* Calculated Scale Result */}
          <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-300 text-[11px] flex items-center justify-between">
            <span>Computed Pixel Span:</span>
            <span className="font-mono font-bold">{pixelDistance.toFixed(1)} px</span>
          </div>

          {graph?.meters_per_pixel && (
            <div className="text-[11px] text-slate-400">
              Current Calibration:{' '}
              <span className="text-emerald-400 font-mono">
                {graph.meters_per_pixel} m / px
              </span>
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg bg-emerald-600 text-white font-medium hover:bg-emerald-500 flex items-center gap-1.5"
            >
              <Check className="w-4 h-4" />
              Apply Scale
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

