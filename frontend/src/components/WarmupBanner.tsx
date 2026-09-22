import { useEffect, useRef, useState } from 'react'
import { ApiError, apiFetch } from '../api/client'
import type { HealthResponse, ModelState } from '../api/types'

const LABELS: Record<keyof HealthResponse['models'], string> = {
  classifier: 'labels',
  text: 'description similarity',
  dino: 'visual shortlist',
  features: 'feature matching',
  segmenter: 'foreground crop',
}

function isCold(state: ModelState): boolean {
  return state === 'idle' || state === 'warming'
}

/** Compact one-line status, shown on Home only while models are warming. */
export function WarmupBanner() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const started = useRef(false)

  useEffect(() => {
    let cancelled = false
    let timer: number | undefined

    async function poll() {
      try {
        const data = await apiFetch<HealthResponse>('/api/health')
        if (cancelled) return
        setHealth(data)
        setError(null)

        if (data.mock_ml) return

        const stillCold = Object.values(data.models).some(isCold)
        if (stillCold) {
          timer = window.setTimeout(poll, 2000)
        }
      } catch (err) {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Could not reach health endpoint')
        timer = window.setTimeout(poll, 4000)
      }
    }

    async function start() {
      if (!started.current) {
        started.current = true
        try {
          await apiFetch<{ state: string }>('/api/health/warmup', { method: 'POST' })
        } catch {
          /* warmup is best-effort; polling still runs */
        }
      }
      await poll()
    }

    void start()
    return () => {
      cancelled = true
      if (timer) window.clearTimeout(timer)
    }
  }, [])

  if (error) {
    return (
      <div className="glass flex items-center gap-2 rounded-full px-3 py-1.5 text-xs text-muted">
        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden />
        <p className="min-w-0 truncate">Models unavailable</p>
      </div>
    )
  }

  if (!health || health.mock_ml) return null

  const loading = (Object.keys(LABELS) as (keyof typeof LABELS)[]).filter((key) =>
    isCold(health.models[key]),
  )
  const failed = (Object.keys(LABELS) as (keyof typeof LABELS)[]).filter(
    (key) => health.models[key] === 'failed',
  )

  if (loading.length === 0 && failed.length === 0) return null

  return (
    <div className="glass flex items-center gap-2 rounded-full px-3 py-1.5 text-xs text-muted animate-in">
      <span
        className={`h-1.5 w-1.5 shrink-0 rounded-full ${loading.length > 0 ? 'bg-primary animate-pulse' : 'bg-accent'}`}
        aria-hidden
      />
      <p className="min-w-0 truncate">
        {loading.length > 0
          ? `Warming ${loading.map((k) => LABELS[k]).join(', ')}…`
          : `Failed: ${failed.map((k) => LABELS[k]).join(', ')}. Ranking still uses description, place, and time.`}
      </p>
    </div>
  )
}
