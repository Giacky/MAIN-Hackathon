import type { HTMLAttributes, ReactNode } from 'react'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
  padded?: boolean
}

export function Card({
  children,
  padded = true,
  className = '',
  ...rest
}: CardProps) {
  return (
    <div
      className={[
        'rounded-2xl border border-hairline bg-card transition duration-150',
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
