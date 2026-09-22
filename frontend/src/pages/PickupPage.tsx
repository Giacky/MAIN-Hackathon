import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError, apiFetch } from '../api/client'
import { fetchThreads } from '../api/coordination'
import type { CoordinationPayload, CoordinationThread } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { RedirectToLogin } from '../auth/RedirectToLogin'
import { ItemCard } from '../components/ItemCard'
import { PickupThreadCard } from '../components/PickupThreadCard'
import { Badge } from '../components/ui/Badge'
import { Button, buttonBase, buttonVariants } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input, TextArea } from '../components/ui/Input'

function senderLabel(sender: string, role: 'lost' | 'found'): string {
  if (sender === role) return 'You'
  if (sender === 'lost') return 'Owner'
  if (sender === 'found') return 'Finder'
  return sender
}

/** /pickup: the viewer's active threads, same list as the Home section. */
export function PickupLandingPage() {
  const { user, loading } = useAuth()
  const [threads, setThreads] = useState<CoordinationThread[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) return
    let cancelled = false
    ;(async () => {
      try {
        const list = await fetchThreads()
        if (cancelled) return
        setThreads(list)
        setError(null)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Could not load pickups')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [user])

  if (loading) return <p className="text-sm text-muted">Loading…</p>
  if (!user) return <RedirectToLogin />

  const active = threads?.filter((t) => !t.recovered) ?? []
  const done = threads?.filter((t) => t.recovered) ?? []

  return (
    <div className="space-y-5 animate-in">
      <header>
        <h1 className="font-display text-2xl text-ink">Pickups</h1>
        <p className="mt-1 text-sm text-muted">
          Conversations and meetups for your matched items.
        </p>
      </header>

      {error ? (
        <p className="text-sm text-accent">{error}</p>
      ) : threads == null ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : threads.length === 0 ? (
        <div className="glass space-y-3 px-4 py-6 text-center">
          <p className="text-sm text-ink">No pickups yet.</p>
          <p className="text-xs text-muted">
            Open one of your reports and tap Message them on a match to start a thread.
          </p>
          <Link to="/reports" className={[buttonBase, buttonVariants.primary, 'px-5 py-2.5 text-sm'].join(' ')}>
            Go to reports
          </Link>
        </div>
      ) : (
        <>
          {active.length > 0 ? (
            <section className="space-y-2">
              <h2 className="font-display text-lg text-ink">In progress</h2>
              {active.map((t) => (
                <PickupThreadCard key={`${t.lost.id}-${t.found.id}`} thread={t} />
              ))}
            </section>
          ) : null}
          {done.length > 0 ? (
            <section className="space-y-2">
              <h2 className="font-display text-lg text-ink">Recovered</h2>
              {done.map((t) => (
                <PickupThreadCard key={`${t.lost.id}-${t.found.id}`} thread={t} />
              ))}
            </section>
          ) : null}
        </>
      )}
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
      const payload = await apiFetch<CoordinationPayload>(`/api/coordination/${lostId}/${foundId}`)
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
  if (!user) return <RedirectToLogin />

  if (error) {
    return (
      <div className="space-y-3 animate-in">
        <p className="text-sm text-accent">{error}</p>
        <Link to="/reports" className="text-sm font-medium text-primary">
          Back to reports
        </Link>
      </div>
    )
  }

  if (!data) {
    return <p className="text-sm text-muted">Loading pickup…</p>
  }

  const contact = data.other_contact
  const anonymous = contact == null || (!contact.email && !contact.phone)

  async function run(action: () => Promise<unknown>, failMsg: string) {
    setBusy(true)
    setActionError(null)
    try {
      await action()
      await load()
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : failMsg)
    } finally {
      setBusy(false)
    }
  }

  async function postMessage(e: FormEvent) {
    e.preventDefault()
    if (!note.trim()) return
    const text = note.trim()
    await run(async () => {
      await apiFetch(`/api/coordination/${lostId}/${foundId}/messages`, {
        method: 'POST',
        body: JSON.stringify({ message: text }),
      })
      setNote('')
    }, 'Could not send note')
  }

  async function proposeMeetup(e: FormEvent) {
    e.preventDefault()
    await run(
      () =>
        apiFetch(`/api/coordination/${lostId}/${foundId}/meetup`, {
          method: 'POST',
          body: JSON.stringify({
            location_name: locationName.trim(),
            meeting_time: meetingTime
              ? new Date(meetingTime).toISOString()
              : new Date().toISOString(),
          }),
        }),
      'Could not propose meetup',
    )
  }

  async function respond(kind: 'accept' | 'decline') {
    await run(
      () => apiFetch(`/api/coordination/${lostId}/${foundId}/meetup/${kind}`, { method: 'POST' }),
      `Could not ${kind}`,
    )
  }

  async function markRecovered() {
    await run(
      () => apiFetch(`/api/coordination/${lostId}/${foundId}/recovered`, { method: 'POST' }),
      'Could not mark recovered',
    )
  }

  const meetup = data.meetup
  const canRespond =
    meetup && meetup.status === 'proposed' && meetup.proposed_by && meetup.proposed_by !== data.role
  const declined = meetup?.status === 'declined'
  const showProposeForm = !data.recovered && (meetup == null || declined)

  const other = data.other_name?.trim() || null
  const roleLine =
    data.role === 'lost'
      ? `You lost this · ${other ?? (anonymous ? 'an anonymous finder' : 'someone')} found it`
      : `You found this · ${other ?? (anonymous ? 'an anonymous owner' : 'someone')} lost it`

  return (
    <div className="space-y-5 pb-20 animate-in">
      <header>
        <h1 className="font-display text-2xl text-ink">Pickup</h1>
        <p className="mt-1 text-sm text-muted">{roleLine}</p>
      </header>

      {data.recovered ? (
        <Card className="animate-in border-success/40 bg-success/10">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-success text-white">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path d="m5 12.5 4.5 4.5L19 7.5" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
            <div>
              <h2 className="font-display text-lg text-ink">Recovered</h2>
              <p className="mt-0.5 text-sm text-muted">
                Both reports are closed. Thanks for bringing it back.
              </p>
            </div>
          </div>
        </Card>
      ) : null}

      <div className="space-y-2">
        <p className="text-xs font-medium uppercase tracking-wide text-muted">Both items</p>
        <div className="space-y-1">
          <p className="text-xs text-muted">Yours</p>
          <ItemCard
            report={data.role === 'lost' ? data.lost : data.found}
            href={`/reports/${data.role === 'lost' ? data.lost.id : data.found.id}`}
          />
        </div>
        <div className="space-y-1">
          <p className="text-xs text-muted">Theirs</p>
          <ItemCard report={data.role === 'lost' ? data.found : data.lost} />
        </div>
      </div>

      <Card>
        <h2 className="font-display text-lg text-ink">Contact</h2>
        {anonymous ? (
          <p className="mt-2 text-sm text-muted">
            The other person chose to stay anonymous for now. Use notes below to coordinate.
          </p>
        ) : (
          <dl className="mt-2 space-y-1 text-sm">
            {contact?.email ? (
              <div className="flex justify-between gap-3">
                <dt className="text-muted">Email</dt>
                <dd>
                  <a className="font-medium text-primary" href={`mailto:${contact.email}`}>
                    {contact.email}
                  </a>
                </dd>
              </div>
            ) : null}
            {contact?.phone ? (
              <div className="flex justify-between gap-3">
                <dt className="text-muted">Phone</dt>
                <dd>
                  <a className="font-medium text-primary" href={`tel:${contact.phone.replace(/\s+/g, '')}`}>
                    {contact.phone}
                  </a>
                </dd>
              </div>
            ) : null}
          </dl>
        )}
      </Card>

      <Card>
        <div className="flex items-center justify-between gap-2">
          <h2 className="font-display text-lg text-ink">Meetup</h2>
          {meetup ? (
            <Badge
              tone={
                meetup.status === 'accepted'
                  ? 'success'
                  : meetup.status === 'declined'
                    ? 'muted'
                    : 'accent'
              }
            >
              {meetup.status}
            </Badge>
          ) : null}
        </div>

        {meetup && !declined ? (
          <div className="mt-2 space-y-2 text-sm">
            <p>
              <span className="text-muted">Place · </span>
              {meetup.location_name}
            </p>
            <p>
              <span className="text-muted">When · </span>
              {meetup.meeting_time ? new Date(meetup.meeting_time).toLocaleString() : '—'}
            </p>
            {meetup.status === 'proposed' && !canRespond ? (
              <p className="text-xs text-muted">Waiting for the other person to respond.</p>
            ) : null}
            {canRespond ? (
              <div className="flex gap-2 pt-1">
                <Button disabled={busy} onClick={() => void respond('accept')}>
                  Accept
                </Button>
                <Button variant="secondary" disabled={busy} onClick={() => void respond('decline')}>
                  Decline
                </Button>
              </div>
            ) : null}
          </div>
        ) : null}

        {declined ? (
          <p className="mt-2 text-sm text-muted">
            {meetup?.location_name} was declined. Propose another place or time.
          </p>
        ) : null}

        {showProposeForm ? (
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
              {busy ? 'Saving…' : declined ? 'Propose again' : 'Propose meetup'}
            </Button>
          </form>
        ) : null}
      </Card>

      <Card>
        <h2 className="font-display text-lg text-ink">Notes</h2>
        <ul className="mt-3 space-y-2">
          {data.messages.length === 0 ? (
            <li className="text-sm text-muted">No notes yet.</li>
          ) : (
            data.messages.map((m, i) => {
              const mineMsg = m.sender === data.role
              return (
                <li
                  key={m.id ?? i}
                  className={[
                    'max-w-[85%] rounded-2xl px-3 py-2 text-sm',
                    mineMsg
                      ? 'ml-auto bg-primary-light text-ink'
                      : 'mr-auto bg-card/70 text-ink shadow-[0_0_0_1px_rgba(226,231,229,.7)]',
                  ].join(' ')}
                >
                  <span className="block text-[11px] font-medium text-muted">
                    {senderLabel(m.sender, data.role)}
                  </span>
                  {m.message}
                </li>
              )
            })
          )}
        </ul>
        {!data.recovered ? (
          <form className="mt-3 space-y-2" onSubmit={(e) => void postMessage(e)}>
            <TextArea
              label="Add a note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              className="min-h-20"
            />
            <Button type="submit" variant="secondary" disabled={busy || !note.trim()}>
              Send note
            </Button>
          </form>
        ) : null}
      </Card>

      {actionError ? <p className="text-sm text-accent">{actionError}</p> : null}

      {/* Sticky glass CTA bar above the nav */}
      <div className="pointer-events-none fixed inset-x-0 bottom-[calc(4.75rem+env(safe-area-inset-bottom))] z-30 flex justify-center px-4">
        <div className="glass-strong pointer-events-auto flex w-full max-w-md items-center gap-2 rounded-full p-1.5">
          {data.recovered ? (
            <Link to="/" className={[buttonBase, buttonVariants.primary, 'flex-1 rounded-full py-2.5'].join(' ')}>
              Back to home
            </Link>
          ) : (
            <>
              <Link
                to={`/reports/${data.role === 'lost' ? data.lost.id : data.found.id}`}
                className={[buttonBase, buttonVariants.ghost, 'rounded-full px-4 py-2.5 text-sm'].join(' ')}
              >
                Your report
              </Link>
              <Button
                className="flex-1 rounded-full py-2.5"
                disabled={busy}
                onClick={() => void markRecovered()}
              >
                {busy ? 'Saving…' : 'Mark recovered'}
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
