import { useEffect, useRef, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { listDocuments } from './api/client'
import ChatInterface from './components/ChatInterface'
import DocumentList from './components/DocumentList'
import ErrorAlert from './components/ErrorAlert'
import LoginPage from './components/LoginPage'
import UploadZone from './components/UploadZone'
import { useTheme } from './hooks/useTheme'
import { LogOut, Sun, Moon, FolderOpen, Info, X } from 'lucide-react'

function RequireAuth({ children }) {
  const token = sessionStorage.getItem('docmind_token')
  return token ? children : <Navigate to="/login" replace />
}

function DocsDropdown({ documents, selectedDocumentId, onSelect, onDelete, onUploadSuccess, onError }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    if (open) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="p-1.5 rounded hover:bg-white/5 transition-colors text-[var(--color-text-muted)] hover:text-brand relative"
        title="Manage documents"
      >
        <FolderOpen className="w-5 h-5" />
        {selectedDocumentId && (
          <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-brand rounded-full" />
        )}
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-2 w-72 glass-panel-deep rounded-2xl border border-[var(--glass-border)] z-50 overflow-hidden shadow-xl">
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--glass-border)]">
            <span className="text-sm font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
              <FolderOpen className="w-4 h-4 text-brand" />
              Documents
            </span>
            <button
              onClick={() => setOpen(false)}
              className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="p-3 flex flex-col gap-3">
            <UploadZone
              onUploadSuccess={(doc) => { onUploadSuccess(doc); setOpen(false) }}
              onError={onError}
            />
            <DocumentList
              documents={documents}
              selectedId={selectedDocumentId}
              onSelect={(id) => { onSelect(id); setOpen(false) }}
              onDelete={onDelete}
              onError={onError}
            />
          </div>
        </div>
      )}
    </div>
  )
}

function InfoOverlay({ open, onClose }) {
  if (!open) return null
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      <div
        className="glass-panel-deep rounded-2xl border border-[var(--glass-border)] w-full max-w-sm p-6 relative"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <span className="text-sm font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
            <Info className="w-4 h-4 text-brand" />
            How DocMind works
          </span>
          <button
            onClick={onClose}
            className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
          DocMind is a RAG (Retrieval-Augmented Generation) document assistant. Upload a PDF and ask
          questions — it retrieves relevant passages from your document and uses an AI model to generate
          accurate, grounded answers. You can search across all documents or focus on one. The RAGAS
          evaluation tab lets you measure answer quality with standard metrics.
        </p>
      </div>
    </div>
  )
}

function MainApp() {
  const navigate = useNavigate()
  const { theme, toggleTheme } = useTheme()
  const [documents, setDocuments] = useState([])
  const [selectedDocumentId, setSelectedDocumentId] = useState(null)
  const [error, setError] = useState(null)
  const [infoOpen, setInfoOpen] = useState(false)

  useEffect(() => {
    async function fetchDocuments() {
      try {
        const docs = await listDocuments()
        setDocuments(docs)
      } catch {
        setError('Failed to load documents. Is the backend running?')
      }
    }
    fetchDocuments()
  }, [])

  const handleUploadSuccess = (newDoc) => {
    setDocuments((prev) => [newDoc, ...prev])
    setSelectedDocumentId(newDoc.id)
  }

  const handleDocumentDeleted = (deletedId) => {
    setDocuments((prev) => prev.filter((d) => d.id !== deletedId))
    setSelectedDocumentId((prev) => (prev === deletedId ? null : prev))
  }

  const handleLogout = () => {
    sessionStorage.removeItem('docmind_token')
    navigate('/login')
  }

  const selectedDoc = documents.find((d) => d.id === selectedDocumentId) || null

  return (
    <div className="flex flex-col h-screen overflow-hidden">

      <header className="glass-panel border-b border-[var(--glass-border)] flex items-center justify-between px-4 py-3 shrink-0">
        <div className="flex items-center gap-2">
          <DocsDropdown
            documents={documents}
            selectedDocumentId={selectedDocumentId}
            onSelect={setSelectedDocumentId}
            onDelete={handleDocumentDeleted}
            onUploadSuccess={handleUploadSuccess}
            onError={setError}
          />
          <span className="font-display font-extrabold text-lg text-[var(--color-text-primary)] tracking-tight">
            DocMind
          </span>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={toggleTheme}
            className="p-1.5 rounded hover:bg-white/5 transition-colors text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          <button
            onClick={() => setInfoOpen(true)}
            className="p-1.5 rounded hover:bg-white/5 transition-colors text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
            title="How DocMind works"
          >
            <Info className="w-4 h-4" />
          </button>
          <button
            onClick={handleLogout}
            className="p-1.5 rounded hover:bg-white/5 transition-colors text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
            title="Sign out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      <main className="flex-1 overflow-hidden bg-transparent">
        <ChatInterface
          selectedDocument={selectedDoc}
          onError={setError}
          onUploadSuccess={handleUploadSuccess}
        />
      </main>

      <InfoOverlay open={infoOpen} onClose={() => setInfoOpen(false)} />
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/*" element={<RequireAuth><MainApp /></RequireAuth>} />
    </Routes>
  )
}
