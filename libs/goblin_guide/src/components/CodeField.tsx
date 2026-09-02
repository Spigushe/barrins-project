import { onlyDigits } from './codeMask'

export interface CodeFieldProps {
  /** `id` for the label association (callers pass `useId()`). */
  id: string
  /** Field label — "Verification code" for signup, "Reset code" for reset. */
  label: string
  value: string
  /** Receives the already digit-masked value. */
  onChange: (value: string) => void
  disabled?: boolean
  invalid?: boolean
  /** Overrides the default hint text. */
  hint?: string
}

/**
 * The digit-masked 6-character one-time-code input shared by the email
 * verification and password-reset screens.
 */
export function CodeField({
  id,
  label,
  value,
  onChange,
  disabled = false,
  invalid = false,
  hint = 'The 6-digit code from your email.',
}: CodeFieldProps) {
  return (
    <div className="gg-field">
      <label className="gg-label" htmlFor={id}>
        {label}
      </label>
      <input
        id={id}
        className="gg-input gg-code"
        inputMode="numeric"
        autoComplete="one-time-code"
        maxLength={6}
        placeholder="000000"
        value={value}
        disabled={disabled}
        aria-invalid={invalid}
        onChange={(event) => {
          onChange(onlyDigits(event.target.value))
        }}
      />
      <span className="gg-hint">{hint}</span>
    </div>
  )
}
