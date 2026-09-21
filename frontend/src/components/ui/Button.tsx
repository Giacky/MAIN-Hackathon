import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  children: ReactNode
  fullWidth?: boolean
}

const variants: Record<Variant, string> = {
  primary:
    'bg-primary text-white hover:brightness-105 disabled:opacity-60 disabled:hover:brightness-100',
  secondary:
    'bg-card text-ink border border-hairline hover:bg-cream disabled:opacity-60',
  ghost: 'bg-transparent text-muted hover:text-ink hover:bg-cream/60 disabled:opacity-60',
}

export function Button({
  variant = 'primary',
  fullWidth,
  className = '',
  children,
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={[
        'inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-[15px] font-medium transition duration-150',
        variants[variant],
        fullWidth ? 'w-full' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      {...rest}
    >
      {children}
    </button>
  )
}
