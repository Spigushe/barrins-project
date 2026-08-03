import { useState } from 'react'
import { useDownloadTeamDeckReport, useMyTeams, useTeamDecks } from '@/hooks/useTeams'
import { teamDeckReportFilename } from '@/lib/mtg-format'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import type { TeamSummary } from '@/schemas/tamiyoScroll'

/**
 * Read-only counterpart to `PersonalDeckSelector` (S2's "Team Decks"): a
 * member can't edit these decks or browse their full stats — the UAT
 * this satisfies is "sees the shared deck, can't edit it, can open its
 * PDF report" (S2 doc), not full cross-tab read access. One deck name,
 * one cumulative PDF — merged across every contributing member, never a
 * per-owner duplicate row.
 */
export function TeamDeckSelector() {
  const { data: myTeams } = useMyTeams()
  const [open, setOpen] = useState(false)

  if (!myTeams || myTeams.length === 0) return null

  return (
    <div className="flex flex-col gap-1.5">
      <Label id="team-deck-label">Team decks</Label>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger
          aria-labelledby="team-deck-label"
          className={cn(
            'flex h-9 w-64 items-center justify-between gap-2 rounded-(--radius-input) border border-border bg-input px-3 py-2 text-sm text-foreground outline-none transition-colors',
            'focus-visible:border-accent',
          )}
        >
          <span className="min-w-0 flex-1 truncate text-left text-muted-foreground">
            Browse shared decks…
          </span>
        </PopoverTrigger>
        <PopoverContent className="flex max-h-80 flex-col gap-3 overflow-y-auto p-3">
          {myTeams.map((team) => (
            <TeamDeckGroup key={team.id} team={team} />
          ))}
        </PopoverContent>
      </Popover>
    </div>
  )
}

function TeamDeckGroup({ team }: { team: TeamSummary }) {
  const { data: decks } = useTeamDecks(team.id)
  const downloadReport = useDownloadTeamDeckReport()

  if (!decks || decks.length === 0) return null

  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-xs font-semibold text-muted-foreground">{team.name}</p>
      {decks.map((deck) => (
        <div key={deck.name_key} className="flex items-center justify-between gap-2">
          <span className="min-w-0 truncate text-sm text-foreground">
            {deck.deck_name}{' '}
            <span className="text-xs text-muted-foreground">
              ({deck.owners.map((owner) => owner.display).join(', ') || 'none'})
            </span>
          </span>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={downloadReport.isPending}
            onClick={() => {
              downloadReport.mutate({
                teamId: team.id,
                nameKey: deck.name_key,
                filename: teamDeckReportFilename(deck),
              })
            }}
          >
            PDF
          </Button>
        </div>
      ))}
    </div>
  )
}
