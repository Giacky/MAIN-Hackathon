import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError, apiFetch } from '../api/client'
import type {
  ClassificationResult,
  LocationPin,
  Preset,
  Report,
  ReportType,
} from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { RedirectToLogin } from '../auth/RedirectToLogin'
import { LocationMap } from '../components/LocationMap'
import { Button } from '../components/ui/Button'
import { Input, TextArea } from '../components/ui/Input'

function toLocalInputValue(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function ReportPage() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const initialType = params.get('type') === 'found' ? 'found' : 'lost'

  const [reportType, setReportType] = useState<ReportType>(initialType)
  const [description, setDescription] = useState('')
  const [eventTime, setEventTime] = useState(toLocalInputValue(new Date()))
  const [preferAnonymous, setPreferAnonymous] = useState(false)
  const [contactPhone, setContactPhone] = useState('')
  const [holdingNote, setHoldingNote] = useState('')
  const [radiusMeters, setRadiusMeters] = useState(200)
  const [pins, setPins] = useState<LocationPin[]>([])
  const [files, setFiles] = useState<File[]>([])
  const [presets, setPresets] = useState<Preset[]>([])
  const [presetId, setPresetId] = useState('')
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setReportType(initialType)
  }, [initialType])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const data = await apiFetch<{ presets: Preset[] }>('/api/demo/presets')
        if (!cancelled) setPresets(data.presets ?? [])
      } catch {
        /* presets optional */
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  // Object URLs for the chosen files; revoked when the selection changes.
  const previews = useMemo(() => files.map((f) => URL.createObjectURL(f)), [files])
  useEffect(() => {
    return () => previews.forEach((u) => URL.revokeObjectURL(u))
  }, [previews])

  const preset = presets.find((p) => p.id === presetId) ?? null

  if (loading) {
    return <p className="text-sm text-muted">Loading…</p>
  }
  if (!user) {
    return <RedirectToLogin />
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('report_type', reportType)
      form.append('description', description.trim())
      form.append('event_time', new Date(eventTime).toISOString())
      form.append('prefer_anonymous', preferAnonymous ? 'true' : 'false')
      if (contactPhone.trim()) form.append('contact_phone', contactPhone.trim())
      if (holdingNote.trim()) form.append('holding_note', holdingNote.trim())
      form.append('locations', JSON.stringify(pins))
      if (presetId) form.append('sample_preset_id', presetId)
      files.forEach((f) => form.append('images', f))

      const data = await apiFetch<{
        report: Report
        classification: ClassificationResult
      }>('/api/reports', { method: 'POST', body: form })

      const category = data.classification.category
      const label =
        category && !/mock|unclassified/i.test(category) ? category.toLowerCase() : null
      navigate(`/matches?report=${encodeURIComponent(data.report.id)}`, {
        state: { toast: label ? `Saved · classified as ${label}` : 'Report saved' },
      })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save report')
      setBusy(false)
    }
  }

  function applyPreset(id: string) {
    if (id === presetId) {
      setPresetId('')
      return
    }
    setPresetId(id)
    const next = presets.find((p) => p.id === id)
    if (!next) return
    setReportType(next.report_type)
    setDescription(next.description)
    setPins([
      {
        latitude: next.latitude,
        longitude: next.longitude,
        radius_meters: next.radius_meters,
      },
    ])
    setRadiusMeters(next.radius_meters)
  }

  function onFiles(list: FileList | null) {
    setFiles(list ? Array.from(list) : [])
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const hasPhoto = files.length > 0 || Boolean(preset)
  const isLost = reportType === 'lost'

  return (
    <div className="space-y-5 animate-in">
      <header>
        <h1 className="font-display text-2xl text-ink">
          {isLost ? 'What did you lose?' : 'What did you find?'}
        </h1>
        <p className="mt-1 text-sm text-muted">
          Start with a photo. Contact email is {user.email}.
        </p>
      </header>

      <form className="space-y-5" onSubmit={(e) => void onSubmit(e)}>
        {/* 1. Type */}
        <div className="glass flex gap-1 rounded-full p-1" role="radiogroup" aria-label="Report type">
          {(['lost', 'found'] as const).map((t) => {
            const on = reportType === t
            return (
              <button
                key={t}
                type="button"
                role="radio"
                aria-checked={on}
                onClick={() => setReportType(t)}
                className={[
                  'flex-1 rounded-full py-2.5 text-sm font-semibold transition-colors duration-200',
                  on
                    ? t === 'lost'
                      ? 'bg-accent text-white shadow-[inset_0_1px_0_rgba(255,255,255,.3)]'
                      : 'bg-primary text-white shadow-[inset_0_1px_0_rgba(255,255,255,.25)]'
                    : 'text-muted hover:text-ink',
                ].join(' ')}
              >
                {t === 'lost' ? 'I lost it' : 'I found it'}
              </button>
            )
          })}
        </div>

        {/* 2. Photos */}
        <section className="space-y-2.5">
          <div className="flex items-baseline justify-between">
            <span className="text-sm font-medium text-ink">Photos</span>
            <span className="text-xs text-muted">{hasPhoto ? 'Looks good' : 'Recommended'}</span>
          </div>

          <div className="flex gap-2.5 overflow-x-auto no-scrollbar pb-1">
            <label
              className={[
                'glass flex h-24 w-24 shrink-0 cursor-pointer flex-col items-center justify-center gap-1 rounded-2xl text-xs font-medium transition duration-150 hover:bg-card/75 active:scale-[0.98]',
                isLost ? 'text-accent' : 'text-primary',
              ].join(' ')}
            >
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path
                  d="M4 8.5A2.5 2.5 0 0 1 6.5 6h1.3l1.2-2h6l1.2 2h1.3A2.5 2.5 0 0 1 20 8.5v8A2.5 2.5 0 0 1 17.5 19h-11A2.5 2.5 0 0 1 4 16.5v-8Z"
                  stroke="currentColor"
                  strokeWidth="1.75"
                  strokeLinejoin="round"
                />
                <circle cx="12" cy="12.5" r="3" stroke="currentColor" strokeWidth="1.75" />
              </svg>
              {files.length ? 'Change' : 'Add photo'}
              <input
                type="file"
                accept="image/*"
                multiple
                className="sr-only"
                onChange={(e) => onFiles(e.target.files)}
              />
            </label>

            {previews.map((src, i) => (
              <div key={src} className="relative h-24 w-24 shrink-0 overflow-hidden rounded-2xl">
                <img src={src} alt="" className="h-full w-full object-cover" />
                <button
                  type="button"
                  aria-label="Remove photo"
                  onClick={() => removeFile(i)}
                  className="absolute right-1.5 top-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-ink/60 text-white backdrop-blur-md transition duration-150 hover:bg-ink/80"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden>
                    <path d="M6 6l12 12M18 6 6 18" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
                  </svg>
                </button>
              </div>
            ))}

            {preset && files.length === 0 ? (
              <div className="relative h-24 w-24 shrink-0 overflow-hidden rounded-2xl ring-2 ring-primary/40">
                <img src={preset.image_url} alt="" className="h-full w-full object-cover" />
                <span className="absolute inset-x-0 bottom-0 bg-ink/55 px-1.5 py-0.5 text-center text-[10px] font-medium text-white backdrop-blur-md">
                  Sample
                </span>
              </div>
            ) : null}
          </div>

          {presets.length > 0 ? (
            <div className="space-y-1.5">
              <span className="text-xs font-medium text-muted">Try a sample</span>
              <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1">
                {presets.map((p) => {
                  const on = p.id === presetId
                  return (
                    <button
                      key={p.id}
                      type="button"
                      aria-pressed={on}
                      onClick={() => applyPreset(p.id)}
                      className={[
                        'flex w-[5.5rem] shrink-0 flex-col gap-1 rounded-2xl border p-1 text-left transition duration-150 active:scale-[0.98]',
                        on
                          ? 'border-primary/50 bg-primary-light/70'
                          : 'border-white/60 bg-card/50 hover:bg-card/70',
                      ].join(' ')}
                    >
                      <img
                        src={p.image_url}
                        alt=""
                        className="aspect-square w-full rounded-xl object-cover"
                      />
                      <span className="flex items-center gap-1 px-1 pb-0.5">
                        <span
                          className={`h-1.5 w-1.5 shrink-0 rounded-full ${p.report_type === 'lost' ? 'bg-accent' : 'bg-primary'}`}
                          aria-hidden
                        />
                        <span className="truncate text-[11px] leading-tight text-ink">{p.label}</span>
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          ) : null}
        </section>

        {/* 3. Description */}
        <TextArea
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required
          rows={3}
          className="min-h-24"
          placeholder={
            isLost
              ? 'Black leather wallet, lost near the library…'
              : 'Silver keys on a red lanyard, found by the station…'
          }
        />

        {/* 4. Location */}
        <div>
          <p className="mb-2 text-sm font-medium text-ink">
            {isLost ? 'Where you last had it' : 'Where you found it'}
          </p>
          <LocationMap
            mode="edit"
            variant={reportType}
            pins={pins}
            radiusMeters={radiusMeters}
            onRadiusChange={setRadiusMeters}
            onAdd={(pin) => setPins((prev) => [...prev, pin])}
            onRemove={(index) => setPins((prev) => prev.filter((_, i) => i !== index))}
            onClear={() => setPins([])}
          />
        </div>

        {/* 5. When */}
        <Input
          label="When"
          type="datetime-local"
          value={eventTime}
          onChange={(e) => setEventTime(e.target.value)}
          required
        />

        {/* 6. Details (collapsed) */}
        <div className="glass overflow-hidden">
          <button
            type="button"
            aria-expanded={detailsOpen}
            onClick={() => setDetailsOpen((o) => !o)}
            className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-ink"
          >
            <span>
              Details
              <span className="ml-2 text-xs font-normal text-muted">
                {[
                  preferAnonymous ? 'anonymous' : null,
                  contactPhone.trim() ? 'phone' : null,
                  holdingNote.trim() ? 'holding note' : null,
                ]
                  .filter(Boolean)
                  .join(' · ') || 'optional'}
              </span>
            </span>
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden
              className={`text-muted transition-transform duration-200 ${detailsOpen ? 'rotate-180' : ''}`}
            >
              <path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          {detailsOpen ? (
            <div className="space-y-3 border-t border-white/60 px-4 pb-4 pt-3 animate-in">
              <label className="flex items-center gap-2.5 text-sm text-ink">
                <input
                  type="checkbox"
                  checked={preferAnonymous}
                  onChange={(e) => setPreferAnonymous(e.target.checked)}
                  className="h-4 w-4 accent-primary"
                />
                Hide my contact from matches
              </label>
              <Input
                label="Phone (optional)"
                type="tel"
                value={contactPhone}
                onChange={(e) => setContactPhone(e.target.value)}
              />
              {reportType === 'found' ? (
                <TextArea
                  label="Holding note"
                  value={holdingNote}
                  onChange={(e) => setHoldingNote(e.target.value)}
                  rows={2}
                  className="min-h-20"
                  placeholder="At the library desk."
                />
              ) : null}
            </div>
          ) : null}
        </div>

        {error ? <p className="text-sm text-accent">{error}</p> : null}

        <Button
          type="submit"
          fullWidth
          variant={isLost ? 'accent' : 'primary'}
          disabled={busy || !description.trim()}
        >
          {busy ? 'Saving…' : isLost ? 'Save lost report' : 'Save found report'}
        </Button>
      </form>
    </div>
  )
}
