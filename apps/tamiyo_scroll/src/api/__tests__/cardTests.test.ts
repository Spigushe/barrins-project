import { describe, expect, it } from 'vitest'
import { cardTestWriteSchema } from '@/schemas/tamiyoScroll'

describe('cardTestWriteSchema', () => {
  it('preserves the personal deck reference needed by the backend update route', () => {
    const payload = cardTestWriteSchema.parse({
      tester: 'Alice',
      card_name: 'Goblin Guide',
      personal_deck_id: '07757e5b-c1cb-4d2a-98da-972deafdfc92',
      opponent_deck_id: '4c3d5ea1-548c-43f5-a552-93f9a2f89e54',
      rating: 4,
      notes: 'Great in the current shell',
    })

    expect(payload.personal_deck_id).toBe('07757e5b-c1cb-4d2a-98da-972deafdfc92')
  })
})
