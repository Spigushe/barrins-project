import type { Match, MatchWrite } from '@/schemas/tamiyoScroll'
import { GAME_RESULT_LABELS } from '@/lib/mtg-format'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'

export const GAME_NOT_PLAYED = '__not_played__'
const GAME_OPTIONS = ['win', 'loss', 'draw'] as const

export interface MatchDraft {
  personalDeckId: string
  opponentDeckId: string
  onPlay: boolean
  game1: string
  game2: string
  game3: string
  openingHand: string
  turningPoint: string
  finalTurn: string
}

export function emptyMatchDraft(defaultPersonalDeckId: string | null): MatchDraft {
  return {
    personalDeckId: defaultPersonalDeckId ?? '',
    opponentDeckId: '',
    onPlay: true,
    game1: GAME_NOT_PLAYED,
    game2: GAME_NOT_PLAYED,
    game3: GAME_NOT_PLAYED,
    openingHand: '',
    turningPoint: '',
    finalTurn: '',
  }
}

export function draftFromMatch(match: Match): MatchDraft {
  return {
    personalDeckId: match.personal_deck_id,
    opponentDeckId: match.opponent_deck_id,
    onPlay: match.on_play,
    game1: match.game1 ?? GAME_NOT_PLAYED,
    game2: match.game2 ?? GAME_NOT_PLAYED,
    game3: match.game3 ?? GAME_NOT_PLAYED,
    openingHand: match.opening_hand ?? '',
    turningPoint: match.turning_point ?? '',
    finalTurn: match.final_turn ?? '',
  }
}

export function matchDraftToWrite(draft: MatchDraft): MatchWrite {
  return {
    personal_deck_id: draft.personalDeckId,
    opponent_deck_id: draft.opponentDeckId,
    on_play: draft.onPlay,
    game1: draft.game1 === GAME_NOT_PLAYED ? null : (draft.game1 as MatchWrite['game1']),
    game2: draft.game2 === GAME_NOT_PLAYED ? null : (draft.game2 as MatchWrite['game2']),
    game3: draft.game3 === GAME_NOT_PLAYED ? null : (draft.game3 as MatchWrite['game3']),
    opening_hand: draft.openingHand.trim() || null,
    turning_point: draft.turningPoint.trim() || null,
    final_turn: draft.finalTurn.trim() || null,
  }
}

export function matchDraftIsValid(draft: MatchDraft): boolean {
  return draft.personalDeckId !== '' && draft.opponentDeckId !== ''
}

function GameResultSelect({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label>{label}</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="w-36">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={GAME_NOT_PLAYED}>— non jouée —</SelectItem>
          {GAME_OPTIONS.map((result) => (
            <SelectItem key={result} value={result}>
              {GAME_RESULT_LABELS[result]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

export function MatchFormFields({
  draft,
  onChange,
  personalDeckOptions,
  metaDeckOptions,
}: {
  draft: MatchDraft
  onChange: (next: MatchDraft) => void
  personalDeckOptions: { id: string; name: string }[]
  metaDeckOptions: { id: string; name: string }[]
}) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-3">
        <div className="flex flex-col gap-1.5">
          <Label>Mon deck</Label>
          <Select
            value={draft.personalDeckId}
            onValueChange={(value) => {
              onChange({ ...draft, personalDeckId: value })
            }}
          >
            <SelectTrigger className="w-52">
              <SelectValue placeholder="— sélectionner —" />
            </SelectTrigger>
            <SelectContent>
              {personalDeckOptions.map((deck) => (
                <SelectItem key={deck.id} value={deck.id}>
                  {deck.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label>Adversaire</Label>
          <Select
            value={draft.opponentDeckId}
            onValueChange={(value) => {
              onChange({ ...draft, opponentDeckId: value })
            }}
          >
            <SelectTrigger className="w-52">
              <SelectValue placeholder="— sélectionner —" />
            </SelectTrigger>
            <SelectContent>
              {metaDeckOptions.map((deck) => (
                <SelectItem key={deck.id} value={deck.id}>
                  {deck.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label>Sur la pioche</Label>
          <Select
            value={draft.onPlay ? 'otp' : 'otd'}
            onValueChange={(value) => {
              onChange({ ...draft, onPlay: value === 'otp' })
            }}
          >
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="otp">On the Play</SelectItem>
              <SelectItem value="otd">On the Draw</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <GameResultSelect
          label="Manche 1"
          value={draft.game1}
          onChange={(value) => {
            onChange({ ...draft, game1: value })
          }}
        />
        <GameResultSelect
          label="Manche 2"
          value={draft.game2}
          onChange={(value) => {
            onChange({ ...draft, game2: value })
          }}
        />
        <GameResultSelect
          label="Manche 3"
          value={draft.game3}
          onChange={(value) => {
            onChange({ ...draft, game3: value })
          }}
        />
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="opening-hand">Mains de départ</Label>
          <Textarea
            id="opening-hand"
            rows={3}
            value={draft.openingHand}
            onChange={(event) => {
              onChange({ ...draft, openingHand: event.target.value })
            }}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="turning-point">Point pivot</Label>
          <Textarea
            id="turning-point"
            rows={3}
            value={draft.turningPoint}
            onChange={(event) => {
              onChange({ ...draft, turningPoint: event.target.value })
            }}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="final-turn">Tour final</Label>
          <Textarea
            id="final-turn"
            rows={3}
            value={draft.finalTurn}
            onChange={(event) => {
              onChange({ ...draft, finalTurn: event.target.value })
            }}
          />
        </div>
      </div>
    </div>
  )
}
