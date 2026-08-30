import { useState } from 'react'
import type { TimelineEvent } from '../types'

interface Props {
  events: TimelineEvent[]
  duration: number
  currentTime: number
  onSelect: (event: TimelineEvent) => void
  selectedEvent: TimelineEvent | null
}

function TimelineViewer({ events, duration, currentTime, onSelect, selectedEvent }: Props) {
  const [zoom, setZoom] = useState(1)

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    const ms = Math.floor((seconds % 1) * 100)
    return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`
  }

  const pixelsPerSecond = 50 * zoom

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">Timeline</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setZoom(Math.max(0.25, zoom - 0.25))}
            className="rounded bg-slate-700 px-2 py-1 text-sm hover:bg-slate-600"
          >
            -
          </button>
          <span className="text-sm text-slate-400">{zoom}x</span>
          <button
            onClick={() => setZoom(Math.min(4, zoom + 0.25))}
            className="rounded bg-slate-700 px-2 py-1 text-sm hover:bg-slate-600"
          >
            +
          </button>
        </div>
      </div>

      <div className="mb-2 flex items-center gap-4 text-sm text-slate-400">
        <span>Duration: {formatTime(duration)}</span>
        <span>Events: {events.length}</span>
        <span>Current: {formatTime(currentTime)}</span>
      </div>

      <div className="relative overflow-x-auto border border-slate-600 rounded bg-slate-900">
        <div
          className="relative h-32"
          style={{ width: `${duration * pixelsPerSecond}px`, minWidth: '100%' }}
        >
          <div className="absolute inset-0 flex">
            {Array.from({ length: Math.ceil(duration) + 1 }, (_, i) => (
              <div
                key={i}
                className="border-l border-slate-700 h-full"
                style={{ width: `${pixelsPerSecond}px`, minWidth: '1px' }}
              >
                {i % 5 === 0 && (
                  <span className="text-xs text-slate-500 ml-1">{formatTime(i)}</span>
                )}
              </div>
            ))}
          </div>

          <div className="absolute top-8 left-0 right-0 h-16">
            {events.map((event, i) => {
              const left = event.timeline_start * pixelsPerSecond
              const width = (event.timeline_end - event.timeline_start) * pixelsPerSecond
              const isSelected = selectedEvent?.clip_id === event.clip_id &&
                                 selectedEvent?.timeline_start === event.timeline_start

              return (
                <div
                  key={i}
                  onClick={() => onSelect(event)}
                  className={`absolute top-0 h-full rounded cursor-pointer border transition-colors ${
                    isSelected
                      ? 'bg-blue-600 border-blue-400'
                      : 'bg-slate-600 border-slate-500 hover:bg-slate-500'
                  }`}
                  style={{ left: `${left}px`, width: `${Math.max(width, 4)}px` }}
                  title={`${event.clip_id}: ${event.lyric_text}`}
                >
                  {width > 60 && (
                    <div className="px-1 py-0.5 text-xs truncate">
                      {event.clip_id}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          <div
            className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-10"
            style={{ left: `${currentTime * pixelsPerSecond}px` }}
          />
        </div>
      </div>
    </div>
  )
}

export default TimelineViewer
