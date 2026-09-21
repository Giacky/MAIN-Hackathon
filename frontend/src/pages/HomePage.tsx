import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, apiFetch } from '../api/client'
import { fetchThreads } from '../api/coordination'
import type { CoordinationThread, Report } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { ItemCard } from '../components/ItemCard'
import { PickupThreadCard } from '../components/PickupThreadCard'
import { Card } from '../components/ui/Card'
import { WarmupBanner } from '../components/WarmupBanner'

function unwrapReports(data: { reports?: Report[] } | Report[]): Report[] {
  return Array.isArray(data) ? data : (data.reports ?? [])
}

export function HomePage() {
  const { user, loading } = useAuth()
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

  const open = mine?.filter((r) => r.status === 'open') ?? []
  const active = threads?.filter((t) => !t.recovered) ?? []

  return (
    <div className="space-y-6 animate-in">
      <header className="space-y-2 pt-1">
        <p className="text-sm text-muted">
          {loading
            ? 'Checking session…'
            : user
              ? `Hi, ${user.display_name.split(' ')[0]}`
              : 'Tap Log in to try a demo account'}
        </p>
        <h1 className="font-display text-[2rem] leading-tight text-ink">Lost something nearby?</h1>
        <p className="max-w-[22rem] text-[15px] leading-relaxed text-muted">
          Report what you lost or found, then rank photo and place matches around Maastricht.
        </p>
      </header>

      <WarmupBanner />

      <div className="grid grid-cols-2 gap-3">
        <Link to="/report?type=lost" className="block">
          <Card className="h-full transition hover:bg-card/70 active:scale-[0.99]">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-accent/15 text-accent">
              <PinGlyph />
            </span>
            <h2 className="mt-3 font-display text-lg leading-tight text-ink">I lost something</h2>
            <p className="mt-1 text-xs text-muted">Pin where you last had it and add a photo.</p>
          </Card>
        </Link>
        <Link to="/report?type=found" className="block">
          <Card className="h-full transition hover:bg-card/70 active:scale-[0.99]">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-primary-light text-primary">
              <HandGlyph />
            </span>
            <h2 className="mt-3 font-display text-lg leading-tight text-ink">I found something</h2>
            <p className="mt-1 text-xs text-muted">Leave a holding note, stay anonymous if you like.</p>
          </Card>
        </Link>
      </div>

      {user ? (
        <>
          <section className="space-y-3">
            <div className="flex items-baseline justify-between">
              <h2 className="font-display text-lg text-ink">Active pickups</h2>
              {active.length > 0 ? (
                <Link to="/pickup" className="text-sm font-medium text-primary">
                  See all
                </Link>
              ) : null}
            </div>
            {threads == null && !error ? (
              <p className="text-sm text-muted">Loading…</p>
            ) : active.length === 0 ? (
              <p className="text-sm text-muted">
                No pickups in progress. Arrange one from a match.
              </p>
            ) : (
              <div className="space-y-2">
                {active.slice(0, 3).map((t) => (
                  <PickupThreadCard key={`${t.lost.id}-${t.found.id}`} thread={t} />
                ))}
              </div>
            )}
          </section>

          <section className="space-y-3">
            <div className="flex items-baseline justify-between">
              <h2 className="font-display text-lg text-ink">Your open reports</h2>
              {open.length > 0 ? (
                <Link to="/matches" className="text-sm font-medium text-primary">
                  Matches
                </Link>
              ) : null}
            </div>
            {error ? (
              <p className="text-sm text-accent">{error}</p>
            ) : mine == null ? (
              <p className="text-sm text-muted">Loading…</p>
            ) : open.length === 0 ? (
              <p className="text-sm text-muted">
                Nothing open yet.{' '}
                <Link to="/report" className="font-medium text-primary">
                  File a report
                </Link>
              </p>
            ) : (
              <div className="space-y-2">
                {open.map((r) => (
                  <ItemCard key={r.id} report={r} href={`/matches?report=${r.id}`} />
                ))}
              </div>
            )}
          </section>
        </>
      ) : (
        <ol className="glass grid grid-cols-3 gap-2 px-2 py-3 text-center">
          {[
            { n: '1', t: 'Report' },
            { n: '2', t: 'Match' },
            { n: '3', t: 'Meet up' },
          ].map((step) => (
            <li key={step.n} className="px-2 py-1">
              <span className="font-display text-lg text-primary">{step.n}</span>
              <p className="mt-0.5 text-xs text-muted">{step.t}</p>
            </li>
          ))}
        </ol>
      )}
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
