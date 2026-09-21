import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, apiFetch } from '../api/client'
import type { Report, ReportType } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { LocationMap } from '../components/LocationMap'

function unwrapReports(data: { reports?: Report[] } | Report[]): Report[] {
  return Array.isArray(data) ? data : (data.reports ?? [])
}

const legend: { kind: ReportType; label: string; on: string; dot: string }[] = [
  { kind: 'lost', label: 'Lost', on: 'bg-accent/15 text-accent border-accent/30', dot: 'bg-accent' },
  { kind: 'found', label: 'Found', on: 'bg-primary-light text-primary border-primary/20', dot: 'bg-primary' },
]

export function MapPage() {
  const { user } = useAuth()
  const [reports, setReports] = useState<Report[] | null>(null)
  const [mineIds, setMineIds] = useState<ReadonlySet<string>>(() => new Set())
  const [error, setError] = useState<string | null>(null)
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
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const data = await apiFetch<{ reports?: Report[] } | Report[]>('/api/reports?scope=mine')
        if (cancelled) return
        setMineIds(new Set(unwrapReports(data).map((r) => r.id)))
      } catch {
        /* popups simply omit the "See matches" link */
      }
    })()
    return () => {
      cancelled = true
    }
  }, [user])

  const withCoords = useMemo(
    () => reports?.filter((r) => r.latitude != null && r.longitude != null) ?? [],
    [reports],
  )
  const shown = useMemo(
    () => withCoords.filter((r) => visible[r.report_type === 'lost' ? 'lost' : 'found']),
    [withCoords, visible],
  )
  const counts = useMemo(
    () => ({
      lost: withCoords.filter((r) => r.report_type === 'lost').length,
      found: withCoords.filter((r) => r.report_type === 'found').length,
    }),
    [withCoords],
  )

  function toggle(kind: ReportType) {
    setVisible((v) => ({ ...v, [kind]: !v[kind] }))
  }

  return (
    <div className="space-y-4 animate-in">
      <header>
        <h1 className="font-display text-2xl text-ink">Map</h1>
        <p className="mt-1 text-sm text-muted">
          Open reports around Maastricht. Coral is lost, teal is found. Tap a pin for details.
        </p>
      </header>

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
        <p className="text-sm text-muted">Loading open reports…</p>
      ) : withCoords.length === 0 ? (
        <p className="text-sm text-muted">
          Nothing with coordinates yet.{' '}
          <Link to="/report" className="font-medium text-primary">
            Add a report
          </Link>
        </p>
      ) : (
        <LocationMap mode="view" reports={shown} mineIds={mineIds} className="h-[28rem]" />
      )}
    </div>
  )
}
