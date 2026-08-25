import { CardNameHover } from '@/components/card-name-hover'
import { ManaPips } from '@/components/mana-pips'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'
import { TableCell, TableRow } from '@/components/ui/table'
import { DECKLIST_LINE_STATUS_TEXT_CLASS } from '@/lib/mtg-format'
import { cn } from '@/lib/utils'
import type { DecklistCard } from '@/schemas/tamiyoScroll'

export function DecklistCardRow({ card }: { card: DecklistCard }) {
  const isPending = card.status === 'pending' && Boolean(card.pending_added_card_name)

  // S17: while pending, the pips/popover describe the *added* card (what
  // the line is turning into), not the removed one still literally on it.
  const manaCost = isPending
    ? (card.pending_added_card_mana_cost ?? null)
    : card.mana_cost
  const text = isPending ? (card.pending_added_card_text ?? null) : card.text
  const keywords = isPending ? (card.pending_added_card_keywords ?? []) : card.keywords

  return (
    <TableRow>
      <TableCell className={cn(DECKLIST_LINE_STATUS_TEXT_CLASS[card.status])}>
        {card.qty}
      </TableCell>
      <TableCell className={cn(DECKLIST_LINE_STATUS_TEXT_CLASS[card.status])}>
        {isPending ? (
          <span className="flex items-center gap-1.5">
            <CardNameHover
              name={card.name}
              scryfallId={card.scryfall_id}
              className="line-through"
            />
            <span aria-hidden="true">→</span>
            <CardNameHover
              name={card.pending_added_card_name ?? ''}
              scryfallId={card.pending_added_card_scryfall_id}
            />
          </span>
        ) : (
          <CardNameHover name={card.name} scryfallId={card.scryfall_id} />
        )}
      </TableCell>
      <TableCell>
        <ManaPips manaCost={manaCost} />
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
            {keywords.length > 0 && (
              <div className="my-2 flex flex-wrap gap-1">
                {keywords.map((keyword) => (
                  <Badge key={keyword} variant="accent">
                    {keyword}
                  </Badge>
                ))}
              </div>
            )}
            <p className="text-sm whitespace-pre-line">{text ?? 'No oracle text.'}</p>
          </PopoverContent>
        </Popover>
      </TableCell>
    </TableRow>
  )
}
