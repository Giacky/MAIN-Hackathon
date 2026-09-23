import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ApiError, apiFetch } from '../api/client'
import type {
  ClassificationResult,
  LocationPin,
  Preset,
  Report,
  ReportType,
} from '../api/types'
import { LocationMap } from '../components/LocationMap'
import { Button } from '../components/ui/Button'
import { Input, TextArea } from '../components/ui/Input'

function toLocalInputValue(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function toastFor(classification?: ClassificationResult | null): string {
  const category = classification?.category
  const label = category && !/mock|unclassified/i.test(category) ? category.toLowerCase() : null
  return label ? `Saved · classified as ${label}` : 'Report saved'
}

export function ReportPage() {
  const navigate = useNavigate()
  const { id: routeId } = useParams()
  const [params] = useSearchParams()
  const editId = routeId ?? params.get('id')
  const isEdit = Boolean(editId)
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
  const [existingImages, setExistingImages] = useState<string[]>([])
  const [presets, setPresets] = useState<Preset[]>([])
  const [presetId, setPresetId] = useState('')
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [samplesOpen, setSamplesOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [loadingEdit, setLoadingEdit] = useState(isEdit)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isEdit) return
    setReportType(initialType)
  }, [initialType, isEdit])

  useEffect(() => {
    if (isEdit) return
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
  }, [isEdit])

  useEffect(() => {
    if (!editId) {
      setLoadingEdit(false)
      return
    }
    let cancelled = false
    setLoadingEdit(true)
    ;(async () => {
      try {
        const data = await apiFetch<{ report: Report }>(`/api/reports/${encodeURIComponent(editId)}`)
        if (cancelled) return
        const r = data.report
        if (r.status !== 'open') {
          navigate(`/reports/${encodeURIComponent(editId)}`, {
            replace: true,
            state: { toast: 'Only open reports can be edited.' },
          })
          return
        }
        setReportType(r.report_type)
        setDescription(r.description)
        setEventTime(toLocalInputValue(new Date(r.event_time)))
        setPreferAnonymous(r.prefer_anonymous)
        setContactPhone(r.contact_phone ?? '')
        setHoldingNote(r.holding_note ?? '')
        const nextPins =
          r.locations?.length > 0
            ? r.locations
            : r.latitude != null && r.longitude != null
              ? [
                  {
                    latitude: r.latitude,
                    longitude: r.longitude,
                    radius_meters: r.radius_meters ?? 200,
                  },
                ]
              : []
        setPins(nextPins)
        if (nextPins[0]) setRadiusMeters(nextPins[0].radius_meters)
        setExistingImages(r.image_urls ?? [])
        setDetailsOpen(Boolean(r.prefer_anonymous || r.contact_phone || r.holding_note))
        setError(null)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Failed to load report')
      } finally {
        if (!cancelled) setLoadingEdit(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [editId])

  const previews = useMemo(() => files.map((f) => URL.createObjectURL(f)), [files])
  useEffect(() => {
    return () => previews.forEach((u) => URL.revokeObjectURL(u))
  }, [previews])

  const preset = presets.find((p) => p.id === presetId) ?? null

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
      form.append('contact_phone', contactPhone.trim())
      form.append('holding_note', holdingNote.trim())
      form.append('locations', JSON.stringify(pins))
      if (!isEdit && presetId) form.append('sample_preset_id', presetId)
      files.forEach((f) => form.append('images', f))

      const path = isEdit ? `/api/reports/${encodeURIComponent(editId!)}` : '/api/reports'
      const data = await apiFetch<{
        report: Report
        classification?: ClassificationResult
      }>(path, { method: isEdit ? 'PATCH' : 'POST', body: form })

      navigate(`/reports/${encodeURIComponent(data.report.id)}`, {
        state: { toast: toastFor(data.classification) },
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

  const hasPhoto = files.length > 0 || Boolean(preset) || existingImages.length > 0
  const isLost = reportType === 'lost'

  if (loadingEdit) {
    return <p className="text-sm text-muted">Loading report…</p>
  }

  return (
    <div className="space-y-5 animate-in">
      {isEdit && editId ? (
        <Link to={`/reports/${editId}`} className="inline-block text-sm font-medium text-primary">
          Back
        </Link>
      ) : null}

      <form className="space-y-5" onSubmit={(e) => void onSubmit(e)}>
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
              {files.length ? 'Change' : isEdit ? 'Add more' : 'Add photo'}
              <input
                type="file"
                accept="image/*"
                multiple
                className="sr-only"
                onChange={(e) => onFiles(e.target.files)}
              />
            </label>

            {existingImages.map((src) => (
              <div key={src} className="relative h-24 w-24 shrink-0 overflow-hidden rounded-2xl">
                <img src={src} alt="" className="h-full w-full object-cover" />
                <span className="absolute inset-x-0 bottom-0 bg-ink/55 px-1.5 py-0.5 text-center text-[10px] font-medium text-white backdrop-blur-md">
                  Current
                </span>
              </div>
            ))}

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

          {!isEdit && presets.length > 0 ? (
            <div className="glass overflow-hidden">
              <button
                type="button"
                aria-expanded={samplesOpen}
                onClick={() => setSamplesOpen((o) => !o)}
                className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-ink"
              >
                <span>
                  Try a sample
                  <span className="ml-2 text-xs font-normal text-muted">
                    {preset ? preset.label : 'optional demo photos'}
                  </span>
                </span>
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  aria-hidden
                  className={`text-muted transition-transform duration-200 ${samplesOpen ? 'rotate-180' : ''}`}
                >
                  <path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
              {samplesOpen ? (
                <div className="flex gap-2 overflow-x-auto no-scrollbar border-t border-white/60 px-3 py-3 animate-in">
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
                        <img src={p.image_url} alt="" className="aspect-square w-full rounded-xl object-cover" />
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
              ) : null}
            </div>
          ) : null}
        </section>

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

        <Input
          label="When"
          type="datetime-local"
          value={eventTime}
          onChange={(e) => setEventTime(e.target.value)}
          required
        />

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
          {busy ? 'Saving…' : isEdit ? 'Save changes' : isLost ? 'Save lost report' : 'Save found report'}
        </Button>
      </form>
    </div>
  )
}
