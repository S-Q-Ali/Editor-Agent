interface QCResult {
  score: number
  warnings: string[]
  errors: string[]
}

interface Props {
  result: QCResult | null
  loading?: boolean
}

function QCDisplay({ result, loading }: Props) {
  if (loading) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
        <h3 className="font-semibold mb-3">Quality Control</h3>
        <div className="text-center py-4 text-slate-400">Running QC checks...</div>
      </div>
    )
  }

  if (!result) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
        <h3 className="font-semibold mb-3">Quality Control</h3>
        <div className="text-center py-4 text-slate-400">No QC results yet</div>
      </div>
    )
  }

  const scoreColor = result.score >= 90
    ? 'text-green-400'
    : result.score >= 70
    ? 'text-yellow-400'
    : 'text-red-400'

  const scoreBg = result.score >= 90
    ? 'bg-green-500'
    : result.score >= 70
    ? 'bg-yellow-500'
    : 'bg-red-500'

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
      <h3 className="font-semibold mb-3">Quality Control</h3>

      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-slate-400">QC Score</span>
          <span className={`text-2xl font-bold ${scoreColor}`}>{result.score}/100</span>
        </div>
        <div className="w-full h-3 bg-slate-700 rounded">
          <div
            className={`h-full rounded ${scoreBg}`}
            style={{ width: `${result.score}%` }}
          />
        </div>
      </div>

      {result.errors.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-medium text-red-400 mb-2">
            Errors ({result.errors.length})
          </h4>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {result.errors.map((error, i) => (
              <div key={i} className="text-sm text-red-300 bg-red-900/20 rounded px-2 py-1">
                {error}
              </div>
            ))}
          </div>
        </div>
      )}

      {result.warnings.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-yellow-400 mb-2">
            Warnings ({result.warnings.length})
          </h4>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {result.warnings.map((warning, i) => (
              <div key={i} className="text-sm text-yellow-300 bg-yellow-900/20 rounded px-2 py-1">
                {warning}
              </div>
            ))}
          </div>
        </div>
      )}

      {result.errors.length === 0 && result.warnings.length === 0 && (
        <div className="text-center py-4 text-green-400">
          All checks passed!
        </div>
      )}
    </div>
  )
}

export default QCDisplay
