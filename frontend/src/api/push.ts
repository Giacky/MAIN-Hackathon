import { apiFetch } from './client'

export interface VapidPublicResponse {
  public_key: string | null
  configured: boolean
}

export async function fetchVapidPublicKey(): Promise<VapidPublicResponse> {
  return apiFetch<VapidPublicResponse>('/api/push/vapid-public-key')
}

export async function subscribePush(subscription: PushSubscriptionJSON): Promise<void> {
  const keys = subscription.keys
  if (!subscription.endpoint || !keys?.p256dh || !keys?.auth) {
    throw new Error('Incomplete push subscription')
  }
  await apiFetch('/api/push/subscribe', {
    method: 'POST',
    body: JSON.stringify({
      endpoint: subscription.endpoint,
      keys: { p256dh: keys.p256dh, auth: keys.auth },
    }),
  })
}

export async function unsubscribePush(endpoint: string): Promise<void> {
  await apiFetch('/api/push/unsubscribe', {
    method: 'POST',
    body: JSON.stringify({ endpoint }),
  })
}

/** Convert a URL-safe base64 VAPID key to a Uint8Array for PushManager.subscribe. */
export function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  const output = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i += 1) output[i] = raw.charCodeAt(i)
  return output
}

export async function ensureServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (!('serviceWorker' in navigator)) return null
  return navigator.serviceWorker.register('/sw.js')
}
