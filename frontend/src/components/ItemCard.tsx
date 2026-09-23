import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { Report } from '../api/types'
import { timeAgo } from '../time'
import { Badge } from './ui/Badge'
import { Card } from './ui/Card'

interface ItemCardProps {
  report: Report
  href?: string
  /** Optional trailing element, e.g. a chevron or count. */
  trailing?: ReactNode
  matchesHref?: string
  onClose?: () => void
  closing?: boolean
}

export function ItemCard({
  report,
  href,
  trailing,
  matchesHref,
  onClose,
  closing = false,
}: ItemCardProps) {
  const photo = report.image_urls?.[0]
  const when = timeAgo(report.event_time ?? report.created_at)
  const hasActions = Boolean(matchesHref || onClose)

  const inner = (
    <Card
      padded={false}
      className={[
        'overflow-hidden',
        href && !hasActions ? 'hover:bg-card/70 active:scale-[0.99]' : '',
      ].join(' ')}
    >
      <div className="flex items-center gap-3 p-3">
        <div className="h-16 w-16 shrink-0 overflow-hidden rounded-2xl bg-primary-light/60">
          {photo ? (
            <img src={photo} alt="" className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-[11px] text-muted">
              No photo
            </div>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-1.5">
            <Badge tone={report.report_type === 'lost' ? 'lost' : 'found'}>
              {report.report_type}
            </Badge>
            {report.status !== 'open' ? (
              <Badge tone={report.status === 'recovered' ? 'success' : 'muted'}>{report.status}</Badge>
            ) : null}
            {when ? <span className="ml-auto text-[11px] text-muted">{when}</span> : null}
          </div>
          <p className="line-clamp-2 text-sm leading-snug text-ink">{report.description}</p>
          {typeof report.match_count === 'number' && report.match_count > 0 ? (
            <p className="mt-0.5 text-xs text-muted">
              {report.match_count === 1 ? '1 match' : `${report.match_count} matches`}
            </p>
          ) : null}
        </div>
        {trailing}
      </div>
      {hasActions ? (
        <div className="flex items-center gap-1 border-t border-white/50 px-2 py-1.5">
          {matchesHref ? (
            <Link
              to={matchesHref}
              className="flex-1 rounded-xl py-1.5 text-center text-sm font-semibold text-primary transition duration-150 hover:bg-primary-light/60"
            >
              Matches
            </Link>
          ) : null}
          {onClose ? (
            <button
              type="button"
              onClick={onClose}
              disabled={closing}
              className="flex-1 rounded-xl py-1.5 text-sm font-medium text-muted transition duration-150 hover:bg-card/70 hover:text-ink disabled:opacity-60"
            >
              {closing ? 'Closing…' : 'Close report'}
            </button>
          ) : null}
        </div>
      ) : null}
    </Card>
  )

  if (href && !hasActions) {
    return (
      <Link to={href} className="block">
        {inner}
      </Link>
    )
  }
  return inner
}
