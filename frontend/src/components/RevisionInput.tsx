import { useState } from 'react'

interface Props {
  onSubmit: (instruction: string) => void
  disabled?: boolean
}

function RevisionInput({ onSubmit, disabled }: Props) {
  const [instruction, setInstruction] = useState('')
  const [history, setHistory] = useState<string[]>([])

  const examples = [
    "0:32 wala clip change karo",
    "Chorus ko zyada energetic karo",
    "Brushing wale clips repeat ho rahe hain",
    "Intro slow lag raha hai",
    "Replace low confidence clips",
    "Make transitions smoother",
  ]

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (instruction.trim() && !disabled) {
      setHistory([...history, instruction.trim()])
      onSubmit(instruction.trim())
      setInstruction('')
    }
  }

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
      <h3 className="font-semibold mb-3">Natural Language Revision</h3>

      <form onSubmit={handleSubmit} className="mb-4">
        <textarea
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          placeholder="Describe what you want to change..."
          disabled={disabled}
          className="w-full rounded-lg border border-slate-600 bg-slate-700 px-3 py-2 text-slate-100 placeholder-slate-400 focus:outline-none focus:border-blue-500 resize-none h-24 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!instruction.trim() || disabled}
          className="mt-2 rounded-lg bg-blue-600 px-4 py-2 font-medium hover:bg-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Apply Revision
        </button>
      </form>

      <div>
        <p className="text-sm text-slate-400 mb-2">Examples:</p>
        <div className="flex flex-wrap gap-2">
          {examples.map((example, i) => (
            <button
              key={i}
              onClick={() => setInstruction(example)}
              disabled={disabled}
              className="rounded-full bg-slate-700 px-3 py-1 text-xs text-slate-300 hover:bg-slate-600 transition-colors disabled:opacity-50"
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      {history.length > 0 && (
        <div className="mt-4 border-t border-slate-700 pt-4">
          <p className="text-sm text-slate-400 mb-2">Revision History:</p>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {history.map((item, i) => (
              <div key={i} className="text-sm text-slate-300">
                <span className="text-slate-500">{i + 1}.</span> {item}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default RevisionInput
