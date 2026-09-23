import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { isUnreadNotification } from '../api/alerts'
import { ApiError, apiFetch } from '../api/client'
import { fetchThreads } from '../api/coordination'
import type {
  CoordinationThread,
  MatchItem,
  MatchNotification,
  MatchesResponse,
  Report,
} from '../api/types'
import { useAlerts } from '../auth/AlertsContext'
import { useAuth } from '../auth/AuthContext'
import { PickupThreadCard } from '../components/PickupThreadCard'
import { Card } from '../components/ui/Card'
import { WarmupBanner } from '../components/WarmupBanner'
import { firstLine } from '../time'

function unwrapReports(data: { reports?: Report[] } | Report[]): Report[] {
  return Array.isArray(data) ? data : (data.reports ?? [])
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

function otherFromMatch(match: MatchItem, mineId: string): Report {
  return match.lost.id === mineId ? match.found : match.lost
}

interface ForYouGroup {
  reportId: string
  mineReport: Report
  other: Report
  count: number
}

export function HomePage() {
  const { user } = useAuth()
  const { notifications } = useAlerts()
  const [mine, setMine] = useState<Report[] | null>(null)
  const [threads, setThreads] = useState<CoordinationThread[] | null>(null)
  const [forYou, setForYou] = useState<ForYouGroup[]>([])
  const [checking, setChecking] = useState(false)
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

  const active = useMemo(() => threads?.filter((t) => !t.recovered) ?? [], [threads])
  const firstName = user?.display_name.split(' ')[0] ?? ''
  const activePairs = useMemo(
    () => new Set(active.map((t) => pairKey(t.lost.id, t.found.id))),
    [active],
  )

  /** One Home card per unread message pair; last line from the thread when available. */
  const messageCards = useMemo(() => {
    const byPair = new Map<string, MatchNotification>()
    for (const n of notifications) {
      if (!isUnreadNotification(n) || n.kind !== 'message') continue
      const key = pairKey(n.lost_report_id, n.found_report_id)
      if (!byPair.has(key)) byPair.set(key, n)
    }
    return [...byPair.values()]
  }, [notifications])

  const messagePairKeys = useMemo(
    () => new Set(messageCards.map((n) => pairKey(n.lost_report_id, n.found_report_id))),
    [messageCards],
  )

  const pickupWithoutUnreadMsg = useMemo(
    () => active.filter((t) => !messagePairKeys.has(pairKey(t.lost.id, t.found.id))),
    [active, messagePairKeys],
  )

  const threadByPair = useMemo(() => {
    const map = new Map<string, CoordinationThread>()
    for (const t of threads ?? []) {
      map.set(pairKey(t.lost.id, t.found.id), t)
    }
    return map
  }, [threads])

  const openReports = useMemo(
    () => (mine ?? []).filter((r) => r.status === 'open'),
    [mine],
  )

  const openWithMatches = useMemo(
    () => openReports.filter((r) => (r.match_count ?? 0) > 0),
    [openReports],
  )

  useEffect(() => {
    if (!user || openReports.length === 0) {
      setChecking(false)
      return
    }
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined

    async function poll() {
      try {
        const statuses = await Promise.all(
          openReports.map(async (report) => {
            const data = await apiFetch<MatchesResponse>(
              `/api/matches?report_id=${encodeURIComponent(report.id)}`,
            )
            return data.status === 'computing'
          }),
        )
        if (cancelled) return
        const anyComputing = statuses.some(Boolean)
        setChecking(anyComputing)
        if (anyComputing) timer = setTimeout(poll, 2500)
      } catch {
        if (!cancelled) setChecking(false)
      }
    }

    void poll()
    return () => {
      cancelled = true
      if (timer !== undefined) clearTimeout(timer)
    }
  }, [user, openReports])

  useEffect(() => {
    if (!user || openWithMatches.length === 0) {
      setForYou([])
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const groups = await Promise.all(
          openWithMatches.map(async (report) => {
            const data = await apiFetch<MatchesResponse>(
              `/api/matches?report_id=${encodeURIComponent(report.id)}`,
            )
            const positive = (data.matches ?? []).filter((m) => (m.overall_score ?? 0) > 0)
            const leftover = positive.filter(
              (m) => !activePairs.has(pairKey(m.lost.id, m.found.id)),
            )
            if (leftover.length === 0) return null
            const top = leftover[0]
            return {
              reportId: report.id,
              mineReport: report,
              other: otherFromMatch(top, report.id),
              count: leftover.length,
            } satisfies ForYouGroup
          }),
        )
        if (cancelled) return
        setForYou(groups.filter((g): g is ForYouGroup => g != null))
      } catch {
        if (!cancelled) setForYou([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [user, openWithMatches, activePairs])

  const hasForYou = forYou.length + messageCards.length + pickupWithoutUnreadMsg.length > 0
  const showForYouSection = hasForYou || checking

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

      {showForYouSection ? (
        <section className="space-y-3">
          <h2 className="font-display text-lg text-ink">For you</h2>
          {checking && !hasForYou ? (
            <div className="glass space-y-2 px-4 py-5 text-center">
              <p className="text-sm font-medium text-ink">Checking for matches</p>
              <div
                className="mx-auto h-1 w-32 overflow-hidden rounded-full bg-primary-light"
                role="progressbar"
                aria-label="Checking for matches"
              >
                <div className="match-indeterminate-bar h-full w-1/3 rounded-full bg-primary" />
              </div>
            </div>
          ) : null}
          <div className="space-y-2">
            {messageCards.map((n) => {
              const key = pairKey(n.lost_report_id, n.found_report_id)
              const thread = threadByPair.get(key)
              const lastLine = thread?.last_message
                ? firstLine(thread.last_message, 60)
                : null
              const photo = thread
                ? (thread.role === 'lost' ? thread.found : thread.lost).image_urls?.[0] ??
                  (thread.role === 'lost' ? thread.lost : thread.found).image_urls?.[0]
                : undefined
              return (
                <Link
                  key={key}
                  to={`/pickup/${n.lost_report_id}/${n.found_report_id}`}
                  className="block"
                >
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
                        <p className="text-xs font-medium text-accent">New message</p>
                        <p className="mt-0.5 line-clamp-2 text-sm leading-snug text-ink">
                          {lastLine ? `“${lastLine}”` : 'Open the thread to reply'}
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
            {forYou.slice(0, 4).map((group) => {
              const photo = group.other.image_urls?.[0] ?? group.mineReport.image_urls?.[0]
              const forLabel = yoursLabel(group.mineReport)
              const title = group.other.description || group.mineReport.description || 'Possible match'
              return (
                <Link key={group.reportId} to={`/reports/${group.reportId}`} className="block">
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
                        {forLabel ? (
                          <p className="text-xs font-medium text-primary">For your {forLabel}</p>
                        ) : (
                          <p className="text-xs font-medium text-primary">Possible match</p>
                        )}
                        <p className="mt-0.5 line-clamp-2 text-sm leading-snug text-ink">{title}</p>
                        <p className="mt-0.5 text-xs text-muted">
                          {group.count === 1 ? 'Needs a look' : `${group.count} possible matches`}
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
            {pickupWithoutUnreadMsg.slice(0, 3).map((t) => (
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
