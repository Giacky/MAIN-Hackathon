import type { HTMLAttributes, ReactNode } from 'react'

export type BadgeTone = 'ink' | 'muted' | 'lost' | 'found' | 'success' | 'accent'

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  children: ReactNode
  tone?: BadgeTone
}

const tones: Record<BadgeTone, string> = {
  ink: 'bg-card/70 text-ink border-white/70',
  muted: 'bg-hairline/50 text-muted border-hairline/70',
  lost: 'bg-accent/15 text-accent border-accent/30',
  found: 'bg-primary-light text-primary border-primary/20',
  success: 'bg-success/15 text-success border-success/30',
  accent: 'bg-accent/85 text-white border-white/50',
}

export function Badge({ children, tone = 'ink', className = '', ...rest }: BadgeProps) {
  return (
    <span
      className={[
        'inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold capitalize backdrop-blur-md',
        tones[tone],
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      {...rest}
    >
      {children}
    </span>
  )
}
