import type { PipelineProgressData } from '../hooks/usePipelineProgress'

const STEP_ICONS: Record<string, string> = {
  analyzing_music: '🎵',
  extracting_lyrics: '🎤',
  analyzing_clips: '🎬',
  building_index: '🔍',
  generating_timeline: '⏱',
  rendering_preview: '🖥',
}

const STEP_ORDER = [
  'analyzing_music',
  'extracting_lyrics',
  'analyzing_clips',
  'building_index',
  'generating_timeline',
  'rendering_preview',
]

interface Props {
  progress: PipelineProgressData | null
}

export default function PipelineProgress({ progress }: Props) {
  if (!progress) return null

  return (
    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-200">Pipeline Progress</h3>
        <span className="text-xs text-slate-400">{progress.overall_percent}%</span>
      </div>

      <div className="space-y-2">
        {STEP_ORDER.map((stepKey) => {
          const step = progress.steps[stepKey]
          if (!step) return null

          const icon = STEP_ICONS[stepKey] || '●'
          const isRunning = step.status === 'running'
          const isCompleted = step.status === 'completed'
          const isError = step.status === 'error'

          return (
            <div key={stepKey} className="flex items-center gap-2">
              <span className="text-sm w-5 text-center">
                {isCompleted ? '✓' : isError ? '✗' : icon}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-0.5">
                  <span className={`text-xs ${isRunning ? 'text-white font-medium' : isCompleted ? 'text-green-400' : isError ? 'text-red-400' : 'text-slate-500'}`}>
                    {step.name}
                  </span>
                  <span className={`text-xs ${isRunning ? 'text-blue-400' : isCompleted ? 'text-green-400' : isError ? 'text-red-400' : 'text-slate-600'}`}>
                    {step.percent}%
                  </span>
                </div>
                <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${
                      isError ? 'bg-red-500' : isCompleted ? 'bg-green-500' : 'bg-blue-500'
                    }`}
                    style={{ width: `${step.percent}%` }}
                  />
                </div>
                {step.message && isRunning && (
                  <p className="text-[10px] text-slate-400 mt-0.5 truncate">{step.message}</p>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {progress.done && (
        <div className="mt-3 text-center text-xs text-green-400 font-medium">
          Pipeline Complete!
        </div>
      )}
      {progress.error && (
        <div className="mt-3 text-center text-xs text-red-400 font-medium">
          Error: {progress.error}
        </div>
      )}
    </div>
  )
}
