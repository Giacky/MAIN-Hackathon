import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import { ApiError, apiFetch } from '../api/client'
import type { CoordinationPayload } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { ItemCard } from '../components/ItemCard'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input, TextArea } from '../components/ui/Input'

function senderLabel(
  sender: string,
  role: 'lost' | 'found',
): string {
  if (sender === role) return 'You'
  if (sender === 'lost') return 'Owner'
  if (sender === 'found') return 'Finder'
  return sender
}

export function PickupLandingPage() {
  return (
    <div className="space-y-4 animate-in">
      <h1 className="font-display text-2xl text-ink">Pickup</h1>
      <p className="text-sm text-muted">
        Choose a ranked match first, then arrange contact and a meetup.
      </p>
      <Link
        to="/matches"
        className="inline-flex rounded-xl bg-primary px-4 py-3 text-sm font-medium text-white"
      >
        Open matches
      </Link>
    </div>
  )
}

export function PickupPage() {
  const { lostId = '', foundId = '' } = useParams()
  const { user, loading } = useAuth()
  const [data, setData] = useState<CoordinationPayload | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState('')
  const [locationName, setLocationName] = useState('University library entrance')
  const [meetingTime, setMeetingTime] = useState('')
  const [actionError, setActionError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const payload = await apiFetch<CoordinationPayload>(
        `/api/coordination/${lostId}/${foundId}`,
      )
      setData(payload)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load pickup')
    }
  }, [lostId, foundId])

  useEffect(() => {
    if (user && lostId && foundId) void load()
  }, [user, lostId, foundId, load])

  if (loading) return <p className="text-sm text-muted">Loading…</p>
  if (!user) return <Navigate to="/account" replace />

  if (error) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-primary">{error}</p>
        <Link to="/matches" className="text-sm text-primary underline">
          Back to matches
        </Link>
      </div>
    )
  }

  if (!data) {
    return <p className="text-sm text-muted">Loading pickup…</p>
  }

  const contact = data.other_contact
  const anonymous =
    contact == null ||
    contact.prefer_anonymous ||
    (!contact.contact_email && !contact.contact_phone && !contact.display_name)

  async function postMessage(e: FormEvent) {
    e.preventDefault()
    if (!note.trim()) return
    setBusy(true)
    setActionError(null)
    try {
      await apiFetch(`/api/coordination/${lostId}/${foundId}/messages`, {
        method: 'POST',
        body: JSON.stringify({ message: note.trim() }),
      })
      setNote('')
      await load()
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Could not send note')
    } finally {
      setBusy(false)
    }
  }

  async function proposeMeetup(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setActionError(null)
    try {
      await apiFetch(`/api/coordination/${lostId}/${foundId}/meetup`, {
        method: 'POST',
        body: JSON.stringify({
          location_name: locationName.trim(),
          meeting_time: meetingTime
            ? new Date(meetingTime).toISOString()
            : new Date().toISOString(),
        }),
      })
      await load()
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Could not propose meetup')
    } finally {
      setBusy(false)
    }
  }

  async function respond(kind: 'accept' | 'decline') {
    setBusy(true)
    setActionError(null)
    try {
      await apiFetch(`/api/coordination/${lostId}/${foundId}/meetup/${kind}`, {
        method: 'POST',
      })
      await load()
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : `Could not ${kind}`)
    } finally {
      setBusy(false)
    }
  }

  async function markRecovered() {
    setBusy(true)
    setActionError(null)
    try {
      await apiFetch(`/api/coordination/${lostId}/${foundId}/recovered`, {
        method: 'POST',
      })
      await load()
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Could not mark recovered')
    } finally {
      setBusy(false)
    }
  }

  const meetup = data.meetup
  const canRespond =
    meetup &&
    meetup.status === 'proposed' &&
    meetup.proposed_by &&
    meetup.proposed_by !== data.role

  return (
    <div className="space-y-5 animate-in">
      <header>
        <h1 className="font-display text-2xl text-ink">Pickup</h1>
        <p className="mt-1 text-sm text-muted">
          You are the {data.role === 'lost' ? 'owner' : 'finder'}.
        </p>
      </header>

      <div className="space-y-2">
        <ItemCard report={data.lost} />
        <ItemCard report={data.found} />
      </div>

      <Card>
        <h2 className="font-display text-lg text-ink">Contact</h2>
        {anonymous ? (
          <p className="mt-2 text-sm text-muted">
            The other person chose to stay anonymous for now. Use notes below to
            coordinate.
          </p>
        ) : (
          <dl className="mt-2 space-y-1 text-sm">
            {contact?.display_name ? (
              <div>
                <dt className="text-muted">Name</dt>
                <dd>{contact.display_name}</dd>
              </div>
            ) : null}
            {contact?.contact_email ? (
              <div>
                <dt className="text-muted">Email</dt>
                <dd>{contact.contact_email}</dd>
              </div>
            ) : null}
            {contact?.contact_phone ? (
              <div>
                <dt className="text-muted">Phone</dt>
                <dd>{contact.contact_phone}</dd>
              </div>
            ) : null}
          </dl>
        )}
      </Card>

      <Card>
        <h2 className="font-display text-lg text-ink">Meetup</h2>
        {meetup ? (
          <div className="mt-2 space-y-2 text-sm">
            <p>
              <span className="text-muted">Place · </span>
              {meetup.location_name}
            </p>
            <p>
              <span className="text-muted">When · </span>
              {meetup.meeting_time
                ? new Date(meetup.meeting_time).toLocaleString()
                : '—'}
            </p>
            <p>
              <span className="text-muted">Status · </span>
              {meetup.status}
            </p>
            {canRespond ? (
              <div className="flex gap-2 pt-1">
                <Button disabled={busy} onClick={() => void respond('accept')}>
                  Accept
                </Button>
                <Button
                  variant="secondary"
                  disabled={busy}
                  onClick={() => void respond('decline')}
                >
                  Decline
                </Button>
              </div>
            ) : null}
          </div>
        ) : (
          <form className="mt-3 space-y-3" onSubmit={(e) => void proposeMeetup(e)}>
            <Input
              label="Place"
              value={locationName}
              onChange={(e) => setLocationName(e.target.value)}
              required
            />
            <Input
              label="Time"
              type="datetime-local"
              value={meetingTime}
              onChange={(e) => setMeetingTime(e.target.value)}
            />
            <Button type="submit" variant="secondary" disabled={busy}>
              {busy ? 'Saving…' : 'Propose meetup'}
            </Button>
          </form>
        )}
      </Card>

      <Card>
        <h2 className="font-display text-lg text-ink">Notes</h2>
        <ul className="mt-3 space-y-2">
          {data.messages.length === 0 ? (
            <li className="text-sm text-muted">No notes yet.</li>
          ) : (
            data.messages.map((m, i) => (
              <li
                key={m.id ?? i}
                className="rounded-xl bg-cream px-3 py-2 text-sm"
              >
                <span className="font-medium">
                  {senderLabel(m.sender, data.role)}
                </span>
                <span className="text-muted"> · </span>
                {m.message}
              </li>
            ))
          )}
        </ul>
        <form className="mt-3 space-y-2" onSubmit={(e) => void postMessage(e)}>
          <TextArea
            label="Add a note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
          />
          <Button type="submit" variant="secondary" disabled={busy || !note.trim()}>
            Send note
          </Button>
        </form>
      </Card>

      {actionError ? <p className="text-sm text-primary">{actionError}</p> : null}

      {data.recovered ? (
        <p className="rounded-xl bg-cream px-3 py-3 text-sm text-muted">
          Both items are marked recovered.
        </p>
      ) : (
        <Button fullWidth disabled={busy} onClick={() => void markRecovered()}>
          {busy ? 'Saving…' : 'Mark recovered'}
        </Button>
      )}
    </div>
  )
}
