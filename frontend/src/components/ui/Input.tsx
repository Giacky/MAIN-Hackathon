import type { InputHTMLAttributes, TextareaHTMLAttributes } from 'react'

export const fieldClass =
  'glass-field w-full px-3.5 py-3 text-[16px] text-ink placeholder:text-muted/70 outline-none transition duration-150 focus:border-primary/50 focus:ring-2 focus:ring-primary/25'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  hint?: string
}

export function Input({ label, hint, id, className = '', ...rest }: InputProps) {
  const inputId = id ?? rest.name
  return (
    <label className="block space-y-1.5">
      {label ? <span className="text-sm font-medium text-ink">{label}</span> : null}
      <input id={inputId} className={`${fieldClass} ${className}`} {...rest} />
      {hint ? <span className="text-xs text-muted">{hint}</span> : null}
    </label>
  )
}

interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  hint?: string
}

export function TextArea({ label, hint, id, className = '', ...rest }: TextAreaProps) {
  const inputId = id ?? rest.name
  return (
    <label className="block space-y-1.5">
      {label ? <span className="text-sm font-medium text-ink">{label}</span> : null}
      <textarea
        id={inputId}
        className={`${fieldClass} min-h-28 resize-y ${className}`}
        {...rest}
      />
      {hint ? <span className="text-xs text-muted">{hint}</span> : null}
    </label>
  )
}
