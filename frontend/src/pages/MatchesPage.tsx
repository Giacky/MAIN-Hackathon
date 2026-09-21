import { useEffect, useMemo, useState } from 'react'
import { Link, Navigate, useSearchParams } from 'react-router-dom'
import { ApiError, apiFetch } from '../api/client'
import type { MatchItem, Report } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { MatchCard } from '../components/MatchCard'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'

function unwrapReports(data: { reports?: Report[] } | Report[]): Report[] {
  return Array.isArray(data) ? data : (data.reports ?? [])
}

function unwrapMatches(
  data: { matches?: MatchItem[] } | MatchItem[],
): MatchItem[] {
  return Array.isArray(data) ? data : (data.matches ?? [])
}

export function MatchesPage() {
  const { user, loading } = useAuth()
  const [params, setParams] = useSearchParams()
  const selectedId = params.get('report')

  const [tab, setTab] = useState<'lost' | 'found'>('lost')
  const [mine, setMine] = useState<Report[] | null>(null)
  const [listError, setListError] = useState<string | null>(null)
  const [matches, setMatches] = useState<MatchItem[] | null>(null)
  const [rankError, setRankError] = useState<string | null>(null)
  const [ranking, setRanking] = useState(false)

  useEffect(() => {
    if (!user) return
    let cancelled = false
    ;(async () => {
      try {
        const data = await apiFetch<{ reports?: Report[] } | Report[]>(
          '/api/reports?scope=mine',
        )
        if (cancelled) return
        setMine(unwrapReports(data))
        setListError(null)
      } catch (err) {
        if (cancelled) return
        setListError(err instanceof ApiError ? err.message : 'Failed to load reports')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [user])

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
      return
    }
    let cancelled = false
    setRanking(true)
    setRankError(null)
    setMatches(null)
    ;(async () => {
      try {
        const data = await apiFetch<{ matches?: MatchItem[] } | MatchItem[]>(
          `/api/matches?report_id=${encodeURIComponent(selectedId)}`,
        )
        if (cancelled) return
        const list = unwrapMatches(data).filter((m) => (m.overall_score ?? 0) > 0)
        setMatches(list)
      } catch (err) {
        if (cancelled) return
        setRankError(err instanceof ApiError ? err.message : 'Ranking failed')
      } finally {
        if (!cancelled) setRanking(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [selectedId, user])

  if (loading) return <p className="text-sm text-muted">Loading…</p>
  if (!user) return <Navigate to="/account" replace />

  const selected = mine?.find((r) => r.id === selectedId)

  return (
    <div className="space-y-5 animate-in">
      <header>
        <h1 className="font-display text-2xl text-ink">Matches</h1>
        <p className="mt-1 text-sm text-muted">
          Pick one of your open reports to rank possible counterparts.
        </p>
      </header>

      <div className="flex gap-2">
        <Button
          variant={tab === 'lost' ? 'primary' : 'secondary'}
          onClick={() => setTab('lost')}
        >
          My lost
        </Button>
        <Button
          variant={tab === 'found' ? 'primary' : 'secondary'}
          onClick={() => setTab('found')}
        >
          My found
        </Button>
      </div>

      {listError ? (
        <p className="text-sm text-primary">{listError}</p>
      ) : mine == null ? (
        <p className="text-sm text-muted">Loading your reports…</p>
      ) : tabReports.length === 0 ? (
        <p className="text-sm text-muted">
          No open {tab} reports.{' '}
          <Link to={`/report?type=${tab}`} className="text-primary underline">
            File one
          </Link>
        </p>
      ) : (
        <ul className="space-y-2">
          {tabReports.map((r) => (
            <li key={r.id}>
              <button
                type="button"
                onClick={() => selectReport(r.id)}
                className={[
                  'w-full rounded-2xl border px-3 py-3 text-left transition duration-150',
                  selectedId === r.id
                    ? 'border-primary/50 bg-cream'
                    : 'border-hairline bg-card hover:border-primary/30',
                ].join(' ')}
              >
                <div className="mb-1 flex items-center gap-2">
                  <Badge tone={r.report_type === 'lost' ? 'lost' : 'found'}>
                    {r.report_type}
                  </Badge>
                  {ranking && selectedId === r.id ? (
                    <span className="text-xs text-muted">Ranking…</span>
                  ) : null}
                </div>
                <p className="line-clamp-2 text-sm text-ink">{r.description}</p>
              </button>
            </li>
          ))}
        </ul>
      )}

      {selected ? (
        <section className="space-y-3">
          <h2 className="font-display text-lg text-ink">Ranked results</h2>
          {ranking ? (
            <p className="text-sm text-muted">Ranking…</p>
          ) : rankError ? (
            <p className="text-sm text-primary">{rankError}</p>
          ) : matches == null ? null : matches.length === 0 ? (
            <p className="text-sm text-muted">
              No positive matches yet. Try another report or add a clearer photo.
            </p>
          ) : (
            <div className="space-y-4">
              {matches.map((m) => (
                <MatchCard
                  key={`${m.lost.id}-${m.found.id}`}
                  match={m}
                  anchorType={selected.report_type}
                />
              ))}
            </div>
          )}
        </section>
      ) : null}
    </div>
  )
}
