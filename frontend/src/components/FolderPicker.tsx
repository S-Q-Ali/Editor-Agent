import { useState, useEffect } from 'react'
import { fileApi } from '../services/api'

interface FolderPickerProps {
  onSelect: (path: string) => void
  onClose: () => void
  initialPath?: string
}

function FolderPicker({ onSelect, onClose, initialPath }: FolderPickerProps) {
  const [currentPath, setCurrentPath] = useState(initialPath || 'C:\\')
  const [parentPath, setParentPath] = useState<string | null>(null)
  const [directories, setDirectories] = useState<{ name: string; path: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadDirectory(currentPath)
  }, [currentPath])

  const loadDirectory = async (path: string) => {
    setLoading(true)
    setError(null)
    try {
      const response = await fileApi.browse(path)
      setCurrentPath(response.data.current)
      setParentPath(response.data.parent)
      setDirectories(response.data.directories)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load directory'
      setError(message)
      setDirectories([])
    } finally {
      setLoading(false)
    }
  }

  const navigateUp = () => {
    if (parentPath) {
      setCurrentPath(parentPath)
    }
  }

  const navigateInto = (path: string) => {
    setCurrentPath(path)
  }

  const pathSegments = currentPath.replace(/[/\\]$/, '').split(/[/\\]/)

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 rounded-xl border border-slate-600 w-full max-w-lg">
        <div className="p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">Select Export Folder</h3>
            <button onClick={onClose} className="text-slate-400 hover:text-white text-xl">x</button>
          </div>

          {/* Breadcrumb */}
          <div className="flex items-center gap-1 mb-3 text-sm flex-wrap">
            {pathSegments.map((segment, i) => (
              <span key={i} className="flex items-center gap-1">
                {i > 0 && <span className="text-slate-500">/</span>}
                <button
                  onClick={() => setCurrentPath(pathSegments.slice(0, i + 1).join('\\') + '\\')}
                  className="text-blue-400 hover:text-blue-300 hover:underline"
                >
                  {segment}
                </button>
              </span>
            ))}
          </div>

          {/* Navigation */}
          <div className="flex gap-2 mb-3">
            {parentPath && (
              <button
                onClick={navigateUp}
                className="rounded-lg border border-slate-600 bg-slate-700 px-3 py-1.5 text-sm hover:bg-slate-600 transition-colors"
              >
                Up
              </button>
            )}
            <button
              onClick={() => onSelect(currentPath)}
              className="flex-1 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium hover:bg-blue-500 transition-colors"
            >
              Select This Folder
            </button>
          </div>

          {/* Directory list */}
          <div className="rounded-lg border border-slate-600 bg-slate-900/50 max-h-64 overflow-y-auto">
            {loading ? (
              <div className="p-4 text-center text-slate-400 text-sm">Loading...</div>
            ) : error ? (
              <div className="p-4 text-center text-red-400 text-sm">{error}</div>
            ) : directories.length === 0 ? (
              <div className="p-4 text-center text-slate-500 text-sm">No subfolders</div>
            ) : (
              directories.map((dir) => (
                <button
                  key={dir.path}
                  onClick={() => navigateInto(dir.path)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-slate-700/50 transition-colors border-b border-slate-700/50 last:border-b-0"
                >
                  <span className="text-yellow-400">Folder</span>
                  <span className="text-slate-200">{dir.name}</span>
                </button>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default FolderPicker
