import { useEffect, useMemo, useState } from 'react'
import { ApiError, apiFetch } from '../api/client'
import { fetchThreads } from '../api/coordination'
import type { CoordinationThread, Report, ReportType } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { RedirectToLogin } from '../auth/RedirectToLogin'
import { ItemCard } from '../components/ItemCard'
import { LocationMap } from '../components/LocationMap'
import { fieldClass } from '../components/ui/Input'

function unwrapReports(data: { reports?: Report[] } | Report[]): Report[] {
  return Array.isArray(data) ? data : (data.reports ?? [])
}

const legend: { kind: ReportType; label: string; on: string; dot: string }[] = [
  { kind: 'lost', label: 'Lost', on: 'bg-accent/15 text-accent border-accent/30', dot: 'bg-accent' },
  { kind: 'found', label: 'Found', on: 'bg-primary-light text-primary border-primary/20', dot: 'bg-primary' },
]

export function MapPage() {
  const { user, loading } = useAuth()
  const [reports, setReports] = useState<Report[] | null>(null)
  const [mineIds, setMineIds] = useState<ReadonlySet<string>>(() => new Set())
  const [threads, setThreads] = useState<CoordinationThread[]>([])
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [visible, setVisible] = useState<Record<ReportType, boolean>>({ lost: true, found: true })

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const data = await apiFetch<{ reports?: Report[] } | Report[]>('/api/reports?scope=open')
        if (cancelled) return
        setReports(unwrapReports(data))
        setError(null)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Failed to load map')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!user) {
      setMineIds(new Set())
      setThreads([])
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const [mine, list] = await Promise.all([
          apiFetch<{ reports?: Report[] } | Report[]>('/api/reports?scope=mine'),
          fetchThreads(),
        ])
        if (cancelled) return
        setMineIds(new Set(unwrapReports(mine).map((r) => r.id)))
        setThreads(list)
      } catch {
        /* list cards simply omit the yours / message links */
      }
    })()
    return () => {
      cancelled = true
    }
  }, [user])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return (reports ?? []).filter((r) => {
      if (!visible[r.report_type === 'lost' ? 'lost' : 'found']) return false
      if (!q) return true
      const hay = `${r.description} ${r.category ?? ''}`.toLowerCase()
      return hay.includes(q)
    })
  }, [reports, visible, query])

  const withCoords = useMemo(
    () => filtered.filter((r) => r.latitude != null && r.longitude != null),
    [filtered],
  )
  const counts = useMemo(
    () => ({
      lost: (reports ?? []).filter((r) => r.report_type === 'lost').length,
      found: (reports ?? []).filter((r) => r.report_type === 'found').length,
    }),
    [reports],
  )
  const threadByReport = useMemo(() => {
    const map = new Map<string, CoordinationThread>()
    for (const t of threads) {
      if (t.recovered) continue
      map.set(t.lost.id, t)
      map.set(t.found.id, t)
    }
    return map
  }, [threads])

  function toggle(kind: ReportType) {
    setVisible((v) => ({ ...v, [kind]: !v[kind] }))
  }

  if (loading) return <p className="text-sm text-muted">Loading…</p>
  if (!user) return <RedirectToLogin />

  return (
    <div className="space-y-4 animate-in">
      <label className="relative block">
        <span className="sr-only">Search</span>
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden
          className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-muted"
        >
          <circle cx="11" cy="11" r="6.25" stroke="currentColor" strokeWidth="1.75" />
          <path d="m16 16 4 4" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
        </svg>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Wallet, keys…"
          className={`${fieldClass} pl-10`}
        />
      </label>

      <div className="flex gap-2" role="group" aria-label="Filter pins">
        {legend.map((item) => {
          const on = visible[item.kind]
          return (
            <button
              key={item.kind}
              type="button"
              aria-pressed={on}
              onClick={() => toggle(item.kind)}
              className={[
                'inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold backdrop-blur-md transition duration-150 active:scale-[0.97]',
                on ? item.on : 'border-hairline/70 bg-card/40 text-muted line-through decoration-muted/60',
              ].join(' ')}
            >
              <span className={`h-2 w-2 rounded-full ${on ? item.dot : 'bg-muted/40'}`} aria-hidden />
              {item.label}
              <span className="tabular-nums opacity-70">{counts[item.kind]}</span>
            </button>
          )
        })}
      </div>

      {error ? (
        <p className="text-sm text-accent">{error}</p>
      ) : reports == null ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : (
        <>
          {withCoords.length > 0 ? (
            <LocationMap mode="view" reports={withCoords} mineIds={mineIds} className="h-[22rem]" />
          ) : (
            <p className="text-sm text-muted">No pins for this filter.</p>
          )}

          <div className="space-y-2">
            {filtered.length === 0 ? (
              <p className="text-sm text-muted">Nothing matches.</p>
            ) : (
              filtered.map((r) => {
                const mine = mineIds.has(r.id)
                const thread = threadByReport.get(r.id)
                const href = mine
                  ? `/reports/${r.id}`
                  : thread
                    ? `/pickup/${thread.lost.id}/${thread.found.id}`
                    : undefined
                return (
                  <ItemCard
                    key={r.id}
                    report={r}
                    href={href}
                    trailing={
                      mine ? (
                        <span className="text-[11px] font-semibold text-primary">Yours</span>
                      ) : thread ? (
                        <span className="text-[11px] font-semibold text-primary">Message</span>
                      ) : undefined
                    }
                  />
                )
              })
            )}
          </div>
        </>
      )}
    </div>
  )
}
