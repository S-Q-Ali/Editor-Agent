import { useState, useEffect } from 'react'

function UpdateNotification() {
  const [updateState, setUpdateState] = useState<
    'checking' | 'available' | 'downloading' | 'downloaded' | null
  >(null)
  const [version, setVersion] = useState('')
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (!window.electronAPI) return

    window.electronAPI.onUpdateAvailable((v) => {
      setVersion(v)
      setUpdateState('available')
    })

    window.electronAPI.onUpdateProgress((p) => {
      setProgress(p)
      setUpdateState('downloading')
    })

    window.electronAPI.onUpdateDownloaded(() => {
      setUpdateState('downloaded')
    })
  }, [])

  if (!window.electronAPI || !updateState) return null

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {updateState === 'available' && (
        <div className="rounded-lg bg-blue-900/90 border border-blue-700 px-4 py-3 text-sm shadow-lg">
          <p className="font-medium text-blue-200">Update Available</p>
          <p className="text-blue-300 text-xs mt-1">Version {version} is being downloaded...</p>
        </div>
      )}

      {updateState === 'downloading' && (
        <div className="rounded-lg bg-blue-900/90 border border-blue-700 px-4 py-3 text-sm shadow-lg">
          <p className="font-medium text-blue-200">Downloading Update...</p>
          <div className="w-48 h-1.5 bg-blue-800 rounded mt-2">
            <div
              className="h-full bg-blue-400 rounded transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-blue-300 text-xs mt-1">{progress}%</p>
        </div>
      )}

      {updateState === 'downloaded' && (
        <div className="rounded-lg bg-green-900/90 border border-green-700 px-4 py-3 text-sm shadow-lg">
          <p className="font-medium text-green-200">Update Ready!</p>
          <p className="text-green-300 text-xs mt-1">Version {version}</p>
          <button
            onClick={() => window.electronAPI?.installUpdate()}
            className="mt-2 rounded bg-green-600 px-3 py-1 text-xs font-medium hover:bg-green-500 transition-colors"
          >
            Restart & Install
          </button>
        </div>
      )}
    </div>
  )
}

export default UpdateNotification
