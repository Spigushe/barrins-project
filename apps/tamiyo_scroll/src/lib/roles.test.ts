import { describe, expect, it } from 'vitest'
import { roleMeetsFloor } from './roles'

describe('roleMeetsFloor', () => {
  it('accepts the exact floor role', () => {
    expect(roleMeetsFloor('moderator', 'moderator')).toBe(true)
  })

  it('accepts every role above the floor (ordinal, not exact-match)', () => {
    expect(roleMeetsFloor('ml_developer', 'moderator')).toBe(true)
    expect(roleMeetsFloor('admin', 'moderator')).toBe(true)
  })

  it('rejects every role below the floor', () => {
    expect(roleMeetsFloor('user', 'moderator')).toBe(false)
  })

  it('rejects an unresolved current user (no role yet, e.g. still loading)', () => {
    expect(roleMeetsFloor(undefined, 'moderator')).toBe(false)
  })
})
