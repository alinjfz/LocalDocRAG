import { useState } from 'react'
import { runEvaluation } from '../api/client'
import { BarChart2, Loader } from 'lucide-react'

const METRIC_LABELS = {
  faithfulness: 'Faithfulness',
  answer_relevancy: 'Relevancy',
  context_precision: 'Precision',
  context_recall: 'Recall',
}

function MetricBadge({ name, value }) {
  const pct = Math.round(value * 100)
  const borderColor =
    value >= 0.8 ? 'border-l-emerald-500' : value >= 0.6 ? 'border-l-indigo-400' : 'border-l-red-500'
  const textColor =
    value >= 0.8 ? 'text-emerald-400' : value >= 0.6 ? 'text-indigo-300' : 'text-red-400'
  const barColor =
    value >= 0.8 ? 'bg-emerald-500' : value >= 0.6 ? 'bg-indigo-500' : 'bg-red-500'

  return (
    <div className={`glass-panel rounded-xl p-3 border-l-4 ${borderColor} flex flex-col gap-1.5`}>
      <span className="text-[10px] text-[var(--color-text-muted)] font-medium uppercase tracking-wide">
        {METRIC_LABELS[name] || name}
      </span>
      <span className={`text-2xl font-bold ${textColor}`}>{pct}%</span>
      <div className="h-1 rounded-full bg-[var(--color-surface-border)] overflow-hidden">
        <div
          className={`h-full rounded-full ${barColor} transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

export default function EvalBadge({ documentId, onError }) {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [question, setQuestion] = useState('')
  const [groundTruth, setGroundTruth] = useState('')

  const handleRun = async (e) => {
    e.preventDefault()
    if (!documentId) {
      onError('Select a document before running evaluation.')
      return
    }
    setLoading(true)
    setMetrics(null)
    try {
      const result = await runEvaluation([
        { question, ground_truth: groundTruth, document_id: documentId },
      ])
      setMetrics(result.metrics)
      setShowForm(false)
    } catch (err) {
      onError(err.response?.data?.detail || 'RAGAS evaluation failed. Check OPENAI_API_KEY.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="glass-panel rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
          <BarChart2 className="w-4 h-4 text-brand" />
          <span className="font-medium">RAG Evaluation</span>
        </div>
        <button
          onClick={() => setShowForm((f) => !f)}
          className="text-xs text-brand hover:text-brand-light transition-colors px-2.5 py-1 rounded-lg border border-brand/20 hover:border-brand/40 hover:bg-brand/5"
        >
          {showForm ? 'Cancel' : 'Run'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleRun} className="space-y-2 mb-3">
          <input
            type="text"
            placeholder="Test question…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            required
            className="input-glass w-full px-3 py-2 text-xs"
          />
          <input
            type="text"
            placeholder="Expected answer (ground truth)…"
            value={groundTruth}
            onChange={(e) => setGroundTruth(e.target.value)}
            required
            className="input-glass w-full px-3 py-2 text-xs"
          />
          <button
            type="submit"
            disabled={loading}
            className="btn-brand w-full text-xs py-2 px-3 flex items-center justify-center gap-1.5"
          >
            {loading ? (
              <>
                <Loader className="w-3.5 h-3.5 animate-spin" />
                Evaluating…
              </>
            ) : (
              'Run RAGAS'
            )}
          </button>
        </form>
      )}

      {metrics && (
        <div className="grid grid-cols-2 gap-2 mt-1">
          {Object.entries(metrics).map(([name, value]) => (
            <MetricBadge key={name} name={name} value={value} />
          ))}
        </div>
      )}
    </div>
  )
}
