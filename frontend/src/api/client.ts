import type { ApiErrorBody } from './types'

const FETCH_TIMEOUT_MS = 3 * 60 * 1000

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function parseError(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as ApiErrorBody
    if (body?.detail) return String(body.detail)
  } catch {
    /* ignore */
  }
  return res.statusText || `Request failed (${res.status})`
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)

  try {
    const headers = new Headers(init.headers)
    if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json')
    }

    const res = await fetch(path, {
      ...init,
      headers,
      credentials: 'include',
      signal: controller.signal,
    })

    if (!res.ok) {
      throw new ApiError(res.status, await parseError(res))
    }

    if (res.status === 204) {
      return undefined as T
    }

    return (await res.json()) as T
  } catch (err) {
    if (err instanceof ApiError) throw err
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError(408, 'Request timed out after 3 minutes')
    }
    throw err
  } finally {
    window.clearTimeout(timer)
  }
}
