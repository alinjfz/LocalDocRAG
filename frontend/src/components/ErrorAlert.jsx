import { useEffect } from 'react'
import { AlertCircle, X } from 'lucide-react'

export default function ErrorAlert({ message, onDismiss, autoHideMs = 5000 }) {
  useEffect(() => {
    if (!message) return
    const timer = setTimeout(onDismiss, autoHideMs)
    return () => clearTimeout(timer)
  }, [message, onDismiss, autoHideMs])

  if (!message) return null

  return (
    <div className="mx-4 mt-2 flex items-start gap-3 bg-red-500/10 backdrop-blur-md border border-red-500/25 rounded-xl shadow-lg px-4 py-3 text-sm text-red-200 animate-in slide-in-from-top-2 duration-200">
      <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
      <span className="flex-1">{message}</span>
      <button
        onClick={onDismiss}
        className="shrink-0 text-red-400 hover:text-red-200 transition-colors"
        aria-label="Dismiss"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}
