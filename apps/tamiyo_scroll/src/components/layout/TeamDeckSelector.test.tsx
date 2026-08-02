import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TeamDeckSelector } from './TeamDeckSelector'

const downloadReportMutate = vi.fn()

let myTeams: { id: string; name: string; is_owner: boolean }[] = []
let teamDecks: Record<
  string,
  {
    name_key: string
    deck_name: string
    owners: { deck_id: string; display: string }[]
    has_thread: boolean
  }[]
> = {}

beforeEach(() => {
  myTeams = []
  teamDecks = {}
  downloadReportMutate.mockClear()
})

vi.mock('@/hooks/useTeams', () => ({
  useMyTeams: () => ({ data: myTeams }),
  useTeamDecks: (teamId: string | null) => ({
    data: teamId ? (teamDecks[teamId] ?? []) : [],
  }),
  useDownloadTeamDeckReport: () => ({ mutate: downloadReportMutate, isPending: false }),
}))

describe('TeamDeckSelector', () => {
  it('renders nothing when the account has no team', () => {
    const { container } = render(<TeamDeckSelector />)
    expect(container).toBeEmptyDOMElement()
  })

  it("lists decks flagged into the account's teams, merged (not one row per owner)", async () => {
    myTeams = [{ id: 'team-1', name: 'Dream Team', is_owner: true }]
    teamDecks = {
      'team-1': [
        {
          name_key: 'mono red',
          deck_name: 'Mono Red',
          owners: [
            { deck_id: 'deck-1', display: 'Bob' },
            { deck_id: 'deck-2', display: 'Alice' },
          ],
          has_thread: false,
        },
      ],
    }
    const user = userEvent.setup()
    render(<TeamDeckSelector />)

    await user.click(screen.getByRole('button', { name: 'Team decks' }))

    expect(screen.getByText('Dream Team')).toBeInTheDocument()
    expect(screen.getAllByText('Mono Red')).toHaveLength(1)
    expect(screen.getByText('(Bob, Alice)')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'PDF' })).toHaveLength(1)
  })

  it('downloads one cumulative PDF report for the deck name', async () => {
    myTeams = [{ id: 'team-1', name: 'Dream Team', is_owner: true }]
    teamDecks = {
      'team-1': [
        {
          name_key: 'mono red',
          deck_name: 'Mono Red',
          owners: [{ deck_id: 'deck-1', display: 'Bob' }],
          has_thread: false,
        },
      ],
    }
    const user = userEvent.setup()
    render(<TeamDeckSelector />)

    await user.click(screen.getByRole('button', { name: 'Team decks' }))
    await user.click(screen.getByRole('button', { name: 'PDF' }))

    expect(downloadReportMutate).toHaveBeenCalledWith({
      teamId: 'team-1',
      nameKey: 'mono red',
      filename: 'team-deck-report-mono-red.pdf',
    })
  })
})
