import { apiFetch } from './client'
import type {
  MatchNotification,
  NotificationReadResponse,
  NotificationsResponse,
} from './types'

export function isUnreadNotification(n: MatchNotification): boolean {
  return n.read_at == null || n.read_at === ''
}

export async function fetchNotifications(): Promise<NotificationsResponse> {
  return apiFetch<NotificationsResponse>('/api/notifications')
}

export async function markNotificationRead(id: string): Promise<NotificationReadResponse> {
  return apiFetch<NotificationReadResponse>(`/api/notifications/${encodeURIComponent(id)}/read`, {
    method: 'POST',
  })
}

export async function markAllNotificationsRead(): Promise<NotificationsResponse> {
  return apiFetch<NotificationsResponse>('/api/notifications/read-all', { method: 'POST' })
}

export async function dismissMatch(lostReportId: string, foundReportId: string): Promise<void> {
  await apiFetch('/api/matches/dismiss', {
    method: 'PATCH',
    body: JSON.stringify({ lost_report_id: lostReportId, found_report_id: foundReportId }),
  })
}

export async function closeReport(reportId: string): Promise<void> {
  await apiFetch(`/api/reports/${encodeURIComponent(reportId)}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status: 'closed' }),
  })
}
