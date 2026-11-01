import React from 'react'
import { Info, ShieldAlert } from 'lucide-react'

export const LegendAndDisclaimer: React.FC = () => {
  return (
    <div className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-4 shadow-lg backdrop-blur-sm space-y-3 text-xs">
      <div className="flex items-center gap-2 text-slate-300 font-semibold uppercase tracking-wider text-[11px]">
        <Info className="w-3.5 h-3.5 text-sky-400" />
        Map Legend & Symbology
      </div>

      <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-300">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-sm" />
          <span>Exit Node</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-sm" />
          <span>Start Point</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-sm" />
          <span>Junction</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-teal-400 border border-teal-200 shadow-sm" />
          <span>Interior Door</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-emerald-400/50 shadow-sm" />
          <span>Exit Doorway</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-purple-400 shadow-sm" />
          <span>Dead End</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-4 h-1 bg-emerald-400 rounded-sm inline-block shadow-[0_0_6px_rgba(16,185,129,0.7)]" />
          <span>Primary Route (Emerald)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-4 h-1 rounded-sm inline-block bg-gradient-to-r from-orange-400 via-yellow-400 via-cyan-400 to-purple-400" />
          <span>Alt Routes (Visible Spectrum)</span>
        </div>
        <div className="flex items-center gap-2 col-span-2">
          <span className="w-4 h-0.5 bg-rose-500 inline-block border-t-2 border-dashed border-rose-400" />
          <span>Blocked Corridor (Click to Unblock)</span>
        </div>
      </div>

      <div className="pt-2 border-t border-slate-700/60">
        <div className="flex items-start gap-2 text-[10px] text-slate-400 leading-relaxed">
          <ShieldAlert className="w-3.5 h-3.5 shrink-0 text-amber-400 mt-0.5" />
          <span>
            <strong>Disclaimer:</strong> This is an algorithmic evaluation tool for educational and planning simulation. It does not certify compliance with NFPA, IBC, or local emergency codes.
          </span>
        </div>
      </div>
    </div>
  )
}

