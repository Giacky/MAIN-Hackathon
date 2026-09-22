import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, apiFetch } from '../api/client'
import type { Report } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { ItemCard } from '../components/ItemCard'

function unwrapReports(data: { reports?: Report[] } | Report[]): Report[] {
  return Array.isArray(data) ? data : (data.reports ?? [])
}

export function ReportsPage() {
  const { user } = useAuth()
  const [reports, setReports] = useState<Report[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) return
    let cancelled = false
    ;(async () => {
      try {
        const data = await apiFetch<{ reports?: Report[] } | Report[]>('/api/reports?scope=mine')
        if (cancelled) return
        setReports(unwrapReports(data))
        setError(null)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Failed to load items')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [user])

  const ordered = useMemo(() => {
    if (!reports) return []
    return [...reports].sort((a, b) => {
      const openA = a.status === 'open' ? 0 : 1
      const openB = b.status === 'open' ? 0 : 1
      if (openA !== openB) return openA - openB
      const timeA = Date.parse(a.event_time || a.created_at || '') || 0
      const timeB = Date.parse(b.event_time || b.created_at || '') || 0
      return timeB - timeA
    })
  }, [reports])

  return (
    <div className="space-y-5 animate-in">
      <header className="flex items-center justify-between gap-3">
        <h1 className="font-display text-2xl text-ink">My items</h1>
        <Link
          to="/report"
          className="shrink-0 rounded-full bg-linear-to-b from-primary/90 to-primary px-4 py-2 text-sm font-medium text-white shadow-[inset_0_1px_0_rgba(255,255,255,.28),0_4px_12px_rgba(23,107,104,.25)] transition duration-150 active:scale-[0.98]"
        >
          New
        </Link>
      </header>

      {error ? (
        <p className="text-sm text-accent">{error}</p>
      ) : reports == null ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : ordered.length === 0 ? (
        <div className="glass space-y-2 px-4 py-6 text-center">
          <p className="text-sm text-ink">Nothing here yet.</p>
          <div className="flex justify-center gap-2">
            <Link to="/report?type=lost" className="text-sm font-medium text-accent">
              Lost
            </Link>
            <span className="text-muted">·</span>
            <Link to="/report?type=found" className="text-sm font-medium text-primary">
              Found
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          {ordered.map((r) => (
            <ItemCard key={r.id} report={r} href={`/reports/${r.id}`} />
          ))}
        </div>
      )}
    </div>
  )
}
