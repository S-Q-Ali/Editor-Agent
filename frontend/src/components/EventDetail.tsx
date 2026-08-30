import type { TimelineEvent } from '../types'

interface Props {
  event: TimelineEvent
  onClose: () => void
  onReplace?: (clipId: string) => void
}

function EventDetail({ event, onClose, onReplace }: Props) {
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

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-slate-400">Source Range</label>
            <p className="font-mono text-sm">
              {formatTime(event.source_start)} - {formatTime(event.source_end)}
            </p>
          </div>
          <div>
            <label className="text-sm text-slate-400">Timeline Range</label>
            <p className="font-mono text-sm">
              {formatTime(event.timeline_start)} - {formatTime(event.timeline_end)}
            </p>
          </div>
        </div>

        <div>
          <label className="text-sm text-slate-400">Duration</label>
          <p className="font-medium">
            {formatTime(event.timeline_end - event.timeline_start)}
          </p>
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
