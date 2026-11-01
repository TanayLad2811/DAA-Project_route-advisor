import React from 'react'
import { Navigation, Route, Zap, Compass, AlertTriangle } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { apiClient } from '../api/client'

export const AlgorithmSelector: React.FC = () => {
  const {
    planId,
    graph,
    algorithm,
    options,
    startPoint,
    exits,
    loading,
    setAlgorithm,
    setOptions,
    setRouteResult,
    setLoading,
    setError,
  } = useAppStore()

  const handleComputeRoute = async () => {
    if (!planId) return
    if (!startPoint) {
      setError('Please click on the floor plan to set an evacuation start location.')
      return
    }
    if (exits.length === 0) {
      setError('Please mark at least one exit on the floor plan.')
      return
    }

    try {
      setLoading(true, 'Computing optimal evacuation route...')
      const result = await apiClient.computeRoute(planId, {
        algorithm,
        start: startPoint,
        exit_ids: exits,
        options,
      })
      setRouteResult(result)
      setLoading(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Routing calculation failed'
      setError(msg)
      setLoading(false)
    }
  }

  const isGridAndDfsAll = graph?.strategy === 'grid' && algorithm === 'dfs' && options.dfs_mode === 'all'

  return (
    <div className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-4 shadow-lg backdrop-blur-sm space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <Navigation className="w-4 h-4 text-emerald-400" />
          Evacuation Algorithm
        </h2>
      </div>

      {/* Algorithm Radio Cards */}
      <div className="space-y-2">
        {/* Shortest Path Card */}
        <label
          className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
            algorithm === 'shortest_path'
              ? 'bg-emerald-500/10 border-emerald-500/60 shadow-sm'
              : 'bg-slate-900/50 border-slate-700/70 hover:border-slate-600'
          }`}
        >
          <input
            type="radio"
            name="algorithm"
            value="shortest_path"
            checked={algorithm === 'shortest_path'}
            onChange={() => setAlgorithm('shortest_path')}
            className="mt-0.5 text-emerald-500 focus:ring-emerald-400"
          />
          <div className="flex-1 text-xs">
            <div className="flex items-center gap-1.5 font-semibold text-slate-200">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              Shortest Path (Recommended)
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Dijkstra / A* minimum physical distance route to nearest exit with ranked alternatives.
            </p>
          </div>
        </label>

        {/* BFS Card */}
        <label
          className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
            algorithm === 'bfs'
              ? 'bg-emerald-500/10 border-emerald-500/60 shadow-sm'
              : 'bg-slate-900/50 border-slate-700/70 hover:border-slate-600'
          }`}
        >
          <input
            type="radio"
            name="algorithm"
            value="bfs"
            checked={algorithm === 'bfs'}
            onChange={() => setAlgorithm('bfs')}
            className="mt-0.5 text-emerald-500 focus:ring-emerald-400"
          />
          <div className="flex-1 text-xs">
            <div className="flex items-center gap-1.5 font-semibold text-slate-200">
              <Compass className="w-3.5 h-3.5 text-sky-400" />
              BFS (Fewest Hops)
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Unweighted breadth-first exploration finding the route with fewest corridor junctions.
            </p>
          </div>
        </label>

        {/* DFS Card */}
        <label
          className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
            algorithm === 'dfs'
              ? 'bg-emerald-500/10 border-emerald-500/60 shadow-sm'
              : 'bg-slate-900/50 border-slate-700/70 hover:border-slate-600'
          }`}
        >
          <input
            type="radio"
            name="algorithm"
            value="dfs"
            checked={algorithm === 'dfs'}
            onChange={() => setAlgorithm('dfs')}
            className="mt-0.5 text-emerald-500 focus:ring-emerald-400"
          />
          <div className="flex-1 text-xs">
            <div className="flex items-center gap-1.5 font-semibold text-slate-200">
              <Route className="w-3.5 h-3.5 text-purple-400" />
              DFS (Route Exploration)
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Finds a valid evacuation corridor or enumerates all existing simple escape paths.
            </p>
          </div>
        </label>
      </div>

      {/* Conditional Options per Algorithm */}
      {algorithm === 'shortest_path' && (
        <div className="bg-slate-900/60 rounded-lg p-3 border border-slate-700/60 space-y-3 text-xs">
          <div>
            <label className="text-[11px] font-medium text-slate-400 block mb-1">Variant</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setOptions({ shortest_variant: 'dijkstra' })}
                className={`py-1.5 px-2 rounded border font-medium transition-colors ${
                  options.shortest_variant === 'dijkstra'
                    ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300'
                    : 'bg-slate-800 border-slate-700 text-slate-400'
                }`}
              >
                Dijkstra (Exact)
              </button>
              <button
                type="button"
                onClick={() => setOptions({ shortest_variant: 'astar' })}
                className={`py-1.5 px-2 rounded border font-medium transition-colors ${
                  options.shortest_variant === 'astar'
                    ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300'
                    : 'bg-slate-800 border-slate-700 text-slate-400'
                }`}
              >
                A* (Euclidean)
              </button>
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>Alternative Routes (k)</span>
              <span className="font-mono text-slate-300">{options.alternatives || 1}</span>
            </div>
            <input
              type="range"
              min={1}
              max={5}
              value={options.alternatives || 3}
              onChange={(e) => setOptions({ alternatives: Number(e.target.value) })}
              className="w-full accent-emerald-400 cursor-pointer"
            />
          </div>
        </div>
      )}

      {algorithm === 'dfs' && (
        <div className="bg-slate-900/60 rounded-lg p-3 border border-slate-700/60 space-y-3 text-xs">
          <div>
            <label className="text-[11px] font-medium text-slate-400 block mb-1">Exploration Mode</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setOptions({ dfs_mode: 'first' })}
                className={`py-1.5 px-2 rounded border font-medium transition-colors ${
                  options.dfs_mode === 'first'
                    ? 'bg-purple-500/20 border-purple-500/50 text-purple-300'
                    : 'bg-slate-800 border-slate-700 text-slate-400'
                }`}
              >
                First Route
              </button>
              <button
                type="button"
                onClick={() => setOptions({ dfs_mode: 'all' })}
                className={`py-1.5 px-2 rounded border font-medium transition-colors ${
                  options.dfs_mode === 'all'
                    ? 'bg-purple-500/20 border-purple-500/50 text-purple-300'
                    : 'bg-slate-800 border-slate-700 text-slate-400'
                }`}
              >
                All Routes
              </button>
            </div>
          </div>

          {options.dfs_mode === 'all' && (
            <div className="space-y-1">
              <div className="flex justify-between text-[11px] text-slate-400">
                <span>Max Paths Cap</span>
                <span className="font-mono text-slate-300">{options.max_paths || 50}</span>
              </div>
              <input
                type="range"
                min={5}
                max={100}
                step={5}
                value={options.max_paths || 50}
                onChange={(e) => setOptions({ max_paths: Number(e.target.value) })}
                className="w-full accent-purple-400 cursor-pointer"
              />
            </div>
          )}

          {isGridAndDfsAll && (
            <div className="p-2.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
              <span>
                Grid graphs contain thousands of nodes causing combinatorial explosion. Switch to the Skeleton strategy for all-paths enumeration.
              </span>
            </div>
          )}
        </div>
      )}

      {/* Compute Route Action Button */}
      <button
        type="button"
        onClick={handleComputeRoute}
        disabled={loading || !graph}
        className="w-full py-2.5 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium text-xs flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/40 transition-colors"
      >
        <Navigation className="w-4 h-4" />
        {loading ? 'Calculating...' : 'Find Evacuation Route'}
      </button>
    </div>
  )
}
