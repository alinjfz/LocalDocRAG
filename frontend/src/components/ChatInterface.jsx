import { useCallback, useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { queryDocuments, uploadDocument } from '../api/client'
import EvalBadge from './EvalBadge'
import SourceCard from './SourceCard'
import { Send, Bot, User, BookOpen, ChevronDown, ChevronUp, Sparkles, Paperclip, Loader } from 'lucide-react'

const SUGGESTIONS_DEFAULT = [
  'What is this document about?',
  'Summarize the key points',
  'What are the main conclusions?',
  'Give me a specific example from the text',
]

const SUGGESTIONS_WITH_DOC = [
  'Summarize this document',
  'What are the key findings?',
  'List the main topics covered',
  'What does this say about methodology?',
]

function useAutoResize(minHeight = 48, maxHeight = 150) {
  const ref = useRef(null)
  const adjust = useCallback(() => {
    const el = ref.current
    if (!el) return
    el.style.height = `${minHeight}px`
    el.style.height = `${Math.min(el.scrollHeight, maxHeight)}px`
  }, [minHeight, maxHeight])
  return { ref, adjust }
}

function SourcesSection({ sources }) {
  const [open, setOpen] = useState(false)
  if (!sources || sources.length === 0) return null

  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-[11px] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors"
      >
        {open ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        {open ? 'Hide' : 'Show'} {sources.length} source{sources.length > 1 ? 's' : ''}
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {sources.map((source, i) => (
            <SourceCard key={i} source={source} index={i + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

function MessageBubble({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center ${
          isUser ? 'bg-brand/30' : 'glass-panel'
        }`}
      >
        {isUser ? (
          <User className="w-3.5 h-3.5 text-brand-light" />
        ) : (
          <Bot className="w-3.5 h-3.5 text-[var(--color-text-muted)]" />
        )}
      </div>

      <div className={`max-w-[80%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div
          className={`rounded-2xl px-4 py-3 text-sm ${
            isUser
              ? 'bg-gradient-to-br from-indigo-600 to-indigo-700 text-white rounded-tr-sm'
              : 'glass-panel text-[var(--color-text-primary)] rounded-tl-sm'
          }`}
        >
          {isUser ? (
            <p>{message.content}</p>
          ) : (
            <div className="prose-docmind">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>
        {!isUser && message.sources && (
          <div className="w-full mt-1 px-1">
            <SourcesSection sources={message.sources} />
          </div>
        )}
      </div>
    </div>
  )
}

function ThinkingBubble() {
  return (
    <div className="flex gap-3">
      <div className="shrink-0 w-7 h-7 rounded-full glass-panel flex items-center justify-center">
        <Bot className="w-3.5 h-3.5 text-[var(--color-text-muted)]" />
      </div>
      <div className="glass-panel rounded-2xl rounded-tl-sm px-4 py-3">
        <div className="flex gap-1 items-center h-4">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-1.5 h-1.5 bg-brand/50 rounded-full animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

function WelcomeScreen({ selectedDocument, onSuggest }) {
  const suggestions = selectedDocument ? SUGGESTIONS_WITH_DOC : SUGGESTIONS_DEFAULT

  return (
    <div className="flex flex-col items-center justify-center h-full text-center gap-6 py-16 px-4">
      <div>
        <div className="w-14 h-14 glass-panel rounded-2xl flex items-center justify-center mx-auto mb-4">
          <BookOpen className="w-7 h-7 text-brand" />
        </div>
        <h2 className="font-display font-bold text-xl text-[var(--color-text-primary)]">
          {selectedDocument ? selectedDocument.filename : 'DocMind'}
        </h2>
        <p className="text-sm text-[var(--color-text-muted)] mt-1.5">
          {selectedDocument
            ? 'Ask anything about this document'
            : 'Upload a PDF, then ask questions about it'}
        </p>
      </div>

      <div className="flex flex-col gap-2 w-full max-w-sm">
        {suggestions.map((s) => (
          <button
            key={s}
            onClick={() => onSuggest(s)}
            className="glass-panel flex items-center gap-2 text-xs px-4 py-2.5 rounded-xl text-[var(--color-text-muted)] hover:text-brand hover:border-brand/40 transition-all text-left"
          >
            <Sparkles className="w-3 h-3 shrink-0 text-brand/60" />
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function ChatInterface({ selectedDocument, onError, onUploadSuccess }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(null)
  const { ref: textareaRef, adjust } = useAutoResize(48, 150)
  const inputRef = textareaRef
  const bottomRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSubmit = async (e) => {
    e.preventDefault()
    const question = input.trim()
    if (!question || loading) return

    setInput('')
    adjust()
    setMessages((prev) => [...prev, { role: 'user', content: question }])
    setLoading(true)

    try {
      const result = await queryDocuments(question, selectedDocument?.id || null)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: result.answer, sources: result.sources },
      ])
    } catch (err) {
      const detail = err.response?.data?.detail || 'Failed to get an answer.'
      onError(detail)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${detail}`, sources: [] },
      ])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''
    setUploadProgress(0)
    try {
      const newDoc = await uploadDocument(file, (pct) => setUploadProgress(pct))
      onUploadSuccess?.(newDoc)
    } catch (err) {
      onError(err.message || 'Upload failed.')
    } finally {
      setUploadProgress(null)
    }
  }

  const handleSuggest = (text) => {
    setInput(text)
    inputRef.current?.focus()
    setTimeout(adjust, 0)
  }

  return (
    <div className="flex flex-col h-full">

      {selectedDocument && (
        <div className="px-4 pt-3 pb-0">
          <div className="inline-flex items-center gap-1.5 glass-panel border border-brand/25 rounded-full px-3 py-1 text-xs text-brand-light">
            <BookOpen className="w-3 h-3" />
            Searching: <span className="font-medium truncate max-w-[200px]">{selectedDocument.filename}</span>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
        {messages.length === 0 ? (
          <WelcomeScreen selectedDocument={selectedDocument} onSuggest={handleSuggest} />
        ) : (
          messages.map((msg, i) => <MessageBubble key={i} message={msg} />)
        )}
        {loading && <ThinkingBubble />}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-[var(--glass-border)] px-4 py-3">
        <EvalBadge documentId={selectedDocument?.id || null} onError={onError} />
      </div>

      <div className="px-4 py-3">
        <div className="glass-panel-deep rounded-2xl">
          <form onSubmit={handleSubmit} className="flex gap-2 p-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => { setInput(e.target.value); adjust() }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e) }
              }}
              placeholder={
                selectedDocument
                  ? `Ask about "${selectedDocument.filename}"…`
                  : 'Ask a question about your documents…'
              }
              disabled={loading}
              className="flex-1 bg-transparent px-2 py-1.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none resize-none disabled:opacity-50"
              style={{ minHeight: '48px', maxHeight: '150px', overflow: 'hidden' }}
            />

            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={handleFileChange}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadProgress !== null}
              className="shrink-0 self-end text-[var(--color-text-muted)] hover:text-brand disabled:opacity-40 disabled:cursor-not-allowed p-2.5 rounded-xl transition-all mb-0.5 hover:bg-white/5 relative"
              title="Upload PDF"
            >
              {uploadProgress !== null ? (
                <span className="flex items-center justify-center w-4 h-4">
                  <Loader className="w-4 h-4 animate-spin" />
                  <span className="absolute text-[8px] font-bold">{uploadProgress}</span>
                </span>
              ) : (
                <Paperclip className="w-4 h-4" />
              )}
            </button>

            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="shrink-0 self-end bg-brand hover:bg-brand-hover hover:shadow-indigo disabled:opacity-40 disabled:cursor-not-allowed text-white p-2.5 rounded-xl transition-all mb-0.5"
              title="Send (Enter)"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
          <p className="text-[10px] text-[var(--color-text-muted)] pb-2 text-center">
            Enter to send · Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  )
}
