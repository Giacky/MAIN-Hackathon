import { Navigate, useLocation } from 'react-router-dom'

const AUTH_PREFIXES = ['/login', '/register']

function isAuthPath(path: string): boolean {
  return AUTH_PREFIXES.some((p) => path === p || path.startsWith(`${p}?`))
}

/** Builds `/login?next=<path>` so login can return here after the session exists. */
export function loginPath(pathname: string, search = ''): string {
  const next = `${pathname}${search}`
  if (!next || next === '/' || isAuthPath(next) || next.startsWith('/login') || next.startsWith('/register')) {
    return '/login'
  }
  return `/login?next=${encodeURIComponent(next)}`
}

/** Only allow same-origin relative paths as a return target. */
export function safeNext(next: string | null): string | null {
  if (!next) return null
  if (!next.startsWith('/') || next.startsWith('//')) return null
  if (next.startsWith('/login') || next.startsWith('/register')) return null
  return next
}

export function RedirectToLogin() {
  const location = useLocation()
  return <Navigate to={loginPath(location.pathname, location.search)} replace />
}
