import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'
import { projectApi } from '../services/api'
import type { Project } from '../types'

function getFileName(path: string) {
  return path.split(/[/\\]/).pop() || path
}

function ProjectPage() {
  const navigate = useNavigate()
  const { currentProject, currentProjectPath, setCurrentProject } = useAppStore()
  const [project, setProject] = useState<Project | null>(currentProject)
  const [loading, setLoading] = useState(!currentProject)
  const [processing, setProcessing] = useState(false)
  const [pipelineStep, setPipelineStep] = useState<string | null>(null)
  const [lyrics, setLyrics] = useState('')

  const [musicUploading, setMusicUploading] = useState(false)
  const [musicProgress, setMusicProgress] = useState(0)
  const [clipsUploading, setClipsUploading] = useState(false)
  const [clipsProgress, setClipsProgress] = useState(0)
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const musicInputRef = useRef<HTMLInputElement>(null)
  const clipsInputRef = useRef<HTMLInputElement>(null)

  const projectPath = currentProjectPath

  useEffect(() => {
    if (projectPath && !project) {
      loadProject()
    } else if (!projectPath) {
      navigate('/')
    }
  }, [projectPath])

  useEffect(() => {
    if (uploadSuccess) {
      const t = setTimeout(() => setUploadSuccess(null), 3000)
      return () => clearTimeout(t)
    }
  }, [uploadSuccess])

  useEffect(() => {
    if (uploadError) {
      const t = setTimeout(() => setUploadError(null), 5000)
      return () => clearTimeout(t)
    }
  }, [uploadError])

  const loadProject = async () => {
    if (!projectPath) return
    try {
      const res = await projectApi.get(projectPath)
      setProject(res.data)
      setCurrentProject(res.data)
    } catch (err) {
      console.error('Failed to load project:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleMusicUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !projectPath) return

    setMusicUploading(true)
    setMusicProgress(0)
    setUploadError(null)

    const formData = new FormData()
    formData.append('file', file)

    const xhr = new XMLHttpRequest()
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        setMusicProgress(Math.round((event.loaded / event.total) * 100))
      }
    }
    xhr.onload = () => {
      setMusicUploading(false)
      setMusicProgress(0)
      if (xhr.status >= 200 && xhr.status < 300) {
        setUploadSuccess(`"${file.name}" uploaded successfully`)
        loadProject()
      } else {
        setUploadError('Music upload failed')
      }
    }
    xhr.onerror = () => {
      setMusicUploading(false)
      setMusicProgress(0)
      setUploadError('Music upload failed — check connection')
    }
    xhr.open('POST', `/api/upload/music/${encodeURIComponent(projectPath)}`)
    xhr.send(formData)

    if (musicInputRef.current) musicInputRef.current.value = ''
  }

  const handleClipsUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0 || !projectPath) return

    const fileCount = files.length
    setClipsUploading(true)
    setClipsProgress(0)
    setUploadError(null)

    const formData = new FormData()
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i])
    }

    const xhr = new XMLHttpRequest()
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        setClipsProgress(Math.round((event.loaded / event.total) * 100))
      }
    }
    xhr.onload = () => {
      setClipsUploading(false)
      setClipsProgress(0)
      if (xhr.status >= 200 && xhr.status < 300) {
        setUploadSuccess(`${fileCount} clip${fileCount > 1 ? 's' : ''} uploaded successfully`)
        loadProject()
      } else {
        setUploadError('Clips upload failed')
      }
    }
    xhr.onerror = () => {
      setClipsUploading(false)
      setClipsProgress(0)
      setUploadError('Clips upload failed — check connection')
    }
    xhr.open('POST', `/api/upload/clips/${encodeURIComponent(projectPath)}`)
    xhr.send(formData)

    if (clipsInputRef.current) clipsInputRef.current.value = ''
  }

  const handleLyricsSubmit = async () => {
    if (!lyrics.trim() || !projectPath) return

    try {
      await fetch(`/api/analysis/lyrics/${encodeURIComponent(projectPath)}`, {
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
      await fetch(`/api/analysis/music/${encodeURIComponent(projectPath)}`, { method: 'POST' })

      setPipelineStep('Extracting lyrics from audio...')
      try {
        await fetch(`/api/analysis/lyrics/${encodeURIComponent(projectPath)}/auto`, { method: 'POST' })
      } catch (lyricsErr) {
        console.warn('Auto lyrics extraction failed, continuing without lyrics:', lyricsErr)
      }

      if (lyrics.trim()) {
        setPipelineStep('Aligning custom lyrics...')
        await handleLyricsSubmit()
      }

      setPipelineStep('Analyzing clips...')
      await fetch(`/api/analysis/clips/${encodeURIComponent(projectPath)}`, { method: 'POST' })

      setPipelineStep('Building search index...')
      await fetch(`/api/search/${encodeURIComponent(projectPath)}/index`, { method: 'POST' })

      setPipelineStep('Generating timeline...')
      await fetch(`/api/timeline/${encodeURIComponent(projectPath)}/generate`, { method: 'POST' })

      setPipelineStep('Rendering preview...')
      await fetch(`/api/render/${encodeURIComponent(projectPath)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preview: true }),
      })

      setPipelineStep('Done!')
      navigate('/project/review')
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

  const musicFileName = project.music_file ? getFileName(project.music_file) : null

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">{project.name}</h2>
        <div className="flex gap-3">
          <button
            onClick={() => navigate('/')}
            className="rounded-lg bg-slate-700 px-4 py-2 font-medium hover:bg-slate-600 transition-colors"
          >
            Back
          </button>
          <button
            onClick={() => navigate('/project/review')}
            className="rounded-lg bg-slate-700 px-4 py-2 font-medium hover:bg-slate-600 transition-colors"
          >
            Review
          </button>
        </div>
      </div>

      {(uploadSuccess || uploadError) && (
        <div
          className={`mb-6 rounded-lg px-4 py-3 text-sm font-medium flex items-center justify-between ${
            uploadSuccess
              ? 'bg-green-900/40 border border-green-700 text-green-300'
              : 'bg-red-900/40 border border-red-700 text-red-300'
          }`}
        >
          <span>{uploadSuccess || uploadError}</span>
          <button
            onClick={() => { setUploadSuccess(null); setUploadError(null) }}
            className="ml-4 text-slate-400 hover:text-white"
          >
            x
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {/* Music Card */}
        <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
          <h3 className="font-semibold mb-3">Music</h3>
          <input
            ref={musicInputRef}
            type="file"
            accept="audio/*"
            onChange={handleMusicUpload}
            className="hidden"
          />

          {musicUploading ? (
            <div>
              <p className="text-sm text-slate-300 mb-2 truncate">{musicFileName || 'Uploading...'}</p>
              <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden mb-1">
                <div
                  className="h-full bg-blue-500 transition-all duration-300 ease-out"
                  style={{ width: `${musicProgress}%` }}
                />
              </div>
              <p className="text-xs text-slate-400">{musicProgress}%</p>
            </div>
          ) : musicFileName ? (
            <div>
              <div className="flex items-center gap-2 text-green-400 text-sm mb-3">
                <span className="text-lg">&#10003;</span>
                <span className="truncate">{musicFileName}</span>
              </div>
              <button
                onClick={() => musicInputRef.current?.click()}
                className="w-full rounded-lg border border-dashed border-slate-600 p-3 text-sm text-slate-400 hover:border-slate-400 hover:text-slate-200 transition-colors"
              >
                Replace Music
              </button>
            </div>
          ) : (
            <button
              onClick={() => musicInputRef.current?.click()}
              className="w-full rounded-lg border border-dashed border-slate-600 p-4 text-sm text-slate-400 hover:border-slate-400 hover:text-slate-200 transition-colors"
            >
              Upload Music File
            </button>
          )}
        </div>

        {/* Lyrics Card */}
        <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
          <h3 className="font-semibold mb-3">Lyrics</h3>
          <textarea
            value={lyrics}
            onChange={(e) => setLyrics(e.target.value)}
            placeholder="Paste lyrics here..."
            className="w-full h-32 rounded-lg border border-slate-600 bg-slate-700 px-3 py-2 text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:border-blue-500 resize-none"
          />
        </div>

        {/* Clips Card */}
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

          {clipsUploading ? (
            <div>
              <p className="text-sm text-slate-300 mb-2">Uploading clips...</p>
              <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden mb-1">
                <div
                  className="h-full bg-blue-500 transition-all duration-300 ease-out"
                  style={{ width: `${clipsProgress}%` }}
                />
              </div>
              <p className="text-xs text-slate-400">{clipsProgress}%</p>
            </div>
          ) : project.clips.length > 0 ? (
            <div>
              <div className="flex items-center gap-2 text-green-400 text-sm mb-2">
                <span className="text-lg">&#10003;</span>
                <span>{project.clips.length} clip{project.clips.length > 1 ? 's' : ''} uploaded</span>
              </div>
              <button
                onClick={() => clipsInputRef.current?.click()}
                className="w-full rounded-lg border border-dashed border-slate-600 p-3 text-sm text-slate-400 hover:border-slate-400 hover:text-slate-200 transition-colors"
              >
                Add More Clips
              </button>
            </div>
          ) : (
            <div>
              <p className="text-sm text-slate-400 mb-3">No clips yet</p>
              <button
                onClick={() => clipsInputRef.current?.click()}
                className="w-full rounded-lg border border-dashed border-slate-600 p-4 text-sm text-slate-400 hover:border-slate-400 hover:text-slate-200 transition-colors"
              >
                Upload Video Clips
              </button>
            </div>
          )}
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
