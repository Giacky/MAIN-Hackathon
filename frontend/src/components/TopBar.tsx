import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

function titleFor(pathname: string): string {
  if (pathname === '/') return 'Lost & Found'
  if (/^\/reports\/[^/]+\/edit/.test(pathname)) return 'Edit report'
  if (/^\/reports\/[^/]+/.test(pathname)) return 'Report'
  if (pathname.startsWith('/reports')) return 'My items'
  if (pathname.startsWith('/report')) return 'New report'
  if (pathname.startsWith('/around') || pathname.startsWith('/map')) return 'Map'
  if (pathname.startsWith('/pickup')) return 'Pickup'
  if (pathname.startsWith('/account')) return 'Account'
  return 'Lost & Found'
}

export function AvatarChip({
  name,
  color,
  size = 'md',
}: {
  name: string
  color?: string | null
  size?: 'sm' | 'md' | 'lg'
}) {
  const initial = name.trim().charAt(0).toUpperCase() || '?'
  const dims = size === 'lg' ? 'h-14 w-14 text-xl' : size === 'sm' ? 'h-7 w-7 text-xs' : 'h-9 w-9 text-sm'
  return (
    <span
      className={`inline-flex ${dims} shrink-0 items-center justify-center rounded-full font-semibold text-white shadow-[inset_0_1px_0_rgba(255,255,255,.35),0_2px_8px_rgba(32,38,37,.18)]`}
      style={{ backgroundColor: color || 'var(--color-primary)' }}
      aria-hidden
    >
      {initial}
    </span>
  )
}

/** Slim glass bar: page title left, avatar chip (or "Log in") right. */
export function TopBar() {
  const { user, loading } = useAuth()
  const { pathname } = useLocation()
  const title = titleFor(pathname)
  const onAccount = pathname.startsWith('/account')

  return (
    <div className="sticky top-0 z-30 -mx-4 px-4 pt-[max(0.5rem,env(safe-area-inset-top))]">
      <header className="glass-strong flex h-12 items-center justify-between rounded-full pl-4 pr-1.5">
        <span className="font-display text-[17px] leading-none text-ink">{title}</span>
        {loading ? (
          <span className="h-9 w-9 rounded-full bg-hairline/60" aria-hidden />
        ) : user ? (
          <Link
            to="/account"
            aria-label={`Account: ${user.display_name}`}
            aria-current={onAccount ? 'page' : undefined}
            className={[
              'flex items-center gap-2 rounded-full py-0.5 pl-2.5 pr-0.5 text-sm text-ink transition duration-150',
              onAccount ? 'bg-primary-light/70' : 'hover:bg-card/60',
            ].join(' ')}
          >
            <span className="max-w-24 truncate text-[13px] font-medium">{user.display_name}</span>
            <AvatarChip name={user.display_name} color={user.avatar} />
          </Link>
        ) : (
          <Link
            to="/login"
            className="rounded-full bg-primary-light px-3.5 py-1.5 text-[13px] font-semibold text-primary transition duration-150 hover:brightness-95"
          >
            Log in
          </Link>
        )}
      </header>
    </div>
  )
}
