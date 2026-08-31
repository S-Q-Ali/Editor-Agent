import { useState } from 'react'
import type { Project } from '../types'

interface Props {
  project: Project
  onClick: () => void
  onDelete: (project: Project) => void
}

function ProjectCard({ project, onClick, onDelete }: Props) {
  const [showConfirm, setShowConfirm] = useState(false)

  const statusColors: Record<string, string> = {
    created: 'bg-slate-600',
    analyzing: 'bg-yellow-600',
    editing: 'bg-blue-600',
    previewing: 'bg-purple-600',
    completed: 'bg-green-600',
  }

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    setShowConfirm(true)
  }

  const confirmDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    onDelete(project)
    setShowConfirm(false)
  }

  const cancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    setShowConfirm(false)
  }

  return (
    <div
      onClick={onClick}
      className="rounded-lg border border-slate-700 bg-slate-800 p-4 hover:border-slate-500 transition-colors cursor-pointer"
    >
      <div className="flex items-start justify-between mb-3">
        <h4 className="font-semibold">{project.name}</h4>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded ${statusColors[project.status] || 'bg-slate-600'}`}>
            {project.status}
          </span>
          <button
            onClick={handleDelete}
            className="text-slate-500 hover:text-red-400 transition-colors p-1"
            title="Delete project"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      </div>
      <div className="text-sm text-slate-400 space-y-1">
        <p>Created: {new Date(project.created_at).toLocaleDateString()}</p>
        <div className="flex gap-4">
          <span>Music: {project.music_file ? '✓' : '—'}</span>
          <span>Lyrics: {project.lyrics_file ? '✓' : '—'}</span>
          <span>Clips: {project.clips.length}</span>
        </div>
      </div>

      {showConfirm && (
        <div className="mt-3 p-3 rounded bg-red-900/30 border border-red-700" onClick={(e) => e.stopPropagation()}>
          <p className="text-sm text-red-300 mb-2">Delete this project? This cannot be undone.</p>
          <div className="flex gap-2">
            <button
              onClick={confirmDelete}
              className="text-xs px-3 py-1 rounded bg-red-600 hover:bg-red-500 text-white"
            >
              Delete
            </button>
            <button
              onClick={cancelDelete}
              className="text-xs px-3 py-1 rounded bg-slate-600 hover:bg-slate-500"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default ProjectCard
