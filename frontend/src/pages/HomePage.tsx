import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, apiFetch } from '../api/client'
import { fetchThreads } from '../api/coordination'
import type { CoordinationThread, MatchNotification, Report } from '../api/types'
import { useAlerts } from '../auth/AlertsContext'
import { useAuth } from '../auth/AuthContext'
import { PickupThreadCard } from '../components/PickupThreadCard'
import { Card } from '../components/ui/Card'
import { WarmupBanner } from '../components/WarmupBanner'
import { firstLine } from '../time'

function unwrapReports(data: { reports?: Report[] } | Report[]): Report[] {
  return Array.isArray(data) ? data : (data.reports ?? [])
}

function viewerReportId(n: MatchNotification, mineIds: ReadonlySet<string>): string | null {
  if (n.report_id && (mineIds.size === 0 || mineIds.has(n.report_id))) return n.report_id
  if (mineIds.has(n.lost_report_id)) return n.lost_report_id
  if (mineIds.has(n.found_report_id)) return n.found_report_id
  return n.report_id ?? null
}

function otherSnippet(n: MatchNotification, myId: string | null): Report | null {
  if (myId === n.lost_report_id) return n.found ?? null
  if (myId === n.found_report_id) return n.lost ?? null
  return n.found ?? n.lost ?? null
}

function yoursLabel(report?: Report): string | null {
  if (!report) return null
  const category = report.category?.trim()
  if (category && !/mock|unclassified/i.test(category)) return category.toLowerCase()
  const line = firstLine(report.description, 42)
  return line || null
}

function pairKey(lostId: string, foundId: string): string {
  return `${lostId}:${foundId}`
}

export function HomePage() {
  const { user } = useAuth()
  const { notifications } = useAlerts()
  const [mine, setMine] = useState<Report[] | null>(null)
  const [threads, setThreads] = useState<CoordinationThread[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) {
      setMine(null)
      setThreads(null)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const [reports, list] = await Promise.all([
          apiFetch<{ reports?: Report[] } | Report[]>('/api/reports?scope=mine'),
          fetchThreads(),
        ])
        if (cancelled) return
        setMine(unwrapReports(reports))
        setThreads(list)
        setError(null)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Could not load your activity')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [user])

  const active = threads?.filter((t) => !t.recovered) ?? []
  const mineIds = useMemo(() => new Set((mine ?? []).map((r) => r.id)), [mine])
  const firstName = user?.display_name.split(' ')[0] ?? ''
  const activePairs = useMemo(
    () => new Set(active.map((t) => pairKey(t.lost.id, t.found.id))),
    [active],
  )

  const possibleGroups = useMemo(() => {
    const positive = notifications.filter((n) => (n.overall_score ?? 0) > 0)
    const groups: { reportId: string | null; items: MatchNotification[] }[] = []
    const index = new Map<string, number>()
    for (const n of positive) {
      if (activePairs.has(pairKey(n.lost_report_id, n.found_report_id))) continue
      const myId = viewerReportId(n, mineIds)
      const key = myId ?? `pair:${n.lost_report_id}:${n.found_report_id}`
      const existing = index.get(key)
      if (existing != null) {
        groups[existing].items.push(n)
      } else {
        index.set(key, groups.length)
        groups.push({ reportId: myId, items: [n] })
      }
    }
    return groups
  }, [notifications, mineIds, activePairs])

  const hasInbox = possibleGroups.length + active.length > 0

  return (
    <div className="space-y-5 animate-in">
      <header className="pt-1">
        <h1 className="font-display text-[2rem] leading-tight text-ink">
          {firstName ? `Hi, ${firstName}` : 'Hi'}
        </h1>
      </header>

      <WarmupBanner />

      <div className="grid grid-cols-2 gap-2">
        <Link
          to="/report?type=lost"
          className="glass flex items-center justify-center gap-2 rounded-full px-4 py-3 text-sm font-semibold text-accent transition duration-150 hover:bg-card/70 active:scale-[0.98]"
        >
          <PinGlyph />
          Lost
        </Link>
        <Link
          to="/report?type=found"
          className="glass flex items-center justify-center gap-2 rounded-full px-4 py-3 text-sm font-semibold text-primary transition duration-150 hover:bg-card/70 active:scale-[0.98]"
        >
          <HandGlyph />
          Found
        </Link>
      </div>

      {error ? <p className="text-sm text-accent">{error}</p> : null}

      {hasInbox ? (
        <section className="space-y-3">
          <h2 className="font-display text-lg text-ink">Inbox</h2>
          <div className="space-y-2">
            {possibleGroups.slice(0, 4).map((group) => {
              const n = group.items[0]
              const myId = group.reportId
              const mineReport = myId ? mine?.find((r) => r.id === myId) : undefined
              const other = otherSnippet(n, myId)
              const href = myId ? `/reports/${myId}` : '/reports'
              const photo = other?.image_urls?.[0] ?? mineReport?.image_urls?.[0]
              const forYou = yoursLabel(mineReport)
              const title = other?.description ?? mineReport?.description ?? 'Possible match'
              const count = group.items.length
              return (
                <Link key={n.id} to={href} className="block">
                  <Card padded={false} className="overflow-hidden hover:bg-card/70 active:scale-[0.99]">
                    <div className="flex items-center gap-3 p-3">
                      <div className="h-16 w-16 shrink-0 overflow-hidden rounded-2xl bg-primary-light/60">
                        {photo ? (
                          <img src={photo} alt="" className="h-full w-full object-cover" />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center text-[11px] text-muted">
                            No photo
                          </div>
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        {forYou ? (
                          <p className="text-xs font-medium text-primary">For your {forYou}</p>
                        ) : (
                          <p className="text-xs font-medium text-primary">Possible match</p>
                        )}
                        <p className="mt-0.5 line-clamp-2 text-sm leading-snug text-ink">{title}</p>
                        <p className="mt-0.5 text-xs text-muted">
                          {count === 1 ? 'Needs a look' : `${count} possible matches`}
                        </p>
                      </div>
                      <svg
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        aria-hidden
                        className="text-muted"
                      >
                        <path
                          d="m9 6 6 6-6 6"
                          stroke="currentColor"
                          strokeWidth="1.75"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </div>
                  </Card>
                </Link>
              )
            })}
            {active.slice(0, 3).map((t) => (
              <PickupThreadCard key={`${t.lost.id}-${t.found.id}`} thread={t} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}

function PinGlyph() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 21s7-4.5 7-11a7 7 0 1 0-14 0c0 6.5 7 11 7 11Z"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <circle cx="12" cy="10" r="2.25" fill="currentColor" />
    </svg>
  )
}

function HandGlyph() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M7 11V6.5a1.5 1.5 0 0 1 3 0V11m0-6a1.5 1.5 0 0 1 3 0v6m0-4.5a1.5 1.5 0 0 1 3 0V13m0-2a1.5 1.5 0 0 1 3 0v3.5A6.5 6.5 0 0 1 12.5 21h-1a6.5 6.5 0 0 1-5.6-3.2L4 14.5a1.6 1.6 0 0 1 2.6-1.8L7 13"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
