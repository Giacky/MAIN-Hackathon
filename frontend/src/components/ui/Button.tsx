import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'accent' | 'secondary' | 'ghost'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  children: ReactNode
  fullWidth?: boolean
}

export const buttonBase =
  'inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-3 text-[15px] font-medium transition duration-150 active:scale-[0.98] disabled:active:scale-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40'

export const buttonVariants: Record<Variant, string> = {
  primary:
    'bg-linear-to-b from-primary/90 to-primary text-white shadow-[inset_0_1px_0_rgba(255,255,255,.28),0_6px_16px_rgba(23,107,104,.28)] hover:brightness-105 disabled:opacity-60 disabled:hover:brightness-100',
  accent:
    'bg-linear-to-b from-accent/90 to-accent text-white shadow-[inset_0_1px_0_rgba(255,255,255,.35),0_6px_16px_rgba(242,140,104,.32)] hover:brightness-105 disabled:opacity-60 disabled:hover:brightness-100',
  secondary: 'glass text-ink hover:bg-card/75 disabled:opacity-60',
  ghost: 'bg-transparent text-muted hover:text-ink hover:bg-card/50 disabled:opacity-60',
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
      className={[buttonBase, buttonVariants[variant], fullWidth ? 'w-full' : '', className]
        .filter(Boolean)
        .join(' ')}
      {...rest}
    >
      {children}
    </button>
  )
}
