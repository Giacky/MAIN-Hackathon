import type { HTMLAttributes, ReactNode } from 'react'

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  children: ReactNode
  tone?: 'ink' | 'stone' | 'lost' | 'found'
}

const tones = {
  ink: 'bg-cream text-ink',
  stone: 'bg-hairline text-muted',
  lost: 'bg-lost/10 text-lost',
  found: 'bg-found/10 text-found',
}

export function Badge({
  children,
  tone = 'ink',
  className = '',
  ...rest
}: BadgeProps) {
  return (
    <span
      className={[
        'inline-flex items-center rounded-lg px-2 py-0.5 text-xs font-medium',
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
