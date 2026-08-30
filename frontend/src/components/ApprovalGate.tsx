import { useState } from 'react'

interface Props {
  qcScore: number
  hasWarnings: boolean
  hasErrors: boolean
  onApprove: () => void
  onRevise: () => void
  loading?: boolean
}

function ApprovalGate({ qcScore, hasWarnings, hasErrors, onApprove, onRevise, loading }: Props) {
  const [confirmed, setConfirmed] = useState(false)

  const canApprove = qcScore >= 70 && !hasErrors && confirmed

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
      <h3 className="text-lg font-semibold mb-4">Human Approval Gate</h3>

      <div className="mb-4 p-4 rounded bg-slate-700/50">
        <p className="text-sm text-slate-300 mb-2">
          Review the preview and QC results before approving the final render.
          The system will not automatically publish content.
        </p>
        <p className="text-sm text-slate-400">
          Once approved, the final MP4 will be rendered with full quality settings.
        </p>
      </div>

      <div className="mb-4">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
            className="w-4 h-4 rounded bg-slate-700 border-slate-600 text-blue-500 focus:ring-blue-500"
          />
          <span className="text-sm">I have reviewed the preview and approve the content</span>
        </label>
      </div>

      {hasErrors && (
        <div className="mb-4 p-3 rounded bg-red-900/30 border border-red-700">
          <p className="text-sm text-red-300">
            Cannot approve: QC has errors that must be resolved first.
          </p>
        </div>
      )}

      {hasWarnings && !hasErrors && (
        <div className="mb-4 p-3 rounded bg-yellow-900/30 border border-yellow-700">
          <p className="text-sm text-yellow-300">
            QC has warnings. You may still approve, but review recommended.
          </p>
        </div>
      )}

      <div className="flex gap-4">
        <button
          onClick={onApprove}
          disabled={!canApprove || loading}
          className="flex-1 rounded-lg bg-green-600 px-4 py-3 font-medium hover:bg-green-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Rendering...' : 'Approve & Render Final'}
        </button>
        <button
          onClick={onRevise}
          disabled={loading}
          className="flex-1 rounded-lg border border-slate-600 px-4 py-3 font-medium hover:bg-slate-700 transition-colors disabled:opacity-50"
        >
          Request Revision
        </button>
      </div>
    </div>
  )
}

export default ApprovalGate
