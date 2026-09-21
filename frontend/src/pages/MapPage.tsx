import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, apiFetch } from '../api/client'
import type { Report } from '../api/types'
import { LocationMap } from '../components/LocationMap'
import { Badge } from '../components/ui/Badge'

function unwrapReports(data: { reports?: Report[] } | Report[]): Report[] {
  return Array.isArray(data) ? data : (data.reports ?? [])
}

export function MapPage() {
  const [reports, setReports] = useState<Report[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const data = await apiFetch<{ reports?: Report[] } | Report[]>(
          '/api/reports?scope=open',
        )
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

  const withCoords =
    reports?.filter((r) => r.latitude != null && r.longitude != null) ?? []

  return (
    <div className="space-y-5 animate-in">
      <header>
        <h1 className="font-display text-2xl text-ink">Map</h1>
        <p className="mt-1 text-sm text-muted">
          Open reports around Maastricht. Blue is lost, green is found.
        </p>
      </header>

      <div className="flex gap-2">
        <Badge tone="lost">Lost</Badge>
        <Badge tone="found">Found</Badge>
      </div>

      {error ? (
        <p className="text-sm text-primary">{error}</p>
      ) : reports == null ? (
        <p className="text-sm text-muted">Loading open reports…</p>
      ) : withCoords.length === 0 ? (
        <p className="text-sm text-muted">
          Nothing with coordinates yet.{' '}
          <Link to="/report" className="text-primary underline">
            Add a report
          </Link>
        </p>
      ) : (
        <LocationMap mode="view" reports={withCoords} />
      )}
    </div>
  )
}
