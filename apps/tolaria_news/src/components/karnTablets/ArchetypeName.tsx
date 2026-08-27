import { CardFacesPreview } from '@/components/card-faces-preview'
import { HoverCard, HoverCardTrigger, HoverCardContent } from '@/components/ui/hover-card'
import type { CardRef } from '@/schemas/karnTablets'

/** An archetype's display name with a Scryfall-art hover of its
 * commander card(s) when any resolve, plain text otherwise. `name` can
 * diverge from the commanders (an admin rename, a "#2" split) — the hover
 * always shows the underlying cards.
 *
 * PROVISIONAL — see src/schemas/karnTablets.ts. */
export function ArchetypeName({
  name,
  commanders,
}: {
  name: string
  commanders: CardRef[]
}) {
  const withArt = commanders.filter(
    (c): c is CardRef & { scryfall_id: string } => c.scryfall_id !== null,
  )

  if (withArt.length === 0) return <span>{name}</span>

  return (
    <HoverCard>
      <HoverCardTrigger asChild>
        <span className="cursor-default underline decoration-dotted decoration-muted-foreground">
          {name}
        </span>
      </HoverCardTrigger>
      <HoverCardContent className="flex w-auto gap-2">
        {withArt.map((c) => (
          <CardFacesPreview
            key={c.scryfall_id}
            scryfallId={c.scryfall_id}
            name={c.name}
          />
        ))}
      </HoverCardContent>
    </HoverCard>
  )
}
