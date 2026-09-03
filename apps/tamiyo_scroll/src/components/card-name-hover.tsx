import { CardFacesPreview } from '@/components/card-faces-preview'
import { HoverCard, HoverCardTrigger, HoverCardContent } from '@/components/ui/hover-card'
import { cn } from '@/lib/utils'

/**
 * A card name, hover-previewed via the Scryfall proxy when a
 * `scryfallId` is known (plain text otherwise). Shared by the decklist
 * row's pending removed/added pair (S17) and the "Tested cards" card
 * log's own Removed/Added Card cells (S17 follow-up), so every card
 * name in the app hovers the same way.
 */
export function CardNameHover({
  name,
  scryfallId,
  className,
}: {
  name: string
  scryfallId: string | null | undefined
  className?: string
}) {
  if (!scryfallId) return <span className={className}>{name}</span>
  return (
    <HoverCard>
      <HoverCardTrigger asChild>
        <span
          className={cn(
            'cursor-default underline decoration-dotted decoration-muted-foreground',
            className,
          )}
        >
          {name}
        </span>
      </HoverCardTrigger>
      <HoverCardContent className="w-auto">
        <CardFacesPreview scryfallId={scryfallId} name={name} />
      </HoverCardContent>
    </HoverCard>
  )
}
