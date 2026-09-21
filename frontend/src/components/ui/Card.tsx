import type { HTMLAttributes, ReactNode } from 'react'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
  padded?: boolean
  /** `strong` uses the more opaque glass for bars and overlays. */
  tone?: 'glass' | 'strong'
}

export function Card({
  children,
  padded = true,
  tone = 'glass',
  className = '',
  ...rest
}: CardProps) {
  return (
    <div
      className={[
        tone === 'strong' ? 'glass-strong' : 'glass',
        'transition duration-150',
        padded ? 'p-4' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      {...rest}
    >
      {children}
    </div>
  )
}
