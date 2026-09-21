import { Link } from 'react-router-dom'
import type { Report } from '../api/types'
import { Badge } from './ui/Badge'
import { Card } from './ui/Card'

interface ItemCardProps {
  report: Report
  href?: string
}

export function ItemCard({ report, href }: ItemCardProps) {
  const photo = report.image_urls?.[0]
  const inner = (
    <Card padded={false} className="overflow-hidden transition duration-150 hover:border-primary/30">
      <div className="flex gap-3 p-3">
        <div className="h-16 w-16 shrink-0 overflow-hidden rounded-xl bg-cream">
          {photo ? (
            <img src={photo} alt="" className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-xs text-muted">
              No photo
            </div>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2">
            <Badge tone={report.report_type === 'lost' ? 'lost' : 'found'}>
              {report.report_type}
            </Badge>
            {report.status !== 'open' ? (
              <Badge tone="stone">{report.status}</Badge>
            ) : null}
          </div>
          <p className="line-clamp-2 text-sm text-ink">{report.description}</p>
        </div>
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
