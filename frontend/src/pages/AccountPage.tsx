import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, apiFetch } from '../api/client'
import type { Report } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { ItemCard } from '../components/ItemCard'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'

const DEMO_USERS = [
  { label: 'Alex', email: 'alex@demo.local' },
  { label: 'Sam', email: 'sam@demo.local' },
  { label: 'Mia', email: 'mia@demo.local' },
]

export function AccountPage() {
  const { user, loading, login, register, logout } = useAuth()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [reports, setReports] = useState<Report[] | null>(null)
  const [reportsError, setReportsError] = useState<string | null>(null)
  const [resetMsg, setResetMsg] = useState<string | null>(null)

  useEffect(() => {
    if (!user) {
      setReports(null)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const data = await apiFetch<{ reports?: Report[] } | Report[]>(
          '/api/reports?scope=mine',
        )
        if (cancelled) return
        const list = Array.isArray(data) ? data : (data.reports ?? [])
        setReports(list)
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
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Authentication failed')
    } finally {
      setBusy(false)
    }
  }

  async function demoLogin(demoEmail: string) {
    setBusy(true)
    setError(null)
    try {
      await login(demoEmail, 'demo')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Demo login failed')
    } finally {
      setBusy(false)
    }
  }

  async function resetDemo() {
    setResetMsg(null)
    setBusy(true)
    try {
      await apiFetch('/api/demo/reset', {
        method: 'POST',
        headers: { 'X-Demo-Reset': 'demo' },
      })
      setResetMsg('Demo data reloaded.')
      if (user) {
        const data = await apiFetch<{ reports?: Report[] } | Report[]>(
          '/api/reports?scope=mine',
        )
        setReports(Array.isArray(data) ? data : (data.reports ?? []))
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
          <h1 className="font-display text-2xl text-ink">Account</h1>
          <p className="mt-1 text-sm text-muted">
            Demo quick-login uses password <span className="text-ink">demo</span>.
          </p>
        </header>

        <div className="grid grid-cols-3 gap-2">
          {DEMO_USERS.map((d) => (
            <Button
              key={d.email}
              variant="secondary"
              disabled={busy}
              onClick={() => void demoLogin(d.email)}
            >
              {d.label}
            </Button>
          ))}
        </div>

        <Card>
          <div className="mb-4 flex gap-2">
            <Button
              variant={mode === 'login' ? 'primary' : 'ghost'}
              onClick={() => setMode('login')}
            >
              Log in
            </Button>
            <Button
              variant={mode === 'register' ? 'primary' : 'ghost'}
              onClick={() => setMode('register')}
            >
              Create account
            </Button>
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
            />
            {error ? <p className="text-sm text-primary">{error}</p> : null}
            <Button type="submit" fullWidth disabled={busy}>
              {busy ? 'Working…' : mode === 'login' ? 'Log in' : 'Create account'}
            </Button>
          </form>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-5 animate-in">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl text-ink">{user.display_name}</h1>
          <p className="mt-1 text-sm text-muted">{user.email}</p>
        </div>
        <Button variant="secondary" onClick={() => void logout()}>
          Log out
        </Button>
      </header>

      <div className="flex flex-wrap gap-2">
        <Link
          to="/report?type=lost"
          className="rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-white"
        >
          New report
        </Link>
        <Link
          to="/matches"
          className="rounded-xl border border-hairline bg-card px-4 py-2.5 text-sm font-medium"
        >
          Matches
        </Link>
        <Button variant="ghost" disabled={busy} onClick={() => void resetDemo()}>
          Reload demo
        </Button>
      </div>
      {resetMsg ? <p className="text-sm text-muted">{resetMsg}</p> : null}

      <section className="space-y-3">
        <h2 className="font-display text-lg text-ink">Your reports</h2>
        {reportsError ? (
          <p className="text-sm text-primary">{reportsError}</p>
        ) : reports == null ? (
          <p className="text-sm text-muted">Loading reports…</p>
        ) : reports.length === 0 ? (
          <p className="text-sm text-muted">
            No reports yet.{' '}
            <Link to="/report" className="text-primary underline">
              File one
            </Link>
          </p>
        ) : (
          <div className="space-y-2">
            {reports.map((r) => (
              <ItemCard
                key={r.id}
                report={r}
                href={`/matches?report=${r.id}`}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
