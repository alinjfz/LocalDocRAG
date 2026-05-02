import { useState } from 'react'
import { FileText, ChevronDown, ChevronUp } from 'lucide-react'

const SNIPPET_LENGTH = 220

function ScoreBar({ score }) {
  const pct = Math.round(score * 100)
  const color = score >= 0.8 ? 'bg-emerald-500' : score >= 0.6 ? 'bg-amber-500' : 'bg-orange-500'

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-white/10 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-[var(--color-text-muted)] w-7 text-right">{pct}%</span>
    </div>
  )
}

export default function SourceCard({ source, index }) {
  const [expanded, setExpanded] = useState(false)

  const isLong = source.content.length > SNIPPET_LENGTH
  const displayText = expanded || !isLong ? source.content : source.content.slice(0, SNIPPET_LENGTH) + '…'

  return (
    <div className="glass-panel rounded-xl p-3 text-xs space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="bg-brand/15 text-brand-light border border-brand/25 px-1.5 py-0.5 rounded text-[10px] font-mono font-medium">
            #{index}
          </span>
          <div className="flex items-center gap-1 text-[var(--color-text-muted)]">
            <FileText className="w-3 h-3" />
            <span>Page {source.page_number}</span>
          </div>
        </div>
      </div>

      <ScoreBar score={source.score} />

      <p className="text-[var(--color-text-secondary)] leading-relaxed">{displayText}</p>

      {isLong && (
        <button
          onClick={() => setExpanded((e) => !e)}
          className="flex items-center gap-1 text-brand hover:text-brand-light transition-colors"
        >
          {expanded
            ? <><ChevronUp className="w-3 h-3" /> Show less</>
            : <><ChevronDown className="w-3 h-3" /> Show more</>
          }
        </button>
      )}
    </div>
  )
}
