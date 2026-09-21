import { Link } from 'react-router-dom'
import type { MatchItem } from '../api/types'
import { Badge } from './ui/Badge'
import { Card } from './ui/Card'

function pct(score: number | null | undefined): number {
  if (score == null || Number.isNaN(score)) return 0
  return Math.round(Math.max(0, Math.min(1, score)) * 100)
}

function Meter({ label, value }: { label: string; value: number | null | undefined }) {
  const width = pct(value)
  return (
    <div className="min-w-0">
      <div className="mb-0.5 flex justify-between gap-2 text-[11px] text-muted">
        <span>{label}</span>
        <span>{value == null ? '—' : `${width}%`}</span>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-hairline">
        <div
          className="h-full rounded-full bg-ink/70 transition-[width] duration-150"
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  )
}

interface MatchCardProps {
  match: MatchItem
  anchorType: 'lost' | 'found'
}

export function MatchCard({ match, anchorType }: MatchCardProps) {
  const other = anchorType === 'lost' ? match.found : match.lost
  const photo = other.image_urls?.[0]
  const overall = pct(match.overall_score)
  const scoreTone = match.overall_score < 0.25 ? 'stone' : 'ink'
  const visual = match.visual

  let visualLine: string | null = null
  if (visual?.shortlisted) {
    if (visual.inliers != null) {
      visualLine = `${visual.inliers} aligned points`
    } else if (visual.dino_score != null) {
      visualLine = `Visual similarity ${pct(visual.dino_score)}%`
    } else {
      visualLine = 'In visual shortlist'
    }
  } else if (visual != null) {
    visualLine = 'Not in the visual shortlist'
  }

  return (
    <Card padded={false} className="overflow-hidden animate-in">
      <div className="relative aspect-[4/3] bg-cream">
        {photo ? (
          <img src={photo} alt="" className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-muted">
            No photo
          </div>
        )}
        <Badge
          tone={scoreTone}
          className="absolute right-3 top-3 shadow-sm backdrop-blur-sm"
        >
          {overall}% match
        </Badge>
      </div>

      <div className="space-y-3 p-4">
        <div>
          <h3 className="font-display text-lg leading-snug text-ink">
            {other.description.slice(0, 80)}
            {other.description.length > 80 ? '…' : ''}
          </h3>
          <p className="mt-1 line-clamp-2 text-sm text-muted">{other.description}</p>
        </div>

        <div className="grid grid-cols-2 gap-x-3 gap-y-2">
          <Meter label="Text" value={match.text_score} />
          <Meter label="Photos" value={match.image_score} />
          <Meter label="Category" value={match.category_score} />
          <Meter label="Location" value={match.geo_score} />
          <Meter label="Time" value={match.time_score} />
        </div>

        {visualLine ? (
          <p className="text-xs text-muted">
            {visualLine}
            {visual?.shortlisted && visual.inlier_ratio != null
              ? ` · ratio ${Math.round(visual.inlier_ratio * 100)}%`
              : null}
            {visual?.shortlisted && visual.dino_score != null && visual.inliers != null
              ? ` · DINO ${pct(visual.dino_score)}%`
              : null}
          </p>
        ) : null}

        {match.image_error ? (
          <p className="text-xs text-muted">Photo model note: {match.image_error}</p>
        ) : null}

        {match.gate_reason ? (
          <p className="text-xs text-muted">Gate: {match.gate_reason}</p>
        ) : null}

        <Link
          to={`/pickup/${match.lost.id}/${match.found.id}`}
          className="mt-1 inline-flex w-full items-center justify-center rounded-xl bg-primary px-4 py-3 text-[15px] font-medium text-white transition duration-150 hover:brightness-105"
        >
          Arrange pickup
        </Link>
      </div>
    </Card>
  )
}
