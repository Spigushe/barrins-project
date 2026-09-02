// Mirrors `PASSWORD_PATTERN` in `apps/barrins_identity/app/schemas/auth.py`.
// Client-side feedback only — the backend is the source of truth on submit.
export const PASSWORD_RULES: { label: string; test: (value: string) => boolean }[] = [
  { label: 'At least 12 characters', test: (value) => value.length >= 12 },
  { label: 'One uppercase letter', test: (value) => /[A-Z]/.test(value) },
  { label: 'One lowercase letter', test: (value) => /[a-z]/.test(value) },
  { label: 'One digit', test: (value) => /\d/.test(value) },
  { label: 'One symbol', test: (value) => /[^\w\s]/.test(value) },
]
