import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { MatchItem } from '../api/types'
import { Badge } from './ui/Badge'
import { buttonBase, buttonVariants } from './ui/Button'
import { Card } from './ui/Card'

function pct(score: number | null | undefined): number {
  if (score == null || Number.isNaN(score)) return 0
  return Math.round(Math.max(0, Math.min(1, score)) * 100)
}

function categoryLooksReal(category?: string | null): boolean {
  return Boolean(category && !/mock|unclassified/i.test(category))
}

/** Matches services.image_matching._MIN_INLIERS. */
const INLIER_FLOOR = 4

/** One-line photo/category verdict; overall score stays secondary. */
function matchVerdict(match: MatchItem): string | null {
  const visual = match.visual
  if (visual?.same_object === true) {
    return 'Photos look like the same object'
  }
  if (visual?.shortlisted) {
    if (visual.same_object == null && visual.inliers != null && visual.inliers >= INLIER_FLOOR) {
      return 'Photos look like the same object'
    }
    return 'Looks like the same item'
  }
  const categoryHit =
    (match.category_score ?? 0) >= 0.5 ||
    (categoryLooksReal(match.lost.category) && match.lost.category === match.found.category)
  if (categoryHit) return 'Same kind of item, nearby'
  return null
}

interface MatchCardProps {
  match: MatchItem
  anchorType: 'lost' | 'found'
  /** True when a pickup thread (notes or meetup) already exists for this pair. */
  hasThread?: boolean
  onDismiss?: () => Promise<void> | void
}

export function MatchCard({ match, anchorType, hasThread = false, onDismiss }: MatchCardProps) {
  const other = anchorType === 'lost' ? match.found : match.lost
  const mine = anchorType === 'lost' ? match.lost : match.found
  const otherPhoto = other.image_urls?.[0]
  const minePhoto = mine.image_urls?.[0]
  const overall = pct(match.overall_score)
  const verdict = matchVerdict(match)
  const [busy, setBusy] = useState(false)
  const [dismissError, setDismissError] = useState<string | null>(null)

  const category = categoryLooksReal(other.category) ? other.category : null
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

  async function handleDismiss() {
    if (!onDismiss || busy) return
    setBusy(true)
    setDismissError(null)
    try {
      await onDismiss()
    } catch (err) {
      setDismissError(err instanceof Error ? err.message : 'Could not dismiss')
      setBusy(false)
    }
  }

  return (
    <Card padded={false} className="overflow-hidden animate-in">
      <div className="grid grid-cols-2 gap-px bg-hairline/40">
        <div className="relative aspect-square bg-primary-light/50">
          {minePhoto ? (
            <img src={minePhoto} alt="" className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full items-center justify-center text-xs text-muted">No photo</div>
          )}
          <Badge tone={mine.report_type === 'lost' ? 'lost' : 'found'} className="absolute left-2 top-2 bg-card/80">
            Yours
          </Badge>
        </div>
        <div className="relative aspect-square bg-primary-light/50">
          {otherPhoto ? (
            <img src={otherPhoto} alt="" className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full items-center justify-center text-xs text-muted">No photo</div>
          )}
          <Badge
            tone={other.report_type === 'lost' ? 'lost' : 'found'}
            className="absolute left-2 top-2 bg-card/80"
          >
            {other.report_type}
          </Badge>
        </div>
      </div>

      <div className="space-y-3 p-4">
        <div>
          {verdict ? (
            <h3 className="font-display text-lg leading-snug text-ink">{verdict}</h3>
          ) : (
            <h3 className="font-display text-lg leading-snug text-ink">{heading}</h3>
          )}
          <p className="mt-0.5 text-xs text-muted">
            Combined ranking {overall}%
            {distance ? ` · ${distance}` : ''}
          </p>
          {verdict ? <p className="mt-2 text-sm font-medium text-ink">{heading}</p> : null}
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

        {match.image_error ? (
          <p className="text-xs text-muted">Photo model note: {match.image_error}</p>
        ) : null}

        {dismissError ? <p className="text-xs text-accent">{dismissError}</p> : null}

        <div className="mt-1 flex items-stretch gap-2">
          <Link
            to={`/pickup/${match.lost.id}/${match.found.id}`}
            className={[
              buttonBase,
              hasThread ? buttonVariants.primary : buttonVariants.accent,
              'min-w-0 flex-1',
            ].join(' ')}
          >
            Message them
          </Link>
          {onDismiss ? (
            <button
              type="button"
              onClick={() => void handleDismiss()}
              disabled={busy}
              className={[buttonBase, buttonVariants.ghost, 'shrink-0 px-3.5'].join(' ')}
            >
              {busy ? '…' : 'Not this'}
            </button>
          ) : null}
        </div>
      </div>
    </Card>
  )
}
