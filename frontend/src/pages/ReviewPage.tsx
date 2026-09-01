import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '../stores/appStore'
import { renderApi } from '../services/api'
import type { TimelineEvent, QCResult, CaptionTemplate, FileEstimate } from '../types'
import TimelineViewer from '../components/TimelineViewer'
import VideoPlayer from '../components/VideoPlayer'
import EventDetail from '../components/EventDetail'
import RevisionInput from '../components/RevisionInput'
import QCDisplay from '../components/QCDisplay'

const CAPTION_TEMPLATE_PREVIEWS: Record<string, { style: string; sample: string }> = {
  subtitle: { style: 'text-sm text-white border-b-2 border-white pb-0.5', sample: 'Aa' },
  karaoke: { style: 'text-lg text-yellow-400 font-bold drop-shadow-lg', sample: 'Aa' },
  kids_bubble: { style: 'text-sm text-white bg-black/50 px-2 py-0.5 rounded-lg', sample: 'Aa' },
  minimal: { style: 'text-xs text-white/70', sample: 'Aa' },
  bold_center: { style: 'text-xl text-white font-bold drop-shadow-xl', sample: 'Aa' },
  colorful: { style: 'text-base text-yellow-300 font-bold', sample: 'Aa' },
}

const QUALITY_PRESETS = [
  { id: 'lossless', crf: 0, preset: 'slow', label: 'Lossless', desc: 'Zero quality loss', size: '~1-2GB/min' },
  { id: 'visually_lossless', crf: 18, preset: 'slow', label: 'Visually Lossless', desc: 'Indistinguishable', size: '~500MB/min' },
  { id: 'balanced', crf: 23, preset: 'medium', label: 'Balanced', desc: 'Great quality', size: '~150MB/min' },
  { id: 'compact', crf: 28, preset: 'fast', label: 'Compact', desc: 'Smaller files', size: '~50MB/min' },
]

