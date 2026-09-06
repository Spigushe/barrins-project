import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TolariaWestPage } from './TolariaWestPage'

const oracle = vi.hoisted(() => ({
  run: vi.fn(),
  reset: vi.fn(),
  status: 'idle' as 'idle' | 'running' | 'done' | 'error',
  progress: 0,
  result: null as unknown,
  error: null as string | null,
}))

vi.mock('@/hooks/useManaOracle', () => ({
  useManaOracle: () => ({
    run: oracle.run,
    reset: oracle.reset,
    status: oracle.status,
    progress: oracle.progress,
    result: oracle.result,
    error: oracle.error,
  }),
}))

beforeEach(() => {
  oracle.run.mockClear()
  oracle.reset.mockClear()
  oracle.status = 'idle'
  oracle.progress = 0
  oracle.result = null
  oracle.error = null
})

describe('TolariaWestPage', () => {
  it('starts with the original toy defaults', () => {
    render(<TolariaWestPage />)
    expect(screen.getByLabelText(/how many lands/i)).toHaveValue(39)
    expect(screen.getByLabelText(/colority of the spell/i)).toHaveValue('1CC')
    expect(screen.getByLabelText(/number of simulations/i)).toHaveValue(5000)
  })

  it('runs the simulation with parsed params on a valid submit', async () => {
    const user = userEvent.setup()
    render(<TolariaWestPage />)
    await user.click(screen.getByRole('button', { name: /find the sources/i }))
    expect(oracle.run).toHaveBeenCalledWith({
      lands: 39,
      colority: '1CC',
      simulations: 5000,
    })
  })

  it('rejects a colority that is not digits and C', async () => {
    const user = userEvent.setup()
    render(<TolariaWestPage />)
    const colority = screen.getByLabelText(/colority of the spell/i)
    await user.clear(colority)
    await user.type(colority, 'xyz')
    await user.click(screen.getByRole('button', { name: /find the sources/i }))
    expect(screen.getByText(/only digits and the letter C/i)).toBeInTheDocument()
    expect(oracle.run).not.toHaveBeenCalled()
  })

  it('rejects a zero-simulation run', async () => {
    const user = userEvent.setup()
    render(<TolariaWestPage />)
    const sims = screen.getByLabelText(/number of simulations/i)
    await user.clear(sims)
    await user.type(sims, '0')
    await user.click(screen.getByRole('button', { name: /find the sources/i }))
    expect(screen.getByText(/at least one simulation/i)).toBeInTheDocument()
    expect(oracle.run).not.toHaveBeenCalled()
  })

  it('shows progress and a disabled button while running', () => {
    oracle.status = 'running'
    oracle.progress = 0.42
    render(<TolariaWestPage />)
    expect(screen.getByRole('status')).toHaveTextContent('Simulating… 42%')
    expect(screen.getByRole('button', { name: /shuffling/i })).toBeDisabled()
  })

  it('reports the source count when the run finds an answer', () => {
    oracle.status = 'done'
    oracle.result = {
      found: true,
      goodLands: 14,
      targetTurn: 3,
      requiredPips: 2,
      colority: '1CC',
      successRate: 0.912,
      ciHalfWidth: 0.007,
      relevantGames: 4200,
      discardedGames: 800,
      simulations: 5000,
    }
    render(<TolariaWestPage />)
    const sentence = screen.getByText(/you need at least/i)
    expect(sentence).toHaveTextContent('14 lands')
    expect(sentence).toHaveTextContent('by turn 3')
    expect(sentence).toHaveTextContent('91.20 ± 0.70%')
  })

  it('explains a mana-screwed not-found result without NaN', () => {
    oracle.status = 'done'
    oracle.result = {
      found: false,
      targetTurn: 9,
      requiredPips: 3,
      colority: '6CCC',
      simulations: 500,
      maxGoodLandsTried: 39,
      everyGameDiscarded: true,
    }
    render(<TolariaWestPage />)
    expect(screen.getByText(/missed its land drops before turn 9/i)).toBeInTheDocument()
  })
})
