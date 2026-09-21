import { useEffect, useState } from 'react'

interface ToastProps {
  message: string | null | undefined
  /** Milliseconds before the toast hides itself. */
  duration?: number
  onDone?: () => void
}

/** Floating glass toast anchored above the bottom nav. */
export function Toast({ message, duration = 3200, onDone }: ToastProps) {
  const [visible, setVisible] = useState(Boolean(message))

  useEffect(() => {
    if (!message) {
      setVisible(false)
      return
    }
    setVisible(true)
    const timer = window.setTimeout(() => {
      setVisible(false)
      onDone?.()
    }, duration)
    return () => window.clearTimeout(timer)
  }, [message, duration, onDone])

  if (!visible || !message) return null

  return (
    <div
      role="status"
      className="pointer-events-none fixed inset-x-0 bottom-[calc(5.5rem+env(safe-area-inset-bottom))] z-50 flex justify-center px-4"
    >
      <div className="glass-strong animate-toast pointer-events-auto flex max-w-md items-center gap-2 rounded-full px-4 py-2.5 text-sm text-ink">
        <span className="h-2 w-2 shrink-0 rounded-full bg-success" aria-hidden />
        <span>{message}</span>
      </div>
    </div>
  )
}
