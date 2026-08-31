import { useState } from 'react'
import type { TimelineEvent } from '../types'
import { timelineApi } from '../services/api'

interface Props {
  event: TimelineEvent
  eventIndex: number
  projectPath: string
  onClose: () => void
  onReplace?: (clipId: string) => void
  onUpdated?: () => void
}

function EventDetail({ event, eventIndex, projectPath, onClose, onReplace, onUpdated }: Props) {
  const [sourceStart, setSourceStart] = useState(event.source_start)
  const [sourceEnd, setSourceEnd] = useState(event.source_end)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    const ms = Math.floor((seconds % 1) * 100)
    return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`
  }

  const confidenceColor = event.confidence > 0.7
    ? 'text-green-400'
    : event.confidence > 0.4
    ? 'text-yellow-400'
    : 'text-red-400'

  const methodColor: Record<string, string> = {
    sequential: 'bg-blue-600',
    clip_match: 'bg-green-600',
    best_available: 'bg-yellow-600',
    hard_fallback: 'bg-red-600',
    manual_override: 'bg-purple-600',
  }

  const handleSaveRange = async () => {
    setSaving(true)
    try {
      await timelineApi.patchEvent(projectPath, eventIndex, {
        source_start: sourceStart,
        source_end: sourceEnd,
      })
      setSaved(true)
      onUpdated?.()
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      console.error('Failed to update event:', err)
    } finally {
      setSaving(false)
    }
  }

  const hasChanges = sourceStart !== event.source_start || sourceEnd !== event.source_end

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">Clip Details</h3>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white"
        >
          x
        </button>
      </div>

      <div className="space-y-3">
        <div>
          <label className="text-sm text-slate-400">Clip ID</label>
          <p className="font-medium">{event.clip_id}</p>
        </div>

        <div>
          <label className="text-sm text-slate-400">Lyric Line</label>
          <p className="font-medium italic">"{event.lyric_text}"</p>
        </div>

        {event.clip_caption && (
          <div>
            <label className="text-sm text-slate-400 flex items-center gap-1.5">
              BLIP Caption
              <span className="text-[10px] bg-slate-600 px-1.5 py-0.5 rounded font-mono">AI</span>
            </label>
            <p className="text-sm text-slate-300 italic mt-0.5">"{event.clip_caption}"</p>
          </div>
        )}

        <div>
          <label className="text-sm text-slate-400">Selection Method</label>
          <div className="flex items-center gap-2 mt-1">
            <span className={`inline-block w-2 h-2 rounded-full ${methodColor[event.selection_method] || 'bg-slate-500'}`} />
            <span className="text-sm font-medium">{event.selection_method || 'unknown'}</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-slate-400">Source Start</label>
            <input
              type="number"
              step="0.1"
              min="0"
              value={sourceStart}
              onChange={(e) => setSourceStart(parseFloat(e.target.value) || 0)}
              className="w-full mt-1 rounded bg-slate-700 border border-slate-600 px-2 py-1 text-sm font-mono focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="text-sm text-slate-400">Source End</label>
            <input
              type="number"
              step="0.1"
              min="0"
              value={sourceEnd}
              onChange={(e) => setSourceEnd(parseFloat(e.target.value) || 0)}
              className="w-full mt-1 rounded bg-slate-700 border border-slate-600 px-2 py-1 text-sm font-mono focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        <div>
          <label className="text-sm text-slate-400">Source Duration</label>
          <p className="font-mono text-sm">{formatTime(sourceEnd - sourceStart)}</p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-slate-400">Timeline Range</label>
            <p className="font-mono text-sm">
              {formatTime(event.timeline_start)} - {formatTime(event.timeline_end)}
            </p>
          </div>
          <div>
            <label className="text-sm text-slate-400">Timeline Duration</label>
            <p className="font-mono text-sm">
              {formatTime(event.timeline_end - event.timeline_start)}
            </p>
          </div>
        </div>

        <div>
          <label className="text-sm text-slate-400">Transition</label>
          <p className="font-medium capitalize">{event.transition}</p>
        </div>

        <div>
          <label className="text-sm text-slate-400">Confidence</label>
          <p className={`font-medium ${confidenceColor}`}>
            {(event.confidence * 100).toFixed(1)}%
          </p>
          <div className="w-full h-2 bg-slate-700 rounded mt-1">
            <div
              className={`h-full rounded ${
                event.confidence > 0.7 ? 'bg-green-500' :
                event.confidence > 0.4 ? 'bg-yellow-500' : 'bg-red-500'
              }`}
              style={{ width: `${event.confidence * 100}%` }}
            />
          </div>
        </div>

        <div>
          <label className="text-sm text-slate-400">Reason</label>
          <p className="text-sm">{event.reason}</p>
        </div>

        {hasChanges && (
          <button
            onClick={handleSaveRange}
            disabled={saving}
            className={`w-full rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              saved
                ? 'bg-green-600 text-white'
                : 'bg-blue-600 hover:bg-blue-500 text-white'
            } disabled:opacity-50`}
          >
            {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Range Override'}
          </button>
        )}

        {onReplace && (
          <button
            onClick={() => onReplace(event.clip_id)}
            className="w-full rounded-lg border border-slate-600 px-4 py-2 text-sm hover:bg-slate-700 transition-colors"
          >
            Replace Clip
          </button>
        )}
      </div>
    </div>
  )
}

export default EventDetail
