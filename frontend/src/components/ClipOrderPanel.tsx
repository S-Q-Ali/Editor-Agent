import { useState, useEffect } from 'react'
import type { ClipOrder, ClipOrderItem } from '../types'
import { clipApi } from '../services/api'

interface ClipOrderPanelProps {
  projectPath: string
  clipFiles: string[]
  onOrderSaved: () => void
}

function detectNumericPrefix(filename: string): number | null {
  const match = filename.match(/^(\d+)[_\-\s]/)
  return match ? parseInt(match[1], 10) : null
}

function ClipOrderPanel({ projectPath, clipFiles, onOrderSaved }: ClipOrderPanelProps) {
  const [items, setItems] = useState<ClipOrderItem[]>([])
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const autoDetected = clipFiles.map((f, i) => {
      const num = detectNumericPrefix(f)
      return { index: num ?? i, filename: f }
    })
    autoDetected.sort((a, b) => a.index - b.index)
    setItems(autoDetected.map((item, i) => ({ ...item, index: i })))
  }, [clipFiles])

  const moveUp = (idx: number) => {
    if (idx === 0) return
    const newItems = [...items]
    ;[newItems[idx - 1], newItems[idx]] = [newItems[idx], newItems[idx - 1]]
    setItems(newItems.map((item, i) => ({ ...item, index: i })))
  }

  const moveDown = (idx: number) => {
    if (idx === items.length - 1) return
    const newItems = [...items]
    ;[newItems[idx], newItems[idx + 1]] = [newItems[idx + 1], newItems[idx]]
    setItems(newItems.map((item, i) => ({ ...item, index: i })))
  }

  const removeItem = (idx: number) => {
    setItems(items.filter((_, i) => i !== idx).map((item, i) => ({ ...item, index: i })))
  }

  const autoSort = () => {
    const sorted = [...items].sort((a, b) => {
      const numA = detectNumericPrefix(a.filename)
      const numB = detectNumericPrefix(b.filename)
      if (numA !== null && numB !== null) return numA - numB
      if (numA !== null) return -1
      if (numB !== null) return 1
      return a.filename.localeCompare(b.filename)
    })
    setItems(sorted.map((item, i) => ({ ...item, index: i })))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const order: ClipOrder = { mode: 'sequential', clips: items }
      await clipApi.saveOrder(projectPath, order)
      setSaved(true)
      onOrderSaved()
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      console.error('Failed to save clip order:', err)
    } finally {
      setSaving(false)
    }
  }

  if (items.length === 0) return null

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 p-4 mt-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-medium text-sm">Clip Order (Sequential Mode)</h4>
        <div className="flex gap-2">
          <button
            onClick={autoSort}
            className="rounded bg-slate-600 px-2 py-1 text-xs hover:bg-slate-500 transition-colors"
          >
            Auto-Sort
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
              saved
                ? 'bg-green-600 text-white'
                : 'bg-blue-600 hover:bg-blue-500 text-white'
            } disabled:opacity-50`}
          >
            {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Order'}
          </button>
        </div>
      </div>

      <p className="text-xs text-slate-400 mb-3">
        Clips will be used in this order. Drag or use arrows to reorder.
      </p>

      <div className="space-y-1 max-h-64 overflow-y-auto">
        {items.map((item, idx) => (
          <div
            key={item.filename}
            className="flex items-center gap-2 rounded bg-slate-700 px-3 py-2 text-sm"
          >
            <span className="w-6 text-center text-xs text-slate-400 font-mono">
              {idx + 1}
            </span>
            <span className="flex-1 truncate text-slate-200">{item.filename}</span>
            <div className="flex gap-1">
              <button
                onClick={() => moveUp(idx)}
                disabled={idx === 0}
                className="rounded px-1.5 py-0.5 text-xs text-slate-400 hover:bg-slate-600 disabled:opacity-30"
              >
                &#9650;
              </button>
              <button
                onClick={() => moveDown(idx)}
                disabled={idx === items.length - 1}
                className="rounded px-1.5 py-0.5 text-xs text-slate-400 hover:bg-slate-600 disabled:opacity-30"
              >
                &#9660;
              </button>
              <button
                onClick={() => removeItem(idx)}
                className="rounded px-1.5 py-0.5 text-xs text-red-400 hover:bg-red-900/40"
              >
                x
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ClipOrderPanel
