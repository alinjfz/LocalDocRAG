import { useState } from 'react'
import { deleteDocument } from '../api/client'
import { FileText, Trash2, Globe } from 'lucide-react'

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function ProviderBadge({ provider }) {
  const colors = {
    openai: 'bg-emerald-900/40 text-emerald-300 border-emerald-700/40',
    anthropic: 'bg-sky-900/40 text-sky-300 border-sky-700/40',
    ollama: 'bg-violet-900/40 text-violet-300 border-violet-700/40',
  }
  return (
    <span
      className={`text-[10px] px-1.5 py-0.5 rounded border font-medium ${
        colors[provider] || 'glass-panel text-[var(--color-text-muted)]'
      }`}
    >
      {provider}
    </span>
  )
}

export default function DocumentList({ documents, selectedId, onSelect, onDelete, onError }) {
  const [deletingId, setDeletingId] = useState(null)

  const handleDelete = async (e, docId) => {
    e.stopPropagation()
    if (!confirm('Delete this document and all its chunks?')) return
    setDeletingId(docId)
    try {
      await deleteDocument(docId)
      onDelete(docId)
    } catch {
      onError('Failed to delete document.')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
          Documents ({documents.length})
        </p>
        {selectedId && (
          <button
            onClick={() => onSelect(null)}
            title="Search all documents"
            className="flex items-center gap-1 text-[10px] text-brand hover:text-brand-light transition-colors"
          >
            <Globe className="w-3 h-3" />
            All
          </button>
        )}
      </div>

      {documents.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center py-8">
          <FileText className="w-8 h-8 text-[var(--color-text-muted)] mb-2 opacity-40" />
          <p className="text-xs text-[var(--color-text-muted)]">No documents yet.</p>
          <p className="text-xs text-[var(--color-text-muted)] opacity-60">Upload a PDF to get started.</p>
        </div>
      ) : (
        <ul className="flex-1 overflow-y-auto space-y-1 pr-0.5">
          {documents.map((doc) => (
            <li key={doc.id}>
              <button
                onClick={() => onSelect(doc.id === selectedId ? null : doc.id)}
                className={`w-full text-left px-3 py-2.5 rounded-lg transition-all group ${
                  doc.id === selectedId
                    ? 'glass-panel ring-1 ring-brand/50 shadow-amber-inset text-[var(--color-text-primary)]'
                    : 'hover:bg-white/5 hover:border-[var(--glass-border)] border border-transparent text-[var(--color-text-secondary)]'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2 min-w-0">
                    <FileText
                      className={`w-4 h-4 mt-0.5 shrink-0 ${
                        doc.id === selectedId ? 'text-brand-light' : 'text-[var(--color-text-muted)]'
                      }`}
                    />
                    <div className="min-w-0">
                      <p className="text-xs font-medium truncate leading-tight" title={doc.filename}>
                        {doc.filename}
                      </p>
                      <div className="flex items-center gap-1.5 mt-1">
                        <span className="text-[10px] text-[var(--color-text-muted)]">{doc.chunk_count} chunks</span>
                        <span className="text-[10px] text-[var(--color-text-muted)] opacity-40">·</span>
                        <ProviderBadge provider={doc.embedding_provider} />
                      </div>
                      <p className="text-[10px] text-[var(--color-text-muted)] mt-0.5">{formatDate(doc.created_at)}</p>
                    </div>
                  </div>

                  <button
                    onClick={(e) => handleDelete(e, doc.id)}
                    disabled={deletingId === doc.id}
                    className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-red-500/15 text-[var(--color-text-muted)] hover:text-red-400 disabled:opacity-30"
                    title="Delete document"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
