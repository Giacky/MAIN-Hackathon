import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError, apiFetch } from '../api/client'
import type { DemoAccount, HealthResponse, Report } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { safeNext } from '../auth/RedirectToLogin'
import { ItemCard } from '../components/ItemCard'
import { AvatarChip } from '../components/TopBar'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'

function unwrapReports(data: { reports?: Report[] } | Report[]): Report[] {
  return Array.isArray(data) ? data : (data.reports ?? [])
}

export function AccountPage() {
  const { user, loading, login, register, logout, refresh } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = safeNext(params.get('next'))

  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [busyEmail, setBusyEmail] = useState<string | null>(null)
  const [accounts, setAccounts] = useState<DemoAccount[] | null>(null)
  const [reports, setReports] = useState<Report[] | null>(null)
  const [reportsError, setReportsError] = useState<string | null>(null)
  const [resetMsg, setResetMsg] = useState<string | null>(null)
  const [confirmReset, setConfirmReset] = useState(false)
  const [demoResetAllowed, setDemoResetAllowed] = useState(false)

  // Demo personas for one-tap login. A 404 (endpoint not shipped yet) renders nothing.
  useEffect(() => {
    if (user) return
    let cancelled = false
    ;(async () => {
      try {
        const data = await apiFetch<{ accounts?: DemoAccount[] } | DemoAccount[]>(
          '/api/auth/demo-accounts',
        )
        if (cancelled) return
        setAccounts(Array.isArray(data) ? data : (data.accounts ?? []))
      } catch {
        if (!cancelled) setAccounts([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [user])

  useEffect(() => {
    if (!user) {
      setReports(null)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const data = await apiFetch<{ reports?: Report[] } | Report[]>('/api/reports?scope=mine')
        if (cancelled) return
        setReports(unwrapReports(data))
        setReportsError(null)
      } catch (err) {
        if (cancelled) return
        setReportsError(err instanceof ApiError ? err.message : 'Failed to load reports')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [user])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const health = await apiFetch<HealthResponse>('/api/health')
        if (cancelled) return
        setDemoResetAllowed(Boolean(health.demo_reset_allowed))
      } catch {
        if (!cancelled) setDemoResetAllowed(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  function afterLogin() {
    if (next) navigate(next, { replace: true })
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      if (mode === 'login') {
        await login(email.trim(), password)
      } else {
        await register(displayName.trim(), email.trim(), password)
      }
      afterLogin()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Authentication failed')
    } finally {
      setBusy(false)
    }
  }

  async function demoLogin(demoEmail: string) {
    setBusy(true)
    setBusyEmail(demoEmail)
    setError(null)
    try {
      await login(demoEmail, 'demo')
      afterLogin()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Demo login failed')
    } finally {
      setBusy(false)
      setBusyEmail(null)
    }
  }

  async function resetDemo() {
    setResetMsg(null)
    setConfirmReset(false)
    setBusy(true)
    try {
      await apiFetch('/api/demo/reset', {
        method: 'POST',
        headers: { 'X-Demo-Reset': 'demo' },
      })
      setResetMsg('Demo data reloaded.')
      // The wipe also resets the users table; re-check the session.
      await refresh()
      try {
        const data = await apiFetch<{ reports?: Report[] } | Report[]>('/api/reports?scope=mine')
        setReports(unwrapReports(data))
      } catch {
        setReports(null)
      }
    } catch (err) {
      setResetMsg(err instanceof ApiError ? err.message : 'Reset failed')
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return <p className="text-sm text-muted">Loading account…</p>
  }

  if (!user) {
    return (
      <div className="space-y-5 animate-in">
        <header>
          <h1 className="font-display text-2xl text-ink">Who are you today?</h1>
          <p className="mt-1 text-sm text-muted">
            {next
              ? 'Log in to continue where you left off.'
              : 'Pick a demo persona to log in with one tap.'}
          </p>
        </header>

        {accounts && accounts.length > 0 ? (
          <div className="grid grid-cols-2 gap-3">
            {accounts.map((a) => {
              const isBusy = busyEmail === a.email
              return (
                <button
                  key={a.email}
                  type="button"
                  disabled={busy}
                  onClick={() => void demoLogin(a.email)}
                  aria-label={`Log in as ${a.name}`}
                  className={[
                    'glass flex flex-col items-start gap-2.5 p-3.5 text-left transition duration-150 hover:bg-card/75 active:scale-[0.98] disabled:opacity-70',
                    isBusy ? 'ring-2 ring-primary/40' : '',
                  ].join(' ')}
                >
                  <AvatarChip name={a.name} color={a.avatar} size="lg" />
                  <span className="min-w-0">
                    <span className="block truncate text-[15px] font-semibold text-ink">
                      {a.name}
                    </span>
                    <span className="mt-0.5 block text-xs leading-snug text-muted">
                      {isBusy ? 'Logging in…' : a.summary}
                    </span>
                  </span>
                </button>
              )
            })}
          </div>
        ) : accounts == null ? (
          <div className="grid grid-cols-2 gap-3" aria-hidden>
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="glass h-32 animate-pulse" />
            ))}
          </div>
        ) : null}

        <Card>
          <div className="mb-4 flex gap-1 rounded-full bg-hairline/40 p-1">
            {(['login', 'register'] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
                className={[
                  'flex-1 rounded-full py-2 text-sm font-medium transition-colors duration-200',
                  mode === m ? 'bg-card text-ink shadow-sm' : 'text-muted hover:text-ink',
                ].join(' ')}
              >
                {m === 'login' ? 'Log in' : 'Create account'}
              </button>
            ))}
          </div>

          <form className="space-y-3" onSubmit={(e) => void onSubmit(e)}>
            {mode === 'register' ? (
              <Input
                label="Name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
                autoComplete="name"
              />
            ) : null}
            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={4}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              hint={mode === 'login' ? 'Demo accounts use the password "demo".' : undefined}
            />
            {error ? <p className="text-sm text-accent">{error}</p> : null}
            <Button type="submit" fullWidth disabled={busy}>
              {busy && !busyEmail ? 'Working…' : mode === 'login' ? 'Log in' : 'Create account'}
            </Button>
          </form>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-5 animate-in">
      <header className="flex items-center gap-3">
        <AvatarChip name={user.display_name} color={user.avatar} size="lg" />
        <div className="min-w-0 flex-1">
          <h1 className="truncate font-display text-2xl text-ink">{user.display_name}</h1>
          <p className="truncate text-sm text-muted">{user.email}</p>
        </div>
        <Button variant="secondary" className="px-3.5 py-2 text-sm" onClick={() => void logout()}>
          Log out
        </Button>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        <Link
          to="/report?type=lost"
          className="rounded-full bg-linear-to-b from-primary/90 to-primary px-4 py-2 text-sm font-medium text-white shadow-[inset_0_1px_0_rgba(255,255,255,.28),0_4px_12px_rgba(23,107,104,.25)] transition duration-150 active:scale-[0.98]"
        >
          New report
        </Link>
        <Link to="/matches" className="glass rounded-full px-4 py-2 text-sm font-medium text-ink">
          Matches
        </Link>
        {demoResetAllowed && !confirmReset ? (
          <Button
            variant="ghost"
            className="px-3 py-2 text-sm"
            disabled={busy}
            onClick={() => {
              setResetMsg(null)
              setConfirmReset(true)
            }}
          >
            Reload demo
          </Button>
        ) : null}
      </div>

      {demoResetAllowed && confirmReset ? (
        <Card className="animate-in border-accent/30">
          <p className="text-sm text-ink">Reload the demo data?</p>
          <p className="mt-1 text-xs text-muted">
            This wipes every report, note, and meetup and reseeds the sample items. You may need to
            log in again.
          </p>
          <div className="mt-3 flex gap-2">
            <Button variant="accent" className="px-4 py-2 text-sm" disabled={busy} onClick={() => void resetDemo()}>
              {busy ? 'Reloading…' : 'Yes, reload'}
            </Button>
            <Button variant="ghost" className="px-4 py-2 text-sm" onClick={() => setConfirmReset(false)}>
              Cancel
            </Button>
          </div>
        </Card>
      ) : null}
      {resetMsg ? <p className="text-sm text-muted">{resetMsg}</p> : null}

      <section className="space-y-3">
        <h2 className="font-display text-lg text-ink">Your reports</h2>
        {reportsError ? (
          <p className="text-sm text-accent">{reportsError}</p>
        ) : reports == null ? (
          <p className="text-sm text-muted">Loading reports…</p>
        ) : reports.length === 0 ? (
          <p className="text-sm text-muted">
            No reports yet.{' '}
            <Link to="/report" className="font-medium text-primary">
              File one
            </Link>
          </p>
        ) : (
          <div className="space-y-2">
            {reports.map((r) => (
              <ItemCard key={r.id} report={r} href={`/matches?report=${r.id}`} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
