# Incident: tested cards disappear from the UI after edit (`GET /api/v1/tamiyo-scroll/card-tests`)

## Status tracking

| Field | Value |
| --- | --- |
| Status | Open |
| Severity | Medium |
| Reported | 2026-07-16 |
| Area | Tamiyo Scroll — "Cartes testées" (BO3 tracking) |
| Blocking | `feat/v1-app` merge to production |
| Owner | Backend (Agent 1) |
| Workaround in place | Yes — schema relaxed client-side, see below |

## Summary

After editing a tested card (changing the opponent's deck), the entire list of
tested cards disappears from the UI. Root cause: the frontend is being migrated
to an API contract where every tested card carries a `personal_deck_id` (uuid,
**required**), but the `GET /api/v1/tamiyo-scroll/card-tests` endpoint doesn't
return that field on existing records yet. The client's strict schema validation
then rejects the whole response.

## Contract expected on the frontend side

`cardTestSchema` (`src/schemas/tamiyoScroll.ts`) now expects each item in the
list to look like:

```ts
{
  id: uuid,
  tester: string,
  card_name: string,
  personal_deck_id: uuid,   // new field, required
  opponent_deck_id: uuid | null,
  rating: int,
  notes: string | null,
  // ...other existing fields (created_at, etc.)
}
```

`cardTestWriteSchema` (POST/PUT) also expects `personal_deck_id` (uuid, required)
in the write payload.

## Concrete payloads

### GET /api/v1/tamiyo-scroll/card-tests — current (broken) response

```json
[
  {
    "id": "b1c2a3d4-1111-4a2b-9c3d-abcdef123456",
    "tester": "Alice",
    "card_name": "Goblin Guide",
    "opponent_deck_id": "4c3d5ea1-548c-43f5-a552-93f9a2f89e54",
    "rating": 4,
    "notes": "Great in the current shell",
    "created_at": "2026-06-01T10:00:00Z"
  }
]
```

→ `personal_deck_id` is missing. `cardTestSchema.array().parse(...)` fails on
this very first element, which invalidates **the entire response** on the client,
not just this one record.

### GET /api/v1/tamiyo-scroll/card-tests — expected (fixed) response

```json
[
  {
    "id": "b1c2a3d4-1111-4a2b-9c3d-abcdef123456",
    "tester": "Alice",
    "card_name": "Goblin Guide",
    "personal_deck_id": "07757e5b-c1cb-4d2a-98da-972deafdfc92",
    "opponent_deck_id": "4c3d5ea1-548c-43f5-a552-93f9a2f89e54",
    "rating": 4,
    "notes": "Great in the current shell",
    "created_at": "2026-06-01T10:00:00Z"
  }
]
```

### POST / PUT /api/v1/tamiyo-scroll/card-tests(/:id)

Write payload sent by the frontend

```json
{
  "personal_deck_id": "07757e5b-c1cb-4d2a-98da-972deafdfc92",
  "tester": "Alice",
  "card_name": "Goblin Guide",
  "opponent_deck_id": "4c3d5ea1-548c-43f5-a552-93f9a2f89e54",
  "rating": 4,
  "notes": "Great in the current shell"
}
```

This payload is already being sent by the current frontend (`toWrite()` in
`CardTestsSection.tsx` builds `personal_deck_id` from the active personal deck).
The backend needs to:

- accept it on write (create and update),
- persist it,
- return it on every subsequent read — including for rows created before the
- field was introduced (backfill required).

### Error observed on the client (Zod, illustrative)

```ts
ZodError: [
  {
    code: 'invalid_type',
    expected: 'string',
    received: 'undefined',
    path: [0, 'personal_deck_id'],
    message: 'Required',
  },
]
```

This error surfaces at `schema.parse(await response.json())`
(`src/api/client.ts:126`) and fails the entire `card-tests` React Query query.

## Reproduction

1. Open the "Suivi BO3" tab → "Cartes testées" section.
2. Edit an existing tested card (e.g. change the opponent's deck) and save.
3. The save (PUT) succeeds, which invalidates and fetches `GET /card-tests` again.
4. If that endpoint's response contains cards without `personal_deck_id`
   (or with a non-uuid value), Zod validation fails on **the whole array**, not
   just the edited row.
5. The component has no explicit error handling on this query, so the list
   silently falls back to "Aucun retour de test." instead of showing an error.

## Impact

- All tested cards become invisible in the UI as soon as a single record doesn't
  match the new contract (not just the one that was edited).
- No data loss on the backend side as far as we know — this is a client-side
  parsing failure, not a deletion. But from the user's perspective, the perceived
  effect is a total loss of visibility.

## What's expected from the backend

- `GET /api/v1/tamiyo-scroll/card-tests` must return `personal_deck_id` (uuid)
  for **every** tested card, including records created before the field existed
  (backfill needed if the field wasn't present in the database yet).
- `POST` / `PUT /api/v1/tamiyo-scroll/card-tests/:id` must accept and persist
  `personal_deck_id` in the write payload.
- Confirm whether `personal_deck_id` should be aligned with the user's active
  personal deck at the time of the test, and how to handle historical tests with
  no associated personal deck (default value? explicit migration?).

## Code references (frontend, for context)

- `src/schemas/tamiyoScroll.ts` — `cardTestSchema` / `cardTestWriteSchema` schemas
- `src/api/client.ts:126` — where the Zod `.parse()` fails and takes down the
  whole request
- `src/hooks/useCardTests.ts:30-37` — `card-tests` query invalidation after
  update, which triggers the refetch that reveals the problem
- `src/pages/suivi-bo3/CardTestsSection.tsx:75` — no `isError` handling on the
  query, hence the silent failure

## Proposed severity — Medium

Blocking for the "Cartes testées" feature until the backend returns/accepts
`personal_deck_id` on this endpoint — to be addressed before merging the
`feat/v1-app` branch to production.

In the meantime, a workaround is in place and will need to be removed once the
fix ships:

```diff
export const cardTestSchema = z.object({
  id: z.uuid(),
  tester: z.string(),
  card_name: z.string(),
-  personal_deck_id: z.uuid(),
+  personal_deck_id: z.uuid().nullable().optional(),
  opponent_deck_id: z.uuid().nullable(),
  rating: z.number().int(),
  notes: z.string().nullable(),
  created_at: z.iso.datetime({ offset: true }),
})
```
