import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MethodologyPage } from './MethodologyPage'

describe('MethodologyPage', () => {
  it('documents the default date floor, pooling, and staples threshold rules', () => {
    render(<MethodologyPage />)

    expect(screen.getByText('Default date range')).toBeInTheDocument()
    expect(screen.getByText(/2015-11-01/)).toBeInTheDocument()
    expect(screen.getByText('Tournament pooling')).toBeInTheDocument()
    expect(screen.getByText('Staples threshold')).toBeInTheDocument()
    expect(screen.getByText(/65%/)).toBeInTheDocument()
  })
})
