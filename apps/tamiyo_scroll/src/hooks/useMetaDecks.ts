import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as metaDecksApi from '@/api/metaDecks'
import type { MetaDeckWrite } from '@/schemas/tamiyoScroll'
import { useMySettings } from './useSettings'
import { useViewingOwner } from './useViewingOwner'

/**
 * Resolves an id (typically a `Match`/`CardTest`'s `opponent_deck_id`)
 * against a list of roster options — checking each option's `merged_ids`,
 * not just its own `id` (F10). A game-scope collapse can fold several
 * underlying roster rows into one displayed line; an existing match still
 * carries whichever duplicate's id it was originally logged against, so a
 * plain `option.id === id` lookup would miss it and show "— select —"/"?"
 * — or worse, if the user then re-picks from what looks like the right
 * option, silently re-link the match to a different roster deck.
 */
export function resolveMetaDeckOption<T extends { id: string; merged_ids?: string[] }>(
  options: T[] | undefined,
  id: string | null | undefined,
): T | undefined {
  if (!id) return undefined
  return options?.find(
    (option) => option.id === id || (option.merged_ids?.includes(id) ?? false),
  )
}

export function useMetaDecks(options: { includeArchived?: boolean } = {}) {
  const owner = useViewingOwner()
  const { data: settings } = useMySettings()
  const includeArchived = options.includeArchived ?? false
  // Included in the key (not just relied on via invalidation) so
  // switching either is a genuinely distinct query — avoids a moment of
  // stale, wrong-scope data flashing while the invalidated query refetches.
  return useQuery({
    queryKey: [
      'meta-decks',
      owner?.id ?? 'self',
      settings?.active_personal_deck_id ?? null,
      settings?.metagame_roster_scope ?? 'game',
      includeArchived,
    ],
    queryFn: () => metaDecksApi.listMetaDecks({ includeArchived }),
  })
}

function useInvalidateMetaDecks() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: ['meta-decks'] })
    void queryClient.invalidateQueries({ queryKey: ['stats'] })
    // Creating/renaming/archiving a roster entry can shift
    // build_merged_view's sharer-opponent remap (sharing_merge.py), which
    // changes the opponent_deck_id matches resolve against server-side —
    // without this, a stale cached match keeps pointing at an id the
    // fresh meta-decks list no longer has, and resolveMetaDeckOption falls
    // back to "?" (F10 UAT).
    void queryClient.invalidateQueries({ queryKey: ['matches'] })
  }
}

export function useCreateMetaDeck() {
  const invalidate = useInvalidateMetaDecks()
  return useMutation({
    mutationFn: (payload: MetaDeckWrite) => metaDecksApi.createMetaDeck(payload),
    onSuccess: invalidate,
  })
}

export function useUpdateMetaDeck() {
  const invalidate = useInvalidateMetaDecks()
  return useMutation({
    mutationFn: ({ deckId, payload }: { deckId: string; payload: MetaDeckWrite }) =>
      metaDecksApi.updateMetaDeck(deckId, payload),
    onSuccess: invalidate,
  })
}

export function useArchiveMetaDeck() {
  const invalidate = useInvalidateMetaDecks()
  return useMutation({
    mutationFn: (deckId: string) => metaDecksApi.archiveMetaDeck(deckId),
    onSuccess: invalidate,
  })
}
