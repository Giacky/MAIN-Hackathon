import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { dismissMatch } from '../api/alerts'
import { ApiError, apiFetch } from '../api/client'
import { fetchThreads, threadKey } from '../api/coordination'
import type { MatchItem, MatchesResponse, Report } from '../api/types'
import { useAlerts } from '../auth/AlertsContext'
import { useAuth } from '../auth/AuthContext'
import { RedirectToLogin } from '../auth/RedirectToLogin'
import { MatchCard } from '../components/MatchCard'
import { Toast } from '../components/Toast'
import { Badge } from '../components/ui/Badge'

const POLL_MS = 2000

function unwrapReports(data: { reports?: Report[] } | Report[]): Report[] {
  return Array.isArray(data) ? data : (data.reports ?? [])
}

function positiveMatches(items: MatchItem[]): MatchItem[] {
  return items.filter((m) => (m.overall_score ?? 0) > 0)
}

function emptyNearbyLabel(report: Report): string {
  const category = report.category?.trim()
  if (category && !/mock|unclassified/i.test(category)) {
    return `No ${category.toLowerCase()} reports nearby`
  }
  return 'No reports nearby'
}

export function MatchesPage() {
  const { user, loading } = useAuth()
  const { markReadForReport, notifications } = useAlerts()
  const [params, setParams] = useSearchParams()
  const location = useLocation()
  const navigate = useNavigate()
  const selectedId = params.get('report')

  const toastFromState = (location.state as { toast?: string } | null)?.toast ?? null
  const [toast, setToast] = useState<string | null>(toastFromState)
  const clearToast = useCallback(() => {
    setToast(null)
    if (toastFromState) navigate(location.pathname + location.search, { replace: true, state: null })
  }, [navigate, location.pathname, location.search, toastFromState])

  const [tab, setTab] = useState<'lost' | 'found'>('lost')
  const [mine, setMine] = useState<Report[] | null>(null)
  const [listError, setListError] = useState<string | null>(null)
  const [matches, setMatches] = useState<MatchItem[] | null>(null)
  const [rankError, setRankError] = useState<string | null>(null)
  const [ranking, setRanking] = useState(false)
  const [threadKeys, setThreadKeys] = useState<ReadonlySet<string>>(() => new Set())

  useEffect(() => {
    if (!user) return
    let cancelled = false
    ;(async () => {
      try {
        const data = await apiFetch<{ reports?: Report[] } | Report[]>('/api/reports?scope=mine')
        if (cancelled) return
        setMine(unwrapReports(data))
        setListError(null)
      } catch (err) {
        if (cancelled) return
        setListError(err instanceof ApiError ? err.message : 'Failed to load reports')
      }
    })()
    ;(async () => {
      try {
        const threads = await fetchThreads()
        if (cancelled) return
        setThreadKeys(new Set(threads.map((t) => threadKey(t.lost.id, t.found.id))))
      } catch {
        /* CTA falls back to "Arrange pickup" */
      }
    })()
    return () => {
      cancelled = true
    }
  }, [user])

  useEffect(() => {
    if (!selectedId || !user) return
    void markReadForReport(selectedId).catch(() => undefined)
  }, [selectedId, user, markReadForReport, notifications])

  const tabReports = useMemo(() => {
    if (!mine) return []
    return mine.filter((r) => r.report_type === tab && r.status === 'open')
  }, [mine, tab])

  useEffect(() => {
    if (!selectedId || !mine) return
    const found = mine.find((r) => r.id === selectedId)
    if (found) setTab(found.report_type)
  }, [selectedId, mine])

  function selectReport(reportId: string) {
    setParams({ report: reportId })
  }

  useEffect(() => {
    if (!selectedId || !user) {
      setMatches(null)
      setRanking(false)
      return
    }
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined

    setRankError(null)
    setMatches(null)
    setRanking(true)

    async function load() {
      try {
        const data = await apiFetch<MatchesResponse>(
          `/api/matches?report_id=${encodeURIComponent(selectedId!)}`,
        )
        if (cancelled) return
        // Keep prior cards while computing; replace with latest rows from the server.
        setMatches(positiveMatches(data.matches ?? []))
        setRankError(null)
        if (data.status === 'computing') {
          setRanking(true)
          timer = setTimeout(load, POLL_MS)
        } else {
          setRanking(false)
        }
      } catch (err) {
        if (cancelled) return
        setRankError(err instanceof ApiError ? err.message : 'Ranking failed')
        setRanking(false)
      }
    }

    void load()
    return () => {
      cancelled = true
      if (timer !== undefined) clearTimeout(timer)
    }
  }, [selectedId, user])

  if (loading) return <p className="text-sm text-muted">Loading…</p>
  if (!user) return <RedirectToLogin />

  const selected = mine?.find((r) => r.id === selectedId)
  const count = matches?.length ?? null

  return (
    <div className="space-y-5 animate-in">
      <header>
        <h1 className="font-display text-2xl text-ink">
          {selected && count != null && !ranking
            ? `${count} possible ${count === 1 ? 'match' : 'matches'}`
            : 'Matches'}
        </h1>
        <p className="mt-1 text-sm text-muted">
          {selected
            ? ranking
              ? 'Ranking photo, text, place, and time…'
              : 'Ranked by photo, text, place, and time.'
            : 'Pick one of your open reports to rank possible counterparts.'}
        </p>
      </header>

      <div className="glass flex gap-1 rounded-full p-1" role="tablist" aria-label="Report type">
        {(['lost', 'found'] as const).map((t) => {
          const on = tab === t
          return (
            <button
              key={t}
              type="button"
              role="tab"
              aria-selected={on}
              onClick={() => setTab(t)}
              className={[
                'flex-1 rounded-full py-2 text-sm font-semibold transition-colors duration-200',
                on ? 'bg-primary-light text-primary' : 'text-muted hover:text-ink',
              ].join(' ')}
            >
              {t === 'lost' ? 'My lost' : 'My found'}
            </button>
          )
        })}
      </div>

      {listError ? (
        <p className="text-sm text-accent">{listError}</p>
      ) : mine == null ? (
        <p className="text-sm text-muted">Loading your reports…</p>
      ) : tabReports.length === 0 ? (
        <p className="text-sm text-muted">
          No open {tab} reports.{' '}
          <Link to={`/report?type=${tab}`} className="font-medium text-primary">
            File one
          </Link>
        </p>
      ) : (
        <ul className="flex gap-2 overflow-x-auto no-scrollbar pb-1">
          {tabReports.map((r) => {
            const on = selectedId === r.id
            const photo = r.image_urls?.[0]
            return (
              <li key={r.id} className="shrink-0">
                <button
                  type="button"
                  aria-pressed={on}
                  onClick={() => selectReport(r.id)}
                  className={[
                    'flex w-40 items-center gap-2.5 rounded-2xl border p-2 text-left transition duration-150 active:scale-[0.98]',
                    on
                      ? 'border-primary/50 bg-primary-light/70'
                      : 'border-white/60 bg-card/50 backdrop-blur-xl hover:bg-card/70',
                  ].join(' ')}
                >
                  <span className="h-12 w-12 shrink-0 overflow-hidden rounded-xl bg-primary-light/60">
                    {photo ? <img src={photo} alt="" className="h-full w-full object-cover" /> : null}
                  </span>
                  <span className="min-w-0 flex-1">
                    <Badge tone={r.report_type === 'lost' ? 'lost' : 'found'} className="mb-0.5">
                      {r.report_type}
                    </Badge>
                    <span className="block truncate text-xs leading-snug text-ink">{r.description}</span>
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}

      {selected ? (
        <section className="space-y-3">
          {ranking ? (
            <div
              className="h-1 overflow-hidden rounded-full bg-primary-light"
              role="progressbar"
              aria-label="Ranking matches"
            >
              <div className="match-indeterminate-bar h-full w-1/3 rounded-full bg-primary" />
            </div>
          ) : null}
          {rankError ? (
            <p className="text-sm text-accent">{rankError}</p>
          ) : matches == null ? null : matches.length === 0 && !ranking ? (
            <div className="glass px-4 py-6 text-center">
              <p className="text-sm text-ink">
                {emptyNearbyLabel(selected)}
              </p>
              <p className="mt-1 text-xs text-muted">
                Try another report or add a clearer photo. New reports are matched as they come in.
              </p>
            </div>
          ) : matches.length > 0 ? (
            <div className="space-y-4">
              {matches.map((m) => (
                <MatchCard
                  key={`${m.lost.id}-${m.found.id}`}
                  match={m}
                  anchorType={selected.report_type}
                  hasThread={threadKeys.has(threadKey(m.lost.id, m.found.id))}
                  onDismiss={async () => {
                    await dismissMatch(m.lost.id, m.found.id)
                    setMatches((prev) =>
                      prev
                        ? prev.filter((x) => !(x.lost.id === m.lost.id && x.found.id === m.found.id))
                        : prev,
                    )
                  }}
                />
              ))}
            </div>
          ) : null}
        </section>
      ) : null}

      <Toast message={toast} onDone={clearToast} />
    </div>
  )
}
