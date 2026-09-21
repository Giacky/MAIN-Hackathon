import { Navigate, useLocation } from 'react-router-dom'

/** Builds `/account?next=<path>` so the account page can return here after login. */
export function loginPath(pathname: string, search = ''): string {
  const next = `${pathname}${search}`
  if (!next || next === '/' || next.startsWith('/account')) return '/account'
  return `/account?next=${encodeURIComponent(next)}`
}

/** Only allow same-origin relative paths as a return target. */
export function safeNext(next: string | null): string | null {
  if (!next) return null
  if (!next.startsWith('/') || next.startsWith('//')) return null
  return next
}

export function RedirectToLogin() {
  const location = useLocation()
  return <Navigate to={loginPath(location.pathname, location.search)} replace />
}
