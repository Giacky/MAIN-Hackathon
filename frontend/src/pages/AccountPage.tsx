import { useEffect, useState } from 'react'
import {
  ensureServiceWorker,
  fetchVapidPublicKey,
  subscribePush,
  unsubscribePush,
  urlBase64ToUint8Array,
} from '../api/push'
import { useAuth } from '../auth/AuthContext'
import { RedirectToLogin } from '../auth/RedirectToLogin'
import { AvatarChip } from '../components/TopBar'
import { Button } from '../components/ui/Button'

type NotifyState = 'unknown' | 'unsupported' | 'denied' | 'off' | 'on' | 'busy'

export function AccountPage() {
  const { user, loading, logout } = useAuth()
  const [notifyState, setNotifyState] = useState<NotifyState>('unknown')
  const [notifyError, setNotifyError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) return
    if (!('Notification' in window) || !('serviceWorker' in navigator)) {
      setNotifyState('unsupported')
      return
    }
    if (Notification.permission === 'denied') {
      setNotifyState('denied')
      return
    }
    ;(async () => {
      try {
        const reg = await ensureServiceWorker()
        const sub = await reg?.pushManager.getSubscription()
        setNotifyState(sub ? 'on' : 'off')
      } catch {
        setNotifyState(Notification.permission === 'granted' ? 'off' : 'off')
      }
    })()
  }, [user])

  async function enableNotify() {
    setNotifyError(null)
    setNotifyState('busy')
    try {
      if (!('Notification' in window)) {
        setNotifyState('unsupported')
        return
      }
      const permission = await Notification.requestPermission()
      if (permission === 'denied') {
        setNotifyState('denied')
        return
      }
      if (permission !== 'granted') {
        setNotifyState('off')
        return
      }
      const vapid = await fetchVapidPublicKey()
      if (!vapid.configured || !vapid.public_key) {
        // Foreground browser notifications still work via AlertsContext.
        setNotifyState('on')
        return
      }
      const reg = await ensureServiceWorker()
      if (!reg) {
        setNotifyState('unsupported')
        return
      }
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapid.public_key) as BufferSource,
      })
      await subscribePush(sub.toJSON())
      setNotifyState('on')
    } catch (err) {
      setNotifyError(err instanceof Error ? err.message : 'Could not enable notifications')
      setNotifyState('off')
    }
  }

  async function disableNotify() {
    setNotifyError(null)
    setNotifyState('busy')
    try {
      const reg = await ensureServiceWorker()
      const sub = await reg?.pushManager.getSubscription()
      if (sub) {
        try {
          await unsubscribePush(sub.endpoint)
        } catch {
          /* still drop local subscription */
        }
        await sub.unsubscribe()
      }
      setNotifyState('off')
    } catch (err) {
      setNotifyError(err instanceof Error ? err.message : 'Could not turn off notifications')
      setNotifyState('on')
    }
  }

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

      <section className="glass space-y-2 px-4 py-4">
        <h2 className="font-display text-lg text-ink">Notifications</h2>
        <p className="text-sm text-muted">
          Get a browser alert for new matches and messages. If permission is denied, the in-app badge
          still works.
        </p>
        {notifyState === 'unsupported' ? (
          <p className="text-sm text-muted">This browser does not support notifications.</p>
        ) : notifyState === 'denied' ? (
          <p className="text-sm text-muted">
            Permission denied in the browser. You will still see the in-app badge.
          </p>
        ) : notifyState === 'on' ? (
          <Button variant="secondary" disabled={false} onClick={() => void disableNotify()}>
            Notifications on · turn off
          </Button>
        ) : (
          <Button
            variant="primary"
            disabled={notifyState === 'busy'}
            onClick={() => void enableNotify()}
          >
            {notifyState === 'busy' ? 'Working…' : 'Notify me'}
          </Button>
        )}
        {notifyError ? <p className="text-sm text-accent">{notifyError}</p> : null}
      </section>
    </div>
  )
}