const AUDIO_QUALITY_PRESETS = [
  { id: 'lossless', codec: 'flac', bitrate: 'N/A', label: 'Lossless (FLAC)', desc: 'Zero loss' },
  { id: 'high', codec: 'aac', bitrate: '320k', label: 'High (AAC 320k)', desc: 'Near-lossless' },
  { id: 'standard', codec: 'aac', bitrate: '192k', label: 'Standard (AAC 192k)', desc: 'Great' },
]

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
  const [finalReady, setFinalReady] = useState(false)

  const [captionsEnabled, setCaptionsEnabled] = useState(true)
  const [captionTemplate, setCaptionTemplate] = useState('subtitle')
  const [captionFontsize, setCaptionFontsize] = useState(24)
  const [captionFontcolor, setCaptionFontcolor] = useState('')
  const [templates, setTemplates] = useState<CaptionTemplate[]>([])

  const [showExport, setShowExport] = useState(false)
  const [exportResolution, setExportResolution] = useState('1080p')
  const [exportQuality, setExportQuality] = useState('balanced')
  const [exportCodec, setExportCodec] = useState('h264')
  const [exportFps, setExportFps] = useState(30)
  const [exportContainer, setExportContainer] = useState('mp4')
  const [audioQuality, setAudioQuality] = useState('standard')
  const [exportPath, setExportPath] = useState('')
  const [estimate, setEstimate] = useState<FileEstimate | null>(null)
  const [estimating, setEstimating] = useState(false)

  useEffect(() => {
    if (!projectPath) {
      navigate('/')
      return
    }
    loadTimeline()
    checkForPreview()
    checkForFinal()
    loadTemplates()
  }, [projectPath])

  const loadTemplates = async () => {
    try {
      const response = await fetch('/api/render/captions/templates')
      if (response.ok) {
        const data = await response.json()
        setTemplates(data.templates || [])
      }
    } catch (err) {
      console.error('Failed to load caption templates:', err)
    }
  }

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

  const checkForFinal = async () => {
    if (!projectPath) return
    try {
      const response = await fetch(`/api/render/${encodeURIComponent(projectPath)}/status`)
      if (response.ok) {
        const data = await response.json()
        const final = data.renders?.find((r: { filename: string }) =>
          r.filename.startsWith('final.')
        )
        setFinalReady(!!final)
      }
    } catch (err) {
      console.error('Failed to check final:', err)
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

  const getAudioSettings = useCallback(() => {
    const preset = AUDIO_QUALITY_PRESETS.find(p => p.id === audioQuality)
    return preset || AUDIO_QUALITY_PRESETS[2]
  }, [audioQuality])

  const getVideoSettings = useCallback(() => {
    const preset = QUALITY_PRESETS.find(p => p.id === exportQuality)
    return preset || QUALITY_PRESETS[2]
  }, [exportQuality])

  const fetchEstimate = useCallback(async () => {
    if (!projectPath) return
    setEstimating(true)
    try {
      const vs = getVideoSettings()
      const as = getAudioSettings()
      const response = await renderApi.estimate(projectPath, {
        crf: vs.crf,
        resolution: exportResolution,
        audio_bitrate: as.bitrate,
        audio_codec: as.codec,
      })
      setEstimate(response.data)
    } catch (err) {
      console.error('Failed to estimate:', err)
    } finally {
      setEstimating(false)
    }
  }, [projectPath, exportResolution, exportQuality, audioQuality, getVideoSettings, getAudioSettings])

  useEffect(() => {
    if (showExport && projectPath) {
      fetchEstimate()
    }
  }, [showExport, exportResolution, exportQuality, audioQuality])

  const handleExport = async () => {
    if (!projectPath) return
    setRendering(true)
    try {
      const vs = getVideoSettings()
      const as = getAudioSettings()
      const response = await fetch(`/api/render/${encodeURIComponent(projectPath)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preview: false,
          caption_template: captionsEnabled ? captionTemplate : 'none',
          caption_fontsize: captionFontsize,
          caption_fontcolor: captionFontcolor || undefined,
          resolution: exportResolution,
          crf: vs.crf,
          preset: vs.preset,
          codec: exportCodec,
          fps: exportFps,
          container: exportContainer,
          audio_codec: as.codec,
          audio_bitrate: as.bitrate,
          audio_sample_rate: 48000,
          audio_channels: 2,
          export_path: exportPath || undefined,
        }),
      })
      if (response.ok) {
        setFinalReady(true)
        setShowExport(false)
      }
    } catch (err) {
      console.error('Failed to export:', err)
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
        <h2 className="text-2xl font-bold">Review & Export</h2>
        <div className="flex gap-3">
          {finalReady && (
            <a
              href={projectPath ? renderApi.downloadUrl(projectPath) : '#'}
              download
              className="rounded-lg bg-green-600 px-4 py-2 font-medium hover:bg-green-500 transition-colors inline-flex items-center gap-2"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
              Download
            </a>
          )}
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
            Back
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
          {/* Caption Settings */}
          <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
            <h3 className="font-semibold mb-3">Captions</h3>

            <label className="flex items-center gap-2 cursor-pointer mb-3">
              <input
                type="checkbox"
                checked={captionsEnabled}
                onChange={(e) => setCaptionsEnabled(e.target.checked)}
                className="rounded text-blue-500"
              />
              <span className="text-sm font-medium">Enable Captions</span>
            </label>

            {captionsEnabled && (
              <>
                <label className="text-sm text-slate-400 mb-2 block">Style</label>
                <div className="grid grid-cols-2 gap-2 mb-3">
                  {templates.filter(t => t.id !== 'none').map((t) => (
                    <button
                      key={t.id}
                      onClick={() => setCaptionTemplate(t.id)}
                      className={`rounded-lg border p-2 text-left transition-colors ${
                        captionTemplate === t.id
                          ? 'border-blue-500 bg-blue-900/30'
                          : 'border-slate-600 hover:border-slate-500'
                      }`}
                    >
                      <div className="text-xs font-medium">{t.label}</div>
                      <div className={`mt-1 ${CAPTION_TEMPLATE_PREVIEWS[t.id]?.style || ''}`}>
                        {CAPTION_TEMPLATE_PREVIEWS[t.id]?.sample || 'Aa'}
                      </div>
                    </button>
                  ))}
                </div>

                <div className="mb-3">
                  <label className="text-sm text-slate-400 mb-1 block">Font Size: {captionFontsize}px</label>
                  <input
                    type="range"
                    min="16"
                    max="72"
                    value={captionFontsize}
                    onChange={(e) => setCaptionFontsize(parseInt(e.target.value))}
                    className="w-full accent-blue-500"
                  />
                </div>

                <div className="mb-3">
                  <label className="text-sm text-slate-400 mb-1 block">Font Color</label>
                  <select
                    value={captionFontcolor}
                    onChange={(e) => setCaptionFontcolor(e.target.value)}
                    className="w-full rounded-lg border border-slate-600 bg-slate-700 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500"
                  >
                    <option value="">Default</option>
                    <option value="white">White</option>
                    <option value="yellow">Yellow</option>
                    <option value="cyan">Cyan</option>
                    <option value="lightgreen">Light Green</option>
                    <option value="magenta">Magenta</option>
                    <option value="red">Red</option>
                  </select>
                </div>
              </>
            )}
          </div>

          {selectedEvent && (
            <EventDetail
              event={selectedEvent}
              eventIndex={events.findIndex(
                (e) => e.clip_id === selectedEvent.clip_id && e.timeline_start === selectedEvent.timeline_start
              )}
              projectPath={projectPath || ''}
              onClose={() => setSelectedEvent(null)}
              onReplace={(clipId) => console.log('Replace clip:', clipId)}
              onUpdated={loadTimeline}
            />
          )}

          <RevisionInput
            onSubmit={handleRevision}
            disabled={rendering}
          />

          {/* Export Button */}
          <button
            onClick={() => setShowExport(true)}
            className="w-full rounded-lg bg-blue-600 py-3 font-medium hover:bg-blue-500 transition-colors"
          >
            Open Export Settings
          </button>
        </div>
      </div>

      {/* Export Settings Modal */}
      {showExport && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-xl border border-slate-600 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold">Export Settings</h2>
                <button onClick={() => setShowExport(false)} className="text-slate-400 hover:text-white text-xl">x</button>
              </div>

              {/* Export Path */}
              <div className="mb-6">
                <label className="text-sm text-slate-400 mb-1 block">Export To (optional)</label>
                <input
                  type="text"
                  value={exportPath}
                  onChange={(e) => setExportPath(e.target.value)}
                  placeholder="Default: project/renders/final.{container}"
                  className="w-full rounded-lg border border-slate-600 bg-slate-700 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
              </div>

              {/* VIDEO Section */}
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-2 h-2 rounded-full bg-blue-500" />
                  <h3 className="font-semibold text-blue-400">VIDEO</h3>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="text-sm text-slate-400 mb-1 block">Format</label>
                    <select
                      value={exportContainer}
                      onChange={(e) => setExportContainer(e.target.value)}
                      className="w-full rounded-lg border border-slate-600 bg-slate-700 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500"
                    >
                      <option value="mp4">MP4</option>
                      <option value="webm">WebM</option>
                      <option value="mkv">MKV</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm text-slate-400 mb-1 block">Resolution</label>
                    <select
                      value={exportResolution}
                      onChange={(e) => setExportResolution(e.target.value)}
                      className="w-full rounded-lg border border-slate-600 bg-slate-700 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500"
                    >
                      <option value="4k">4K (3840x2160)</option>
                      <option value="1080p">1080p (1920x1080)</option>
                      <option value="720p">720p (1280x720)</option>
                      <option value="480p">480p (854x480)</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm text-slate-400 mb-1 block">Codec</label>
                    <select
                      value={exportCodec}
                      onChange={(e) => setExportCodec(e.target.value)}
                      className="w-full rounded-lg border border-slate-600 bg-slate-700 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500"
                    >
                      <option value="h264">H.264</option>
                      <option value="h265">H.265 / HEVC</option>
                      <option value="av1">AV1</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm text-slate-400 mb-1 block">FPS</label>
                    <select
                      value={exportFps}
                      onChange={(e) => setExportFps(parseInt(e.target.value))}
                      className="w-full rounded-lg border border-slate-600 bg-slate-700 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500"
                    >
                      <option value={24}>24 fps</option>
                      <option value={25}>25 fps</option>
                      <option value={30}>30 fps</option>
                      <option value={60}>60 fps</option>
                    </select>
                  </div>
                </div>

                <label className="text-sm text-slate-400 mb-2 block">Quality</label>
                <div className="grid grid-cols-4 gap-2">
                  {QUALITY_PRESETS.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setExportQuality(p.id)}
                      className={`rounded-lg border p-2 text-left transition-colors ${
                        exportQuality === p.id
                          ? 'border-blue-500 bg-blue-900/30'
                          : 'border-slate-600 hover:border-slate-500'
                      }`}
                    >
                      <div className="text-xs font-medium">{p.label}</div>
                      <div className="text-[10px] text-slate-500">CRF {p.crf}</div>
                      <div className="text-[10px] text-slate-500">{p.size}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* AUDIO Section */}
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-2 h-2 rounded-full bg-green-500" />
                  <h3 className="font-semibold text-green-400">AUDIO</h3>
                </div>

                <label className="text-sm text-slate-400 mb-2 block">Quality</label>
                <div className="grid grid-cols-3 gap-2">
                  {AUDIO_QUALITY_PRESETS.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setAudioQuality(p.id)}
                      className={`rounded-lg border p-2 text-left transition-colors ${
                        audioQuality === p.id
                          ? 'border-green-500 bg-green-900/30'
                          : 'border-slate-600 hover:border-slate-500'
                      }`}
                    >
                      <div className="text-xs font-medium">{p.label}</div>
                      <div className="text-[10px] text-slate-500">{p.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* File Size Estimate */}
              <div className="rounded-lg bg-slate-700/50 p-4 mb-6">
                <h4 className="text-sm font-medium mb-2">Estimated File Size</h4>
                {estimating ? (
                  <p className="text-sm text-slate-400">Calculating...</p>
                ) : estimate ? (
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-slate-400">Video</span>
                      <p className="font-medium">{estimate.video_mb} MB</p>
                    </div>
                    <div>
                      <span className="text-slate-400">Audio</span>
                      <p className="font-medium">{estimate.audio_mb} MB</p>
                    </div>
                    <div>
                      <span className="text-slate-400">Total</span>
                      <p className="font-bold text-blue-400">{estimate.total_mb} MB</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-slate-400">—</p>
                )}
                <p className="text-[10px] text-slate-500 mt-2">Duration: {Math.floor(duration / 60)}:{String(Math.floor(duration % 60)).padStart(2, '0')}</p>
              </div>

              {/* Export Button */}
              <button
                onClick={handleExport}
                disabled={rendering}
                className="w-full rounded-lg bg-blue-600 py-3 font-medium hover:bg-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {rendering ? 'Exporting...' : 'Start Export'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ReviewPage
