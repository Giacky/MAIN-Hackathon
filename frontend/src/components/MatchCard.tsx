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

  const category = other.category && !/mock|unclassified/i.test(other.category) ? other.category : null
  const heading = category
    ? category.charAt(0).toUpperCase() + category.slice(1)
    : other.report_type === 'found'
      ? 'Found item'
      : 'Lost item'
  const distance =
    match.distance_meters != null
      ? match.distance_meters >= 1000
        ? `${(match.distance_meters / 1000).toFixed(1)} km apart`
        : `${Math.round(match.distance_meters)} m apart`
      : null

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
          <div className="flex items-baseline justify-between gap-2">
            <h3 className="font-display text-lg leading-snug text-ink">{heading}</h3>
            {distance ? <span className="text-xs text-muted">{distance}</span> : null}
          </div>
          <p className="mt-1 line-clamp-2 text-sm text-ink">{other.description}</p>
          {other.holding_note ? (
            <p className="mt-1 text-xs text-muted">Where it is now: {other.holding_note}</p>
          ) : null}
          {other.prefer_anonymous ? (
            <p className="mt-1 text-xs text-muted">
              {other.report_type === 'found' ? 'Finder' : 'Owner'} is staying anonymous
            </p>
          ) : null}
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
