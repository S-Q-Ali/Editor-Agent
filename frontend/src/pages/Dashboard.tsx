import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { projectApi, healthApi } from '../services/api'
import { useAppStore } from '../stores/appStore'
import type { Project } from '../types'
import ProjectCard from '../components/ProjectCard'
import CreateProjectModal from '../components/CreateProjectModal'

function Dashboard() {
  const navigate = useNavigate()
  const { setCurrentProject } = useAppStore()
  const [projects, setProjects] = useState<Project[]>([])
  const [health, setHealth] = useState<{ ffmpeg: boolean; ffprobe: boolean } | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [projectsRes, healthRes] = await Promise.all([
        projectApi.list(),
        healthApi.check(),
      ])
      setProjects(projectsRes.data)
      setHealth(healthRes.data)
    } catch (err) {
      console.error('Failed to load data:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateProject = async (name: string) => {
    try {
      const res = await projectApi.create(name)
      const project = res.data
      setCurrentProject(project)
      setShowCreateModal(false)
      navigate('/project')
    } catch (err) {
      console.error('Failed to create project:', err)
    }
  }

  const handleDeleteProject = async (project: Project) => {
    try {
      await projectApi.delete(project.path)
      setProjects(projects.filter((p) => p.id !== project.id))
    } catch (err) {
      console.error('Failed to delete project:', err)
    }
  }

  const handleSelectProject = (project: Project) => {
    setCurrentProject(project)
    navigate('/project')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">Loading...</div>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <button
          onClick={() => setShowCreateModal(true)}
          className="rounded-lg bg-blue-600 px-4 py-2 font-medium hover:bg-blue-500 transition-colors"
        >
          New Project
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
          <h3 className="text-lg font-semibold mb-2">System Status</h3>
          {health ? (
            <div className="space-y-1 text-sm">
              <div className="flex items-center gap-2">
                <span className={health.ffmpeg ? 'text-green-400' : 'text-red-400'}>
                  {health.ffmpeg ? '●' : '●'}
                </span>
                FFmpeg {health.ffmpeg ? 'Available' : 'Not Found'}
              </div>
              <div className="flex items-center gap-2">
                <span className={health.ffprobe ? 'text-green-400' : 'text-red-400'}>
                  {health.ffprobe ? '●' : '●'}
                </span>
                FFprobe {health.ffprobe ? 'Available' : 'Not Found'}
              </div>
            </div>
          ) : (
            <p className="text-slate-400 text-sm">Unable to check system</p>
          )}
        </div>

        <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
          <h3 className="text-lg font-semibold mb-2">Projects</h3>
          <p className="text-3xl font-bold">{projects.length}</p>
        </div>

        <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
          <h3 className="text-lg font-semibold mb-2">Quick Start</h3>
          <ol className="text-sm text-slate-400 space-y-1 list-decimal list-inside">
            <li>Create a new project</li>
            <li>Upload music file</li>
            <li>Paste or upload lyrics</li>
            <li>Upload AI video clips</li>
            <li>Click Generate</li>
          </ol>
        </div>
      </div>

      <h3 className="text-xl font-semibold mb-4">Your Projects</h3>
      {projects.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-600 p-12 text-center">
          <p className="text-slate-400 mb-4">No projects yet</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="rounded-lg bg-slate-700 px-4 py-2 hover:bg-slate-600 transition-colors"
          >
            Create Your First Project
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onClick={() => handleSelectProject(project)}
              onDelete={handleDeleteProject}
            />
          ))}
        </div>
      )}

      {showCreateModal && (
        <CreateProjectModal
          onSubmit={handleCreateProject}
          onClose={() => setShowCreateModal(false)}
        />
      )}
    </div>
  )
}

export default Dashboard
