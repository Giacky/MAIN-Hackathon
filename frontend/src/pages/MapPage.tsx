import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError, apiFetch } from '../api/client'
import { fetchThreads } from '../api/coordination'
import type { CoordinationThread, Report, ReportType } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { RedirectToLogin } from '../auth/RedirectToLogin'
import { ItemCard } from '../components/ItemCard'
import { LocationMap } from '../components/LocationMap'
import { Badge } from '../components/ui/Badge'
import { Button, buttonBase, buttonVariants } from '../components/ui/Button'
import { fieldClass } from '../components/ui/Input'
import { firstLine, timeAgo } from '../time'

function unwrapReports(data: { reports?: Report[] } | Report[]): Report[] {
  return Array.isArray(data) ? data : (data.reports ?? [])
}

const legend: { kind: ReportType; label: string; on: string; dot: string }[] = [
  { kind: 'lost', label: 'Lost', on: 'bg-accent/15 text-accent border-accent/30', dot: 'bg-accent' },
  { kind: 'found', label: 'Found', on: 'bg-primary-light text-primary border-primary/20', dot: 'bg-primary' },
]

function claimHref(report: Report): string {
  const opposite = report.report_type === 'found' ? 'lost' : 'found'
  const pins =
    report.locations?.length > 0
      ? report.locations
      : report.latitude != null && report.longitude != null
        ? [
            {
              latitude: report.latitude,
              longitude: report.longitude,
              radius_meters: report.radius_meters ?? 200,
            },
          ]
        : []
  const params = new URLSearchParams({ type: opposite, claim: report.id })
  if (pins[0]) {
    params.set('lat', String(pins[0].latitude))
    params.set('lng', String(pins[0].longitude))
    params.set('radius', String(pins[0].radius_meters))
  }
  return `/report?${params.toString()}`
}

export function MapPage() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const [reports, setReports] = useState<Report[] | null>(null)
  const [mineIds, setMineIds] = useState<ReadonlySet<string>>(() => new Set())
  const [threads, setThreads] = useState<CoordinationThread[]>([])
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [visible, setVisible] = useState<Record<ReportType, boolean>>({ lost: true, found: true })
  const [preview, setPreview] = useState<Report | null>(null)

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

  function openOther(report: Report) {
    const thread = threadByReport.get(report.id)
    if (thread) {
      navigate(`/pickup/${thread.lost.id}/${thread.found.id}`)
      return
    }
    setPreview(report)
  }

  if (loading) return <p className="text-sm text-muted">Loading…</p>
  if (!user) return <RedirectToLogin />

  const claimLabel =
    preview?.report_type === 'found' ? 'This is mine' : preview?.report_type === 'lost' ? 'I found this' : null

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
              {reports != null ? (
                <span className="tabular-nums opacity-70">{counts[item.kind]}</span>
              ) : null}
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
            <LocationMap
              mode="view"
              reports={withCoords}
              mineIds={mineIds}
              className="h-[22rem]"
              onSelectReport={(report) => {
                if (mineIds.has(report.id)) return
                openOther(report)
              }}
            />
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
                    onSelect={!mine && !thread ? () => setPreview(r) : undefined}
                    trailing={
                      mine ? (
                        <span className="text-[11px] font-semibold text-primary">Yours</span>
                      ) : thread ? (
                        <span className="text-[11px] font-semibold text-primary">Message</span>
                      ) : (
                        <span className="text-[11px] font-semibold text-muted">Claim</span>
                      )
                    }
                  />
                )
              })
            )}
          </div>
        </>
      )}

      {preview ? (
        <div
          className="fixed inset-0 z-40 flex items-end justify-center bg-ink/35 px-4 pb-8 pt-16 backdrop-blur-sm animate-in"
          role="dialog"
          aria-modal="true"
          aria-labelledby="map-claim-title"
          onClick={() => setPreview(null)}
        >
          <div
            className="glass-strong w-full max-w-md space-y-4 rounded-3xl p-4 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex gap-3">
              <div className="h-20 w-20 shrink-0 overflow-hidden rounded-2xl bg-primary-light/60">
                {preview.image_urls?.[0] ? (
                  <img src={preview.image_urls[0]} alt="" className="h-full w-full object-cover" />
                ) : null}
              </div>
              <div className="min-w-0 flex-1">
                <div className="mb-1 flex items-center gap-1.5">
                  <Badge tone={preview.report_type === 'lost' ? 'lost' : 'found'}>
                    {preview.report_type}
                  </Badge>
                  {timeAgo(preview.event_time ?? preview.created_at) ? (
                    <span className="text-[11px] text-muted">
                      {timeAgo(preview.event_time ?? preview.created_at)}
                    </span>
                  ) : null}
                </div>
                <h2 id="map-claim-title" className="font-display text-lg leading-snug text-ink">
                  {firstLine(preview.description, 100)}
                </h2>
                {preview.holding_note ? (
                  <p className="mt-1 text-xs text-muted">Holding: {preview.holding_note}</p>
                ) : null}
              </div>
            </div>
            <div className="flex flex-col gap-2">
              {claimLabel ? (
                <Link
                  to={claimHref(preview)}
                  className={[buttonBase, buttonVariants.accent, 'w-full py-2.5 text-center'].join(' ')}
                >
                  {claimLabel}
                </Link>
              ) : null}
              <Button variant="ghost" type="button" onClick={() => setPreview(null)}>
                Not this
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
