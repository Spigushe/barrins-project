import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { PasswordRules } from './PasswordRules'
import { PASSWORD_RULES } from './passwordPolicy'

describe('<PasswordRules>', () => {
  it('marks every rule unmet for an empty value', () => {
    render(<PasswordRules value="" />)
    const rules = screen.getAllByRole('listitem')
    expect(rules).toHaveLength(PASSWORD_RULES.length)
    for (const rule of rules) {
      expect(rule).toHaveAttribute('data-met', 'false')
    }
  })

  it('marks every rule met for a value that satisfies the pattern', () => {
    render(<PasswordRules value="GoblinGuide!23x" />)
    for (const rule of screen.getAllByRole('listitem')) {
      expect(rule).toHaveAttribute('data-met', 'true')
    }
  })

  it('flags only the failing rule for a value missing a digit', () => {
    render(<PasswordRules value="GoblinGuide!xyz" />)
    expect(screen.getByText('One digit').closest('.gg-rule')).toHaveAttribute(
      'data-met',
      'false',
    )
    expect(screen.getByText('One symbol').closest('.gg-rule')).toHaveAttribute(
      'data-met',
      'true',
    )
  })
})
