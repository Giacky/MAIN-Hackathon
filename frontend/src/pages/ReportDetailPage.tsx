import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { closeReport, dismissMatch } from '../api/alerts'
import { ApiError, apiFetch } from '../api/client'
import { fetchThreads, threadKey } from '../api/coordination'
import type { MatchItem, MatchesResponse, Report } from '../api/types'
import { useAlerts } from '../auth/AlertsContext'
import { useAuth } from '../auth/AuthContext'
import { LocationMap } from '../components/LocationMap'
import { MatchCard } from '../components/MatchCard'
import { Toast } from '../components/Toast'
import { Badge } from '../components/ui/Badge'
import { formatShortWhen } from '../time'

const POLL_MS = 2000

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

function categoryLooksReal(category?: string | null): boolean {
  return Boolean(category && !/mock|unclassified/i.test(category))
}

export function ReportDetailPage() {
  const { id = '' } = useParams()
  const { user } = useAuth()
  const { markReadForReport, notifications } = useAlerts()
  const location = useLocation()
  const navigate = useNavigate()

  const toastFromState = (location.state as { toast?: string } | null)?.toast ?? null
  const [toast, setToast] = useState<string | null>(toastFromState)
  const clearToast = useCallback(() => {
    setToast(null)
    if (toastFromState) navigate(location.pathname + location.search, { replace: true, state: null })
  }, [navigate, location.pathname, location.search, toastFromState])

  const [report, setReport] = useState<Report | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [closing, setClosing] = useState(false)
  const [matches, setMatches] = useState<MatchItem[] | null>(null)
  const [rankError, setRankError] = useState<string | null>(null)
  const [ranking, setRanking] = useState(false)
  const [threadKeys, setThreadKeys] = useState<ReadonlySet<string>>(() => new Set())
  const [pinsOpen, setPinsOpen] = useState(false)

  useEffect(() => {
    if (!user || !id) return
    let cancelled = false
    setReport(null)
    setLoadError(null)
    ;(async () => {
      try {
        const data = await apiFetch<{ report: Report }>(`/api/reports/${encodeURIComponent(id)}`)
        if (cancelled) return
        setReport(data.report)
        setLoadError(null)
      } catch (err) {
        if (cancelled) return
        setLoadError(err instanceof ApiError ? err.message : 'Failed to load report')
      }
    })()
    ;(async () => {
      try {
        const threads = await fetchThreads()
        if (cancelled) return
        setThreadKeys(new Set(threads.map((t) => threadKey(t.lost.id, t.found.id))))
      } catch {
        /* CTA stays "Message them" */
      }
    })()
    return () => {
      cancelled = true
    }
  }, [user, id])

  useEffect(() => {
    if (!id || !user) return
    void markReadForReport(id).catch(() => undefined)
  }, [id, user, markReadForReport, notifications])

  useEffect(() => {
    if (!id || !user || !report || report.status !== 'open') {
      if (report && report.status !== 'open') {
        setMatches([])
        setRanking(false)
      }
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
          `/api/matches?report_id=${encodeURIComponent(id)}`,
        )
        if (cancelled) return
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
  }, [id, user, report?.status])

  async function onClose() {
    if (!report) return
    setClosing(true)
    try {
      await closeReport(report.id)
      setReport({ ...report, status: 'closed' })
      setLoadError(null)
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : 'Could not close report')
    } finally {
      setClosing(false)
    }
  }

  if (loadError && !report) {
    return (
      <div className="space-y-3 animate-in">
        <p className="text-sm text-accent">{loadError}</p>
        <Link to="/reports" className="text-sm font-medium text-primary">
          My items
        </Link>
      </div>
    )
  }

  if (!report) {
    return <p className="text-sm text-muted">Loading report…</p>
  }

  const isOpen = report.status === 'open'
  const category = categoryLooksReal(report.category) ? report.category : null
  const when = formatShortWhen(report.event_time)
  const photos = report.image_urls ?? []
  const count = matches?.length ?? null
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

  return (
    <div className="space-y-5 animate-in">
      <header className="space-y-1">
        <Link to="/reports" className="text-sm font-medium text-primary">
          My items
        </Link>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex flex-wrap items-center gap-1.5">
              <Badge tone={report.report_type === 'lost' ? 'lost' : 'found'}>{report.report_type}</Badge>
              {report.status !== 'open' ? (
                <Badge tone={report.status === 'recovered' ? 'success' : 'muted'}>{report.status}</Badge>
              ) : null}
              {category ? <Badge tone="ink">{category}</Badge> : null}
            </div>
            <h1 className="font-display text-2xl leading-tight text-ink">{report.description}</h1>
            {when ? <p className="text-sm text-muted">{when}</p> : null}
          </div>
          {isOpen ? (
            <div className="flex shrink-0 items-center gap-3 pt-1">
              <Link to={`/reports/${report.id}/edit`} className="text-sm font-semibold text-primary">
                Edit
              </Link>
              <button
                type="button"
                disabled={closing}
                onClick={() => void onClose()}
                className="text-sm font-medium text-muted transition duration-150 hover:text-ink disabled:opacity-60"
              >
                {closing ? 'Closing…' : 'Close'}
              </button>
            </div>
          ) : null}
        </div>
      </header>

      {photos.length > 0 ? (
        <div className="flex gap-2.5 overflow-x-auto no-scrollbar pb-1">
          {photos.map((src) => (
            <div key={src} className="h-52 w-[min(100%,18rem)] shrink-0 overflow-hidden rounded-3xl bg-primary-light/50">
              <img src={src} alt="" className="h-full w-full object-cover" />
            </div>
          ))}
        </div>
      ) : (
        <div className="glass flex h-32 items-center justify-center text-sm text-muted">No photo</div>
      )}

      {report.holding_note ? (
        <p className="text-sm text-ink">
          <span className="text-muted">Holding note · </span>
          {report.holding_note}
        </p>
      ) : null}

      {report.prefer_anonymous ? (
        <p className="text-xs text-muted">You chose to stay anonymous on matches.</p>
      ) : null}

      {loadError ? <p className="text-sm text-accent">{loadError}</p> : null}

      <section className="space-y-3">
        <h2 className="font-display text-lg text-ink">
          {count != null && !ranking
            ? `${count} possible ${count === 1 ? 'match' : 'matches'}`
            : 'Possible matches'}
        </h2>
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
            <p className="text-sm text-ink">{emptyNearbyLabel(report)}</p>
          </div>
        ) : matches.length > 0 ? (
          <div className="space-y-4">
            {matches.map((m) => (
              <MatchCard
                key={`${m.lost.id}-${m.found.id}`}
                match={m}
                anchorType={report.report_type}
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

      {pins.length > 0 ? (
        <div className="glass overflow-hidden">
          <button
            type="button"
            aria-expanded={pinsOpen}
            onClick={() => setPinsOpen((o) => !o)}
            className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-ink"
          >
            <span>
              Pins
              <span className="ml-2 text-xs font-normal text-muted">
                {pins.length === 1 ? '1 pin' : `${pins.length} pins`}
              </span>
            </span>
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden
              className={`text-muted transition-transform duration-200 ${pinsOpen ? 'rotate-180' : ''}`}
            >
              <path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          {pinsOpen ? (
            <div className="border-t border-white/60 px-3 pb-3 pt-2 animate-in">
              <LocationMap mode="view" reports={[report]} className="h-56" />
            </div>
          ) : null}
        </div>
      ) : null}

      <Toast message={toast} onDone={clearToast} />
    </div>
  )
}
