import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import {
  fetchNotifications,
  isUnreadNotification,
  markAllNotificationsRead,
  markNotificationRead,
} from '../api/alerts'
import { ApiError } from '../api/client'
import type { MatchNotification, NotificationsResponse } from '../api/types'
import { useAuth } from './AuthContext'

const POLL_MS = 8000

interface AlertsContextValue {
  notifications: MatchNotification[]
  unreadCount: number
  refresh: () => Promise<void>
  markRead: (id: string) => Promise<void>
  markReadForReport: (reportId: string) => Promise<void>
  markAllRead: () => Promise<void>
}

const AlertsContext = createContext<AlertsContextValue | null>(null)

function withReadAt(list: MatchNotification[], ids: ReadonlySet<string>): MatchNotification[] {
  const now = new Date().toISOString()
  return list.map((n) => (ids.has(n.id) ? { ...n, read_at: n.read_at ?? now } : n))
}

function unreadFromPayload(data: NotificationsResponse, marked: ReadonlySet<string>): number {
  const stillUnreadOnServer = data.notifications.filter(
    (n) => marked.has(n.id) && isUnreadNotification(n),
  ).length
  if (typeof data.unread_count === 'number') {
    return Math.max(0, data.unread_count - stillUnreadOnServer)
  }
  return data.notifications.filter((n) => !marked.has(n.id) && isUnreadNotification(n)).length
}

export function AlertsProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [notifications, setNotifications] = useState<MatchNotification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const notificationsRef = useRef(notifications)
  notificationsRef.current = notifications
  const markedIdsRef = useRef(new Set<string>())

  const applyPayload = useCallback((data: NotificationsResponse) => {
    const marked = markedIdsRef.current
    setNotifications(
      data.notifications.map((n) =>
        marked.has(n.id) && isUnreadNotification(n) ? { ...n, read_at: n.read_at ?? new Date().toISOString() } : n,
      ),
    )
    setUnreadCount(unreadFromPayload(data, marked))
  }, [])

  const refresh = useCallback(async () => {
    const data = await fetchNotifications()
    applyPayload(data)
  }, [applyPayload])

  useEffect(() => {
    if (!user) {
      markedIdsRef.current = new Set()
      setNotifications([])
      setUnreadCount(0)
      return
    }

    let cancelled = false
    let timer: number | undefined
    let inFlight = false

    async function tick() {
      if (inFlight) {
        if (!cancelled) timer = window.setTimeout(tick, POLL_MS)
        return
      }
      inFlight = true
      let stop = false
      try {
        const data = await fetchNotifications()
        if (!cancelled) applyPayload(data)
      } catch (err) {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 401) {
          setNotifications([])
          setUnreadCount(0)
          stop = true
          return
        }
      } finally {
        inFlight = false
        if (!cancelled && !stop) timer = window.setTimeout(tick, POLL_MS)
      }
    }

    void tick()
    return () => {
      cancelled = true
      if (timer !== undefined) window.clearTimeout(timer)
    }
  }, [user, applyPayload])

  const markRead = useCallback(async (id: string) => {
    if (!markedIdsRef.current.has(id)) {
      markedIdsRef.current.add(id)
      setNotifications((prev) => withReadAt(prev, new Set([id])))
      setUnreadCount((count) => Math.max(0, count - 1))
    }
    try {
      const data = await markNotificationRead(id)
      setNotifications((prev) =>
        prev.map((n) => (n.id === data.notification.id ? { ...n, ...data.notification } : n)),
      )
      setUnreadCount(data.unread_count)
    } catch (err) {
      markedIdsRef.current.delete(id)
      throw err
    }
  }, [])

  const markReadForReport = useCallback(async (reportId: string) => {
    const related = notificationsRef.current.filter(
      (n) =>
        !markedIdsRef.current.has(n.id) &&
        isUnreadNotification(n) &&
        (n.lost_report_id === reportId || n.found_report_id === reportId || n.report_id === reportId),
    )
    if (related.length === 0) return
    for (const n of related) markedIdsRef.current.add(n.id)
    const ids = new Set(related.map((n) => n.id))
    setNotifications((prev) => withReadAt(prev, ids))
    setUnreadCount((count) => Math.max(0, count - related.length))
    await Promise.all(related.map((n) => markNotificationRead(n.id)))
    const data = await fetchNotifications()
    applyPayload(data)
  }, [applyPayload])

  const markAllRead = useCallback(async () => {
    const unread = notificationsRef.current.filter(
      (n) => !markedIdsRef.current.has(n.id) && isUnreadNotification(n),
    )
    if (unread.length === 0) return
    for (const n of unread) markedIdsRef.current.add(n.id)
    setNotifications((prev) => withReadAt(prev, new Set(unread.map((n) => n.id))))
    setUnreadCount(0)
    const data = await markAllNotificationsRead()
    applyPayload(data)
  }, [applyPayload])

  const value = useMemo(
    () => ({ notifications, unreadCount, refresh, markRead, markReadForReport, markAllRead }),
    [notifications, unreadCount, refresh, markRead, markReadForReport, markAllRead],
  )

  return <AlertsContext.Provider value={value}>{children}</AlertsContext.Provider>
}

export function useAlerts(): AlertsContextValue {
  const ctx = useContext(AlertsContext)
  if (!ctx) throw new Error('useAlerts must be used within AlertsProvider')
  return ctx
}
