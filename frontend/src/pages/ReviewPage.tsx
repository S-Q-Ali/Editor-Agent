import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'
import type { TimelineEvent, QCResult } from '../types'
import TimelineViewer from '../components/TimelineViewer'
import VideoPlayer from '../components/VideoPlayer'
import EventDetail from '../components/EventDetail'
import RevisionInput from '../components/RevisionInput'
import QCDisplay from '../components/QCDisplay'
import ApprovalGate from '../components/ApprovalGate'

function ReviewPage() {
  const navigate = useNavigate()
  const { currentProjectPath } = useAppStore()
  const projectPath = currentProjectPath
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [duration, setDuration] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)
  const [selectedEvent, setSelectedEvent] = useState<TimelineEvent | null>(null)
  const [qcResult, setQcResult] = useState<QCResult | null>(null)
  const [videoSrc, setVideoSrc] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [qcLoading, setQcLoading] = useState(false)
  const [rendering, setRendering] = useState(false)

  useEffect(() => {
    if (!projectPath) {
      navigate('/')
      return
    }
    loadTimeline()
    checkForPreview()
  }, [projectPath])

  const loadTimeline = async () => {
    if (!projectPath) return
    try {
      const response = await fetch(`/api/timeline/${encodeURIComponent(projectPath)}`)
      if (response.ok) {
        const data = await response.json()
        setEvents(data.tracks?.video || [])
        setDuration(data.duration || 0)
      }
    } catch (err) {
      console.error('Failed to load timeline:', err)
    } finally {
      setLoading(false)
    }
  }

  const checkForPreview = async () => {
    if (!projectPath) return
    try {
      const response = await fetch(`/api/render/${encodeURIComponent(projectPath)}/status`)
      if (response.ok) {
        const data = await response.json()
        const preview = data.renders?.find((r: { filename: string }) =>
          r.filename === 'preview.mp4'
        )
        if (preview) {
          setVideoSrc(`/api/files/${encodeURIComponent(projectPath)}/renders/preview.mp4`)
        }
      }
    } catch (err) {
      console.error('Failed to check preview:', err)
    }
  }

  const runQC = async () => {
    if (!projectPath) return
    setQcLoading(true)
    try {
      const response = await fetch(`/api/qc/${encodeURIComponent(projectPath)}`, { method: 'POST' })
      if (response.ok) {
        const data = await response.json()
        setQcResult(data)
      }
    } catch (err) {
      console.error('Failed to run QC:', err)
    } finally {
      setQcLoading(false)
    }
  }

  const handleRevision = async (instruction: string) => {
    if (!projectPath) return
    try {
      const response = await fetch(`/api/revision/${encodeURIComponent(projectPath)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction }),
      })
      if (response.ok) {
        await loadTimeline()
        setQcResult(null)
      }
    } catch (err) {
      console.error('Failed to apply revision:', err)
    }
  }

  const handleApprove = async () => {
    if (!projectPath) return
    setRendering(true)
    try {
      const response = await fetch(`/api/render/${encodeURIComponent(projectPath)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preview: false }),
      })
      if (response.ok) {
        const data = await response.json()
        console.log('Final render complete:', data)
      }
    } catch (err) {
      console.error('Failed to render final:', err)
    } finally {
      setRendering(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">Loading timeline...</div>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Review & Approve</h2>
        <div className="flex gap-3">
          <button
            onClick={runQC}
            disabled={qcLoading}
            className="rounded-lg bg-slate-700 px-4 py-2 font-medium hover:bg-slate-600 transition-colors disabled:opacity-50"
          >
            {qcLoading ? 'Running QC...' : 'Run QC'}
          </button>
          <button
            onClick={() => navigate('/project')}
            className="rounded-lg bg-slate-700 px-4 py-2 font-medium hover:bg-slate-600 transition-colors"
          >
            Back to Project
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <VideoPlayer
            src={videoSrc}
            onTimeUpdate={setCurrentTime}
          />

          <TimelineViewer
            events={events}
            duration={duration}
            currentTime={currentTime}
            onSelect={setSelectedEvent}
            selectedEvent={selectedEvent}
          />

          <QCDisplay result={qcResult} loading={qcLoading} />
        </div>

        <div className="space-y-6">
          {selectedEvent && (
            <EventDetail
              event={selectedEvent}
              onClose={() => setSelectedEvent(null)}
              onReplace={(clipId) => console.log('Replace clip:', clipId)}
            />
          )}

          <RevisionInput
            onSubmit={handleRevision}
            disabled={rendering}
          />

          <ApprovalGate
            qcScore={qcResult?.score ?? 0}
            hasWarnings={(qcResult?.warnings?.length ?? 0) > 0}
            hasErrors={(qcResult?.errors?.length ?? 0) > 0}
            onApprove={handleApprove}
            onRevise={() => handleRevision('Please revise the timeline')}
            loading={rendering}
          />
        </div>
      </div>
    </div>
  )
}

export default ReviewPage
