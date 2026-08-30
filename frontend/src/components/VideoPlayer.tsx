import { useState, useRef, useEffect } from 'react'

interface Props {
  src: string | null
  onTimeUpdate?: (time: number) => void
  onEnded?: () => void
}

function VideoPlayer({ src, onTimeUpdate, onEnded }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [playing, setPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(1)

  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime)
      onTimeUpdate?.(video.currentTime)
    }

    const handleLoadedMetadata = () => {
      setDuration(video.duration)
    }

    const handleEnded = () => {
      setPlaying(false)
      onEnded?.()
    }

    video.addEventListener('timeupdate', handleTimeUpdate)
    video.addEventListener('loadedmetadata', handleLoadedMetadata)
    video.addEventListener('ended', handleEnded)

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate)
      video.removeEventListener('loadedmetadata', handleLoadedMetadata)
      video.removeEventListener('ended', handleEnded)
    }
  }, [onTimeUpdate, onEnded])

  const togglePlay = () => {
    const video = videoRef.current
    if (!video) return

    if (playing) {
      video.pause()
    } else {
      video.play()
    }
    setPlaying(!playing)
  }

  const seek = (time: number) => {
    const video = videoRef.current
    if (!video) return
    video.currentTime = time
    setCurrentTime(time)
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  if (!src) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800 p-8 flex items-center justify-center">
        <p className="text-slate-400">No video loaded</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 overflow-hidden">
      <video
        ref={videoRef}
        src={src}
        className="w-full aspect-video bg-black"
        onClick={togglePlay}
      />

      <div className="p-4">
        <div className="mb-3">
          <input
            type="range"
            min={0}
            max={duration || 0}
            value={currentTime}
            onChange={(e) => seek(parseFloat(e.target.value))}
            className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={togglePlay}
              className="rounded-lg bg-blue-600 px-4 py-2 font-medium hover:bg-blue-500 transition-colors"
            >
              {playing ? 'Pause' : 'Play'}
            </button>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setVolume(Math.max(0, volume - 0.1))}
                className="text-slate-400 hover:text-white"
              >
                -
              </button>
              <input
                type="range"
                min={0}
                max={1}
                step={0.1}
                value={volume}
                onChange={(e) => {
                  const v = parseFloat(e.target.value)
                  setVolume(v)
                  if (videoRef.current) videoRef.current.volume = v
                }}
                className="w-20 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              <button
                onClick={() => setVolume(Math.min(1, volume + 0.1))}
                className="text-slate-400 hover:text-white"
              >
                +
              </button>
            </div>
          </div>

          <div className="text-sm text-slate-400">
            {formatTime(currentTime)} / {formatTime(duration)}
          </div>
        </div>
      </div>
    </div>
  )
}

export default VideoPlayer
