import { Link } from 'react-router-dom'
import type { CoordinationThread } from '../api/types'
import { firstLine } from '../time'
import { Badge, type BadgeTone } from './ui/Badge'
import { Card } from './ui/Card'

function statusLabel(t: CoordinationThread): { label: string; tone: BadgeTone } {
  if (t.recovered) return { label: 'Recovered', tone: 'success' }
  switch (t.meetup_status) {
    case 'accepted':
      return { label: 'Meetup accepted', tone: 'success' }
    case 'proposed':
      return { label: 'Meetup proposed', tone: 'accent' }
    case 'declined':
      return { label: 'Meetup declined', tone: 'muted' }
    default:
      return { label: 'In conversation', tone: 'ink' }
  }
}

/** One active pickup thread: both photos, role line, status, last note. */
export function PickupThreadCard({ thread }: { thread: CoordinationThread }) {
  const mine = thread.role === 'lost' ? thread.lost : thread.found
  const theirs = thread.role === 'lost' ? thread.found : thread.lost
  const status = statusLabel(thread)
  const roleLine = thread.role === 'lost' ? 'You lost this' : 'You found this'

  return (
    <Link to={`/pickup/${thread.lost.id}/${thread.found.id}`} className="block">
      <Card padded={false} className="overflow-hidden hover:bg-card/70 active:scale-[0.99]">
        <div className="flex items-center gap-3 p-3">
          <div className="relative h-16 w-20 shrink-0">
            <Thumb src={mine.image_urls?.[0]} className="absolute left-0 top-0 z-10 h-12 w-12 border-2 border-white" />
            <Thumb src={theirs.image_urls?.[0]} className="absolute bottom-0 right-0 h-12 w-12 border-2 border-white" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="mb-1 flex flex-wrap items-center gap-1.5">
              <Badge tone={status.tone}>{status.label}</Badge>
              <span className="text-[11px] text-muted">{roleLine}</span>
            </div>
            <p className="line-clamp-1 text-sm text-ink">{firstLine(mine.description)}</p>
            <p className="mt-0.5 line-clamp-1 text-xs text-muted">
              {thread.last_message ? `“${firstLine(thread.last_message, 60)}”` : 'No notes yet'}
            </p>
          </div>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden className="text-muted">
            <path d="m9 6 6 6-6 6" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </Card>
    </Link>
  )
}

function Thumb({ src, className }: { src?: string; className: string }) {
  return (
    <div className={`overflow-hidden rounded-xl bg-primary-light/60 ${className}`}>
      {src ? <img src={src} alt="" className="h-full w-full object-cover" /> : null}
    </div>
  )
}
