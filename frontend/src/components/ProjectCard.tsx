import type { Project } from '../types'

interface Props {
  project: Project
  onClick: () => void
}

function ProjectCard({ project, onClick }: Props) {
  const statusColors: Record<string, string> = {
    created: 'bg-slate-600',
    analyzing: 'bg-yellow-600',
    editing: 'bg-blue-600',
    previewing: 'bg-purple-600',
    completed: 'bg-green-600',
  }

  return (
    <div
      onClick={onClick}
      className="rounded-lg border border-slate-700 bg-slate-800 p-4 hover:border-slate-500 transition-colors cursor-pointer"
    >
      <div className="flex items-start justify-between mb-3">
        <h4 className="font-semibold">{project.name}</h4>
        <span className={`text-xs px-2 py-0.5 rounded ${statusColors[project.status] || 'bg-slate-600'}`}>
          {project.status}
        </span>
      </div>
      <div className="text-sm text-slate-400 space-y-1">
        <p>Created: {new Date(project.created_at).toLocaleDateString()}</p>
        <div className="flex gap-4">
          <span>Music: {project.music_file ? '✓' : '—'}</span>
          <span>Lyrics: {project.lyrics_file ? '✓' : '—'}</span>
          <span>Clips: {project.clips.length}</span>
        </div>
      </div>
    </div>
  )
}

export default ProjectCard
