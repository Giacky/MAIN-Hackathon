import { useAuth } from '../auth/AuthContext'
import { RedirectToLogin } from '../auth/RedirectToLogin'
import { AvatarChip } from '../components/TopBar'
import { Button } from '../components/ui/Button'

export function AccountPage() {
  const { user, loading, logout } = useAuth()

  if (loading) {
    return <p className="text-sm text-muted">Loading account…</p>
  }

  if (!user) {
    return <RedirectToLogin />
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
    </div>
  )
}
