/** Relative timestamp for report chips and map popups. */
export function timeAgo(iso?: string | null): string | null {
  if (!iso) return null
  const then = Date.parse(iso)
  if (Number.isNaN(then)) return null
  const seconds = Math.round((Date.now() - then) / 1000)
  if (seconds < 45) return 'just now'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  if (days < 7) return `${days}d ago`
  return new Date(then).toLocaleDateString()
}

/** Compact absolute time, e.g. `21 Sep, 21:52`. */
export function formatShortWhen(iso?: string | null): string | null {
  if (!iso) return null
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return null
  const d = new Date(t)
  const day = d.getDate()
  const month = d.toLocaleString('en-GB', { month: 'short' })
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${day} ${month}, ${hh}:${mm}`
}

/** First line of a description, truncated for compact cards. */
export function firstLine(text: string, max = 80): string {
  const line = text.split('\n')[0]?.trim() ?? ''
  if (line.length <= max) return line
  return `${line.slice(0, Math.max(0, max - 1)).trimEnd()}…`
}
