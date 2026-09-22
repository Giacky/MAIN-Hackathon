import { useEffect, useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError, apiFetch } from '../api/client'
import type { DemoAccount } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { safeNext } from '../auth/RedirectToLogin'
import { AvatarChip } from '../components/TopBar'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'

export function LoginPage() {
  const { user, loading, login, register } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [params] = useSearchParams()
  const next = safeNext(params.get('next'))

  const initialMode: 'login' | 'register' =
    location.pathname === '/register' || params.get('mode') === 'register' ? 'register' : 'login'
  const [mode, setMode] = useState<'login' | 'register'>(initialMode)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [busyEmail, setBusyEmail] = useState<string | null>(null)
  const [accounts, setAccounts] = useState<DemoAccount[] | null>(null)

  useEffect(() => {
    setMode(initialMode)
  }, [initialMode])

  useEffect(() => {
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
  }, [])

  function afterLogin() {
    navigate(next || '/', { replace: true })
  }

  function switchMode(nextMode: 'login' | 'register') {
    setMode(nextMode)
    setError(null)
    const search = new URLSearchParams()
    if (next) search.set('next', next)
    if (nextMode === 'register') search.set('mode', 'register')
    const qs = search.toString()
    navigate(nextMode === 'register' ? `/register${qs ? `?${qs}` : ''}` : `/login${qs ? `?${qs}` : ''}`, {
      replace: true,
    })
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

  if (loading) {
    return <p className="text-sm text-muted">Loading…</p>
  }

  if (user) {
    return <Navigate to={next || '/'} replace />
  }

  return (
    <div className="space-y-5 pt-8 animate-in">
      <header>
        <p className="text-sm font-medium text-primary">Lost & Found</p>
        <h1 className="mt-1 font-display text-2xl text-ink">
          {mode === 'login' ? 'Log in' : 'Create an account'}
        </h1>
        <p className="mt-1 text-sm text-muted">
          {mode === 'register'
            ? 'Create an account to file a report.'
            : next
              ? 'Log in to continue where you left off.'
              : 'Report lost and found items around Maastricht.'}
        </p>
      </header>

      <Card>
        <div className="mb-4 flex gap-1 rounded-full bg-hairline/40 p-1">
          {(['login', 'register'] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => switchMode(m)}
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

      <section className="space-y-3">
        <h2 className="text-sm font-medium text-muted">Or try a demo</h2>
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
                    <span className="block truncate text-[15px] font-semibold text-ink">{a.name}</span>
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
      </section>
    </div>
  )
}
