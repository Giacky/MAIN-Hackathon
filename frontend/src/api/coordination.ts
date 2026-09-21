import { ApiError, apiFetch } from './client'
import type { CoordinationThread } from './types'

/**
 * Lists the viewer's active pickup threads. Returns an empty list when the
 * endpoint is not available yet (404) so pages can render their empty state.
 */
export async function fetchThreads(): Promise<CoordinationThread[]> {
  try {
    const data = await apiFetch<{ threads?: CoordinationThread[] } | CoordinationThread[]>(
      '/api/coordination',
    )
    return Array.isArray(data) ? data : (data.threads ?? [])
  } catch (err) {
    if (err instanceof ApiError && (err.status === 404 || err.status === 405)) return []
    throw err
  }
}

export function threadKey(lostId: string, foundId: string): string {
  return `${lostId}::${foundId}`
}
