import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { projectApi } from '../services/api'
import type { Project } from '../types'

function ProjectPage() {
  const { projectPath } = useParams<{ projectPath: string }>()
  const navigate = useNavigate()
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [pipelineStep, setPipelineStep] = useState<string | null>(null)
  const [lyrics, setLyrics] = useState('')
  const musicInputRef = useRef<HTMLInputElement>(null)
  const clipsInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (projectPath) {
      loadProject(projectPath)
    }
  }, [projectPath])

  const loadProject = async (path: string) => {
    try {
      const res = await projectApi.get(path)
      setProject(res.data)
    } catch (err) {
      console.error('Failed to load project:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleMusicUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !projectPath) return

    const formData = new FormData()
    formData.append('file', file)

    try {
      await fetch(`/api/upload/music/${projectPath}`, {
        method: 'POST',
        body: formData,
      })
      loadProject(projectPath)
    } catch (err) {
      console.error('Upload failed:', err)
    }
  }

  const handleClipsUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || !projectPath) return

    const formData = new FormData()
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i])
    }

    try {
      await fetch(`/api/upload/clips/${projectPath}`, {
        method: 'POST',
        body: formData,
      })
      loadProject(projectPath)
    } catch (err) {
      console.error('Upload failed:', err)
    }
  }

  const handleLyricsSubmit = async () => {
    if (!lyrics.trim() || !projectPath) return

    try {
      await fetch(`/api/analysis/lyrics/${projectPath}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: lyrics, use_whisper: false }),
      })
    } catch (err) {
      console.error('Lyrics submit failed:', err)
    }
  }

  const runPipeline = async () => {
    if (!projectPath) return
    setProcessing(true)

    try {
      setPipelineStep('Analyzing music...')
      await fetch(`/api/analysis/music/${projectPath}`, { method: 'POST' })

      setPipelineStep('Aligning lyrics...')
      if (lyrics.trim()) {
        await handleLyricsSubmit()
      }

      setPipelineStep('Analyzing clips...')
      await fetch(`/api/analysis/clips/${projectPath}`, { method: 'POST' })

      setPipelineStep('Building search index...')
      await fetch(`/api/search/${projectPath}/index`, { method: 'POST' })

      setPipelineStep('Generating timeline...')
      await fetch(`/api/timeline/${projectPath}/generate`, { method: 'POST' })

      setPipelineStep('Rendering preview...')
      await fetch(`/api/render/${projectPath}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preview: true }),
      })

      setPipelineStep('Done!')
      navigate(`/project/${projectPath}/review`)
    } catch (err) {
      console.error('Pipeline failed:', err)
      setPipelineStep('Pipeline failed')
    } finally {
      setProcessing(false)
    }
  }

  if (loading) {
    return <div className="text-center py-12 text-slate-400">Loading project...</div>
  }

  if (!project) {
    return <div className="text-center py-12 text-slate-400">Project not found</div>
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">{project.name}</h2>
        <button
          onClick={() => navigate(`/project/${projectPath}/review`)}
          className="rounded-lg bg-slate-700 px-4 py-2 font-medium hover:bg-slate-600 transition-colors"
        >
          Review
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
          <h3 className="font-semibold mb-3">Music</h3>
          <input
            ref={musicInputRef}
            type="file"
            accept="audio/*"
            onChange={handleMusicUpload}
            className="hidden"
          />
          {project.music_file ? (
            <p className="text-green-400 text-sm">Music uploaded</p>
          ) : (
            <button
              onClick={() => musicInputRef.current?.click()}
              className="w-full rounded-lg border border-dashed border-slate-600 p-4 text-sm text-slate-400 hover:border-slate-400 hover:text-slate-200 transition-colors"
            >
              Upload Music File
            </button>
          )}
        </div>

        <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
          <h3 className="font-semibold mb-3">Lyrics</h3>
          <textarea
            value={lyrics}
            onChange={(e) => setLyrics(e.target.value)}
            placeholder="Paste lyrics here..."
            className="w-full h-32 rounded-lg border border-slate-600 bg-slate-700 px-3 py-2 text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:border-blue-500 resize-none"
          />
        </div>

        <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
          <h3 className="font-semibold mb-3">AI Video Clips</h3>
          <input
            ref={clipsInputRef}
            type="file"
            accept="video/*"
            multiple
            onChange={handleClipsUpload}
            className="hidden"
          />
          <div className="mb-3">
            <p className="text-sm text-slate-400">{project.clips.length} clips uploaded</p>
          </div>
          <button
            onClick={() => clipsInputRef.current?.click()}
            className="w-full rounded-lg border border-dashed border-slate-600 p-4 text-sm text-slate-400 hover:border-slate-400 hover:text-slate-200 transition-colors"
          >
            Upload Video Clips
          </button>
        </div>
      </div>

      <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
        <h3 className="font-semibold mb-3">Pipeline</h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
          {[
            'Music Analysis',
            'Lyrics Alignment',
            'Clip Analysis',
            'Semantic Search',
            'Timeline Generation',
          ].map((step) => (
            <div
              key={step}
              className={`rounded-lg p-3 text-center text-sm ${
                pipelineStep?.toLowerCase().includes(step.split(' ')[0].toLowerCase())
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700'
              }`}
            >
              {step}
            </div>
          ))}
        </div>

        {pipelineStep && (
          <div className="mb-4 text-sm text-slate-300">
            Current: {pipelineStep}
          </div>
        )}

        <button
          onClick={runPipeline}
          disabled={processing}
          className="w-full rounded-lg bg-blue-600 py-3 font-medium hover:bg-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {processing ? 'Processing...' : 'Generate'}
        </button>
      </div>
    </div>
  )
}

export default ProjectPage
