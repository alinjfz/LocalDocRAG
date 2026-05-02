import { useCallback, useRef, useState } from 'react'
import { uploadDocument } from '../api/client'
import { Upload, CheckCircle } from 'lucide-react'

export default function UploadZone({ onUploadSuccess, onError }) {
  const [isDragging, setIsDragging] = useState(false)
  const [progress, setProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [lastUploaded, setLastUploaded] = useState(null)
  const fileInputRef = useRef(null)

  const handleFile = useCallback(
    async (file) => {
      if (!file) return
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        onError('Only PDF files are supported.')
        return
      }

      setUploading(true)
      setProgress(0)
      setLastUploaded(null)

      try {
        const doc = await uploadDocument(file, (pct) => setProgress(pct))
        setLastUploaded(doc.filename)
        onUploadSuccess(doc)
      } catch (err) {
        onError(err.message || 'Upload failed.')
      } finally {
        setUploading(false)
        setProgress(0)
        if (fileInputRef.current) fileInputRef.current.value = ''
      }
    },
    [onUploadSuccess, onError]
  )

  const onDrop = useCallback(
    (e) => {
      e.preventDefault()
      setIsDragging(false)
      handleFile(e.dataTransfer.files[0])
    },
    [handleFile]
  )

  return (
    <div>
      <p className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
        Upload Document
      </p>

      <div
        onClick={() => !uploading && fileInputRef.current?.click()}
        onDrop={onDrop}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
        onDragLeave={() => setIsDragging(false)}
        className={`
          glass-panel relative border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-all
          ${isDragging
            ? 'border-brand bg-brand/8 shadow-amber scale-[1.01]'
            : 'border-[var(--glass-border)] hover:border-brand/50 hover:bg-white/5'}
          ${uploading ? 'pointer-events-none opacity-70' : ''}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={(e) => handleFile(e.target.files[0])}
        />

        {uploading ? (
          <div className="space-y-2">
            <div className="text-xs text-[var(--color-text-secondary)]">Uploading… {progress}%</div>
            <div className="w-full bg-white/10 rounded-full h-1.5">
              <div
                className="h-1.5 rounded-full transition-all duration-150"
                style={{
                  width: `${progress}%`,
                  background: 'linear-gradient(90deg, #d97706, #fbbf24)',
                }}
              />
            </div>
          </div>
        ) : lastUploaded ? (
          <div className="flex items-center justify-center gap-2 text-sm text-green-400">
            <CheckCircle className="w-4 h-4" />
            <span className="truncate max-w-[10rem]" title={lastUploaded}>{lastUploaded}</span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1.5">
            <Upload className="w-6 h-6 text-[var(--color-text-muted)]" />
            <div className="text-xs text-[var(--color-text-secondary)]">
              <span className="text-brand font-medium">Click to upload</span> or drag &amp; drop
            </div>
            <div className="text-xs text-[var(--color-text-muted)]">PDF files only</div>
          </div>
        )}
      </div>
    </div>
  )
}
