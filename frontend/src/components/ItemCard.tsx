import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { Report } from '../api/types'
import { timeAgo } from '../lib/time'
import { Badge } from './ui/Badge'
import { Card } from './ui/Card'

interface ItemCardProps {
  report: Report
  href?: string
  /** Optional trailing element, e.g. a chevron or count. */
  trailing?: ReactNode
}

export function ItemCard({ report, href, trailing }: ItemCardProps) {
  const photo = report.image_urls?.[0]
  const when = timeAgo(report.event_time ?? report.created_at)
  const inner = (
    <Card
      padded={false}
      className={[
        'overflow-hidden',
        href ? 'hover:bg-card/70 active:scale-[0.99]' : '',
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
        </div>
        {trailing}
      </div>
    </Card>
  )

  if (href) {
    return (
      <Link to={href} className="block">
        {inner}
      </Link>
    )
  }
  return inner
}
