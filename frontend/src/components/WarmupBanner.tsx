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

        const models = data.models
        const stillCold = Object.values(models).some(isCold)
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
      <div className="rounded-xl border border-hairline bg-cream px-3 py-2 text-sm text-muted">
        Models unavailable: {error}
      </div>
    )
  }

  if (!health) {
    return (
      <div className="rounded-xl border border-hairline bg-cream px-3 py-2 text-sm text-muted">
        Checking model status…
      </div>
    )
  }

  if (health.mock_ml) {
    return (
      <div className="rounded-xl border border-hairline bg-cream px-3 py-2 text-sm text-muted">
        Using placeholder labels (mock ML).
      </div>
    )
  }

  const loading = (Object.keys(LABELS) as (keyof typeof LABELS)[]).filter(
    (key) => isCold(health.models[key]),
  )
  const failed = (Object.keys(LABELS) as (keyof typeof LABELS)[]).filter(
    (key) => health.models[key] === 'failed',
  )

  if (loading.length === 0 && failed.length === 0) return null

  return (
    <div className="rounded-xl border border-hairline bg-cream px-3 py-2 text-sm text-muted animate-in">
      {loading.length > 0 ? (
        <p>Warming up {loading.map((k) => LABELS[k]).join(', ')}…</p>
      ) : null}
      {failed.length > 0 ? (
        <p className="mt-0.5">
          Failed: {failed.map((k) => LABELS[k]).join(', ')}. Ranking still uses
          description, location, and time.
        </p>
      ) : null}
    </div>
  )
}
