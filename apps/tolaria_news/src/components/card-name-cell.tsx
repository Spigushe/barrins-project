import { CardFacesPreview } from '@/components/card-faces-preview'
import { HoverCard, HoverCardTrigger, HoverCardContent } from '@/components/ui/hover-card'

/** Card name with a Scryfall-art hover preview when `scryfall_id` is
 * known, plain text otherwise. Shared by any table row shaped like a
 * card (deck mainboard, tournament staples). */
export function CardNameCell({
  card,
}: {
  card: { name: string; scryfall_id: string | null }
}) {
  if (!card.scryfall_id) {
    return <span>{card.name}</span>
  }
  return (
    <HoverCard>
      <HoverCardTrigger asChild>
        <span className="cursor-default underline decoration-dotted decoration-muted-foreground">
          {card.name}
        </span>
      </HoverCardTrigger>
      <HoverCardContent className="w-auto">
        <CardFacesPreview scryfallId={card.scryfall_id} name={card.name} />
      </HoverCardContent>
    </HoverCard>
  )
}
