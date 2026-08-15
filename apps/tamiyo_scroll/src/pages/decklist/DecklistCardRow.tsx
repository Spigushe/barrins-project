import { CardFacesPreview } from '@/components/card-faces-preview'
import { ManaPips } from '@/components/mana-pips'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { HoverCard, HoverCardTrigger, HoverCardContent } from '@/components/ui/hover-card'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'
import { TableCell, TableRow } from '@/components/ui/table'
import { DECKLIST_LINE_STATUS_TEXT_CLASS } from '@/lib/mtg-format'
import { cn } from '@/lib/utils'
import type { DecklistCard } from '@/schemas/tamiyoScroll'

export function DecklistCardRow({ card }: { card: DecklistCard }) {
  return (
    <TableRow>
      <TableCell className={cn(DECKLIST_LINE_STATUS_TEXT_CLASS[card.status])}>
        {card.qty}
      </TableCell>
      <TableCell className={cn(DECKLIST_LINE_STATUS_TEXT_CLASS[card.status])}>
        {card.scryfall_id ? (
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
        ) : (
          card.name
        )}
      </TableCell>
      <TableCell>
        <ManaPips manaCost={card.mana_cost} />
      </TableCell>
      <TableCell>
        <Popover>
          <PopoverTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label={`${card.name} info`}
            >
              ⓘ
            </Button>
          </PopoverTrigger>
          <PopoverContent className="p-3">
            {card.keywords.length > 0 && (
              <div className="my-2 flex flex-wrap gap-1">
                {card.keywords.map((keyword) => (
                  <Badge key={keyword} variant="accent">
                    {keyword}
                  </Badge>
                ))}
              </div>
            )}
            <p className="text-sm whitespace-pre-line">
              {card.text ?? 'No oracle text.'}
            </p>
          </PopoverContent>
        </Popover>
      </TableCell>
    </TableRow>
  )
}
