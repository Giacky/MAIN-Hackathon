import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { isUnreadNotification } from '../api/alerts'
import { ApiError, apiFetch } from '../api/client'
import type { Report, ReportType } from '../api/types'
import { useAlerts } from '../auth/AlertsContext'
import { useAuth } from '../auth/AuthContext'
import { ItemCard } from '../components/ItemCard'

function unwrapReports(data: { reports?: Report[] } | Report[]): Report[] {
  return Array.isArray(data) ? data : (data.reports ?? [])
}

function newestOpenType(reports: Report[]): ReportType {
  const open = reports
    .filter((r) => r.status === 'open')
    .sort((a, b) => {
      const timeA = Date.parse(a.event_time || a.created_at || '') || 0
      const timeB = Date.parse(b.event_time || b.created_at || '') || 0
      return timeB - timeA
    })
  return open[0]?.report_type === 'found' ? 'found' : 'lost'
}

export function ReportsPage() {
  const { user } = useAuth()
  const { notifications } = useAlerts()
  const [reports, setReports] = useState<Report[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<ReportType | null>(null)

  const activityByReport = useMemo(() => {
    const map = new Map<string, { hasUnread: boolean; hasMessage: boolean }>()
    for (const n of notifications) {
      if (!isUnreadNotification(n)) continue
      const rid = n.report_id
      if (!rid) continue
      const prev = map.get(rid) ?? { hasUnread: false, hasMessage: false }
      prev.hasUnread = true
      if (n.kind === 'message') prev.hasMessage = true
      map.set(rid, prev)
    }
    return map
  }, [notifications])

  useEffect(() => {
    if (!user) return
    let cancelled = false
    ;(async () => {
      try {
        const data = await apiFetch<{ reports?: Report[] } | Report[]>('/api/reports?scope=mine')
        if (cancelled) return
        const list = unwrapReports(data)
        setReports(list)
        setTab((prev) => prev ?? newestOpenType(list))
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

  const activeTab: ReportType = tab ?? 'lost'

  const ordered = useMemo(() => {
    if (!reports) return []
    return reports
      .filter((r) => r.report_type === activeTab)
      .sort((a, b) => {
        const openA = a.status === 'open' ? 0 : 1
        const openB = b.status === 'open' ? 0 : 1
        if (openA !== openB) return openA - openB
        const timeA = Date.parse(a.event_time || a.created_at || '') || 0
        const timeB = Date.parse(b.event_time || b.created_at || '') || 0
        return timeB - timeA
      })
  }, [reports, activeTab])

  return (
    <div className="space-y-5 animate-in">
      <div className="flex justify-end">
        <Link
          to="/report"
          className="shrink-0 rounded-full bg-linear-to-b from-primary/90 to-primary px-4 py-2 text-sm font-medium text-white shadow-[inset_0_1px_0_rgba(255,255,255,.28),0_4px_12px_rgba(23,107,104,.25)] transition duration-150 active:scale-[0.98]"
        >
          New
        </Link>
      </div>

      <div className="glass flex gap-1 rounded-full p-1" role="tablist" aria-label="Report type">
        {(['lost', 'found'] as const).map((t) => {
          const on = activeTab === t
          return (
            <button
              key={t}
              type="button"
              role="tab"
              aria-selected={on}
              onClick={() => setTab(t)}
              className={[
                'flex-1 rounded-full py-2.5 text-sm font-semibold transition-colors duration-200',
                on
                  ? t === 'lost'
                    ? 'bg-accent text-white shadow-[inset_0_1px_0_rgba(255,255,255,.3)]'
                    : 'bg-primary text-white shadow-[inset_0_1px_0_rgba(255,255,255,.25)]'
                  : 'text-muted hover:text-ink',
              ].join(' ')}
            >
              {t === 'lost' ? 'Lost' : 'Found'}
            </button>
          )
        })}
      </div>

      {error ? (
        <p className="text-sm text-accent">{error}</p>
      ) : reports == null ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : ordered.length === 0 ? (
        <div className="glass space-y-2 px-4 py-6 text-center">
          <p className="text-sm text-ink">
            {activeTab === 'lost' ? 'No lost reports yet.' : 'No found reports yet.'}
          </p>
          <Link
            to={`/report?type=${activeTab}`}
            className={`text-sm font-medium ${activeTab === 'lost' ? 'text-accent' : 'text-primary'}`}
          >
            {activeTab === 'lost' ? 'Report something lost' : 'Report something found'}
          </Link>
        </div>
      ) : (
        <div className="space-y-2">
          {ordered.map((r) => {
            const activity = activityByReport.get(r.id)
            return (
              <ItemCard
                key={r.id}
                report={r}
                href={`/reports/${r.id}`}
                hasUnreadActivity={Boolean(activity?.hasUnread)}
                showNewMessage={Boolean(activity?.hasMessage)}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}
