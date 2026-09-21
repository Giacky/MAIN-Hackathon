import { useEffect, useState, type FormEvent } from 'react'
import { Link, Navigate, useSearchParams } from 'react-router-dom'
import { ApiError, apiFetch } from '../api/client'
import type {
  ClassificationResult,
  LocationPin,
  Preset,
  Report,
  ReportType,
} from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { LocationMap } from '../components/LocationMap'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input, TextArea } from '../components/ui/Input'

function toLocalInputValue(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function ReportPage() {
  const { user, loading } = useAuth()
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
  const [files, setFiles] = useState<FileList | null>(null)
  const [presets, setPresets] = useState<Preset[]>([])
  const [presetId, setPresetId] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [created, setCreated] = useState<{
    report: Report
    classification: ClassificationResult
  } | null>(null)

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

  if (loading) {
    return <p className="text-sm text-muted">Loading…</p>
  }
  if (!user) {
    return <Navigate to="/account" replace />
  }

  if (created) {
    return (
      <div className="space-y-4 animate-in">
        <h1 className="font-display text-2xl text-ink">Report saved</h1>
        <Card>
          <p className="text-sm text-muted">Classification</p>
          <p className="mt-1 text-ink">
            {created.classification.category ?? 'Unknown category'}
            {created.classification.urgency
              ? ` · ${created.classification.urgency}`
              : ''}
            {created.classification.is_mock ? ' (placeholder)' : ''}
          </p>
          <p className="mt-3 line-clamp-3 text-sm text-ink">
            {created.report.description}
          </p>
        </Card>
        <Link
          to={`/matches?report=${created.report.id}`}
          className="inline-flex w-full items-center justify-center rounded-xl bg-primary px-4 py-3 text-[15px] font-medium text-white"
        >
          See matches
        </Link>
        <Button variant="secondary" fullWidth onClick={() => setCreated(null)}>
          File another
        </Button>
      </div>
    )
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
      if (files) {
        Array.from(files).forEach((f) => form.append('images', f))
      }

      const data = await apiFetch<{
        report: Report
        classification: ClassificationResult
      }>('/api/reports', { method: 'POST', body: form })
      setCreated(data)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save report')
    } finally {
      setBusy(false)
    }
  }

  function applyPreset(id: string) {
    setPresetId(id)
    const preset = presets.find((p) => p.id === id)
    if (!preset) return
    setReportType(preset.report_type)
    setDescription(preset.description)
    setPins([
      {
        latitude: preset.latitude,
        longitude: preset.longitude,
        radius_meters: preset.radius_meters,
      },
    ])
    setRadiusMeters(preset.radius_meters)
  }

  return (
    <div className="space-y-5 animate-in">
      <header>
        <h1 className="font-display text-2xl text-ink">Report an item</h1>
        <p className="mt-1 text-sm text-muted">
          Signed in as {user.display_name}. Contact email is your account email.
        </p>
      </header>

      <form className="space-y-4" onSubmit={(e) => void onSubmit(e)}>
        <div className="flex gap-2">
          {(['lost', 'found'] as const).map((t) => (
            <Button
              key={t}
              type="button"
              variant={reportType === t ? 'primary' : 'secondary'}
              onClick={() => setReportType(t)}
            >
              {t === 'lost' ? 'Lost' : 'Found'}
            </Button>
          ))}
        </div>

        <TextArea
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required
          placeholder="Black leather wallet, lost near the library…"
        />

        <Input
          label="When"
          type="datetime-local"
          value={eventTime}
          onChange={(e) => setEventTime(e.target.value)}
          required
        />

        {reportType === 'found' ? (
          <TextArea
            label="Holding note"
            value={holdingNote}
            onChange={(e) => setHoldingNote(e.target.value)}
            placeholder="At the library desk."
          />
        ) : null}

        <label className="flex items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            checked={preferAnonymous}
            onChange={(e) => setPreferAnonymous(e.target.checked)}
            className="accent-primary"
          />
          Hide my contact from matches
        </label>

        <Input
          label="Phone (optional)"
          type="tel"
          value={contactPhone}
          onChange={(e) => setContactPhone(e.target.value)}
        />

        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-ink">Photos</span>
          <input
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => setFiles(e.target.files)}
            className="block w-full text-sm text-muted file:mr-3 file:rounded-lg file:border-0 file:bg-cream file:px-3 file:py-2 file:text-ink"
          />
        </label>

        {presets.length > 0 ? (
          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-ink">Or use a sample</span>
            <select
              value={presetId}
              onChange={(e) => applyPreset(e.target.value)}
              className="w-full rounded-xl border border-hairline bg-card px-3.5 py-3 text-[16px]"
            >
              <option value="">None</option>
              {presets.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        <div>
          <p className="mb-2 text-sm font-medium text-ink">Locations</p>
          <LocationMap
            mode="edit"
            pins={pins}
            radiusMeters={radiusMeters}
            onRadiusChange={setRadiusMeters}
            onAdd={(pin) => setPins((prev) => [...prev, pin])}
            onRemove={(index) =>
              setPins((prev) => prev.filter((_, i) => i !== index))
            }
            onClear={() => setPins([])}
          />
        </div>

        {error ? <p className="text-sm text-primary">{error}</p> : null}

        <Button type="submit" fullWidth disabled={busy || !description.trim()}>
          {busy ? 'Saving…' : 'Submit report'}
        </Button>
      </form>
    </div>
  )
}
