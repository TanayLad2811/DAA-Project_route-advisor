import React, { useRef, useState } from 'react'
import { Upload, FileImage, AlertCircle, CheckCircle2, X } from 'lucide-react'
import { apiClient } from '../api/client'
import { useAppStore } from '../store/useAppStore'

const MAX_SIZE_BYTES = 10 * 1024 * 1024 // 10 MB

export const UploadPanel: React.FC = () => {
  const [dragActive, setDragActive] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const { planId, imageUrl, imageWidth, imageHeight, setPlan, clearPlan, setError } = useAppStore()

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    const file = files[0]
    setErrorMessage(null)

    // Validation
    const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'application/pdf']
    const isPdf = file.name.toLowerCase().endsWith('.pdf')
    const isImage = file.type.startsWith('image/') || isPdf

    if (!isImage && !validTypes.includes(file.type)) {
      const err = 'Unsupported file format. Please upload a PNG, JPG, or PDF.'
      setErrorMessage(err)
      setError(err)
      return
    }

    if (file.size > MAX_SIZE_BYTES) {
      const err = `File exceeds size limit of 10 MB (${(file.size / (1024 * 1024)).toFixed(1)} MB uploaded).`
      setErrorMessage(err)
      setError(err)
      return
    }

    try {
      setUploading(true)
      const response = await apiClient.uploadPlan(file)
      setPlan(response)
      setErrorMessage(null)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed'
      setErrorMessage(msg)
      setError(msg)
    } finally {
      setUploading(false)
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    handleFiles(e.dataTransfer.files)
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files)
  }

  return (
    <div className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-4 shadow-lg backdrop-blur-sm">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <FileImage className="w-4 h-4 text-emerald-400" />
          Floor Plan Upload
        </h2>
        {planId && (
          <button
            onClick={clearPlan}
            className="text-xs text-slate-400 hover:text-rose-400 flex items-center gap-1 transition-colors"
            title="Remove plan"
          >
            <X className="w-3.5 h-3.5" />
            Reset
          </button>
        )}
      </div>

      {!planId ? (
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-all duration-200 ${
            dragActive
              ? 'border-emerald-400 bg-emerald-500/10 scale-[1.01]'
              : 'border-slate-600 hover:border-slate-500 bg-slate-900/50 hover:bg-slate-900/80'
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept="image/png,image/jpeg,image/jpg,application/pdf"
            className="hidden"
            onChange={handleChange}
          />
          <div className="flex flex-col items-center gap-2">
            <div className="p-3 bg-slate-800 rounded-full text-slate-300">
              <Upload className={`w-6 h-6 ${uploading ? 'animate-bounce text-emerald-400' : ''}`} />
            </div>
            {uploading ? (
              <p className="text-sm text-emerald-400 font-medium">Processing floor plan...</p>
            ) : (
              <>
                <p className="text-sm text-slate-200 font-medium">
                  Drop your floor plan here, or <span className="text-emerald-400 underline">browse</span>
                </p>
                <p className="text-xs text-slate-400">
                  PNG, JPG, or PDF (1st page) up to 10 MB
                </p>
                <div className="pt-2">
                  <button
                    type="button"
                    onClick={async (e) => {
                      e.stopPropagation()
                      try {
                        setUploading(true)
                        const resp = await apiClient.loadSample('office_rooms')
                        setPlan(resp)
                      } catch (err: unknown) {
                        const m = err instanceof Error ? err.message : 'Failed to load sample'
                        setErrorMessage(m)
                      } finally {
                        setUploading(false)
                      }
                    }}
                    className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-slate-700 text-[11px] font-medium transition-colors"
                  >
                    ✨ Try Sample Office Plan
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-slate-900/70 border border-slate-700/60 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
              Plan Loaded
            </span>
            <span className="text-xs text-slate-400 font-mono">
              {imageWidth} × {imageHeight} px
            </span>
          </div>
          {imageUrl && (
            <div className="w-full h-24 bg-slate-950 rounded overflow-hidden border border-slate-800 flex items-center justify-center">
              <img
                src={imageUrl}
                alt="Floor plan preview"
                className="max-h-full max-w-full object-contain"
              />
            </div>
          )}
        </div>
      )}

      {errorMessage && (
        <div className="mt-3 p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}
    </div>
  )
}
