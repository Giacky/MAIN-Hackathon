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

const bannerClass = 'glass flex items-start gap-2.5 rounded-2xl px-3.5 py-2.5 text-sm text-muted'

function Dot({ tone }: { tone: 'muted' | 'accent' | 'success' | 'primary' }) {
  const color =
    tone === 'success'
      ? 'bg-success'
      : tone === 'accent'
        ? 'bg-accent'
        : tone === 'primary'
          ? 'bg-primary animate-pulse'
          : 'bg-muted/60'
  return <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${color}`} aria-hidden />
}

export function WarmupBanner() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [justReady, setJustReady] = useState(false)
  const started = useRef(false)
  const sawCold = useRef(false)

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
          sawCold.current = true
          timer = window.setTimeout(poll, 2000)
        } else if (sawCold.current) {
          sawCold.current = false
          setJustReady(true)
          timer = window.setTimeout(() => setJustReady(false), 3000)
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
      <div className={bannerClass}>
        <Dot tone="accent" />
        <p>Models unavailable: {error}</p>
      </div>
    )
  }

  if (!health) {
    return (
      <div className={bannerClass}>
        <Dot tone="muted" />
        <p>Checking model status…</p>
      </div>
    )
  }

  if (health.mock_ml) {
    return (
      <div className={bannerClass}>
        <Dot tone="muted" />
        <p>Using placeholder labels (mock ML).</p>
      </div>
    )
  }

  const loading = (Object.keys(LABELS) as (keyof typeof LABELS)[]).filter((key) =>
    isCold(health.models[key]),
  )
  const failed = (Object.keys(LABELS) as (keyof typeof LABELS)[]).filter(
    (key) => health.models[key] === 'failed',
  )

  if (loading.length === 0 && failed.length === 0) {
    if (!justReady) return null
    return (
      <div className={`${bannerClass} animate-in text-success`}>
        <Dot tone="success" />
        <p>Models ready. Photo, text, place, and time all count.</p>
      </div>
    )
  }

  return (
    <div className={`${bannerClass} animate-in`}>
      <Dot tone={loading.length > 0 ? 'primary' : 'accent'} />
      <div>
        {loading.length > 0 ? <p>Warming up {loading.map((k) => LABELS[k]).join(', ')}…</p> : null}
        {failed.length > 0 ? (
          <p className="mt-0.5">
            Failed: {failed.map((k) => LABELS[k]).join(', ')}. Ranking still uses description,
            location, and time.
          </p>
        ) : null}
      </div>
    </div>
  )
}
