import { Badge } from '@/components/ui/badge'
import { CardFacesPreview } from '@/components/card-faces-preview'
import { ManaPips } from '@/components/mana-pips'
import { HoverCard, HoverCardTrigger, HoverCardContent } from '@/components/ui/hover-card'
import type { CommanderRef } from '@/schemas/tolariaNews'

function CommanderBadge({ commander }: { commander: CommanderRef }) {
  if (!commander.scryfall_id) {
    return <Badge variant="accent">{commander.name}</Badge>
  }
  return (
    <HoverCard>
      <HoverCardTrigger asChild>
        <Badge variant="accent" className="cursor-default">
          {commander.name}
        </Badge>
      </HoverCardTrigger>
      <HoverCardContent className="w-auto">
        <div className="flex flex-col gap-2">
          <CardFacesPreview scryfallId={commander.scryfall_id} name={commander.name} />
          <ManaPips manaCost={commander.mana_cost} />
        </div>
      </HoverCardContent>
    </HoverCard>
  )
}

/** One or two commander badges (solo or partner pair), each with an
 * on-hover card-art preview -- shared between the tournament deck list's
 * commander column and the commander-trend chips. */
export function CommanderHoverBadge({ commanders }: { commanders: CommanderRef[] }) {
  if (commanders.length === 0) return null
  return (
    <div className="flex flex-wrap gap-1">
      {commanders.map((commander) => (
        <CommanderBadge key={commander.name} commander={commander} />
      ))}
    </div>
  )
}
