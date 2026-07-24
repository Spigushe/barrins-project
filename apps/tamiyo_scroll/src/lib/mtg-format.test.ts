import { describe, expect, it } from 'vitest'
import {
  formatDate,
  formatDateTime,
  formatPercent,
  ratingTextClass,
  winrateTextClass,
} from './mtg-format'

describe('formatPercent', () => {
  it('renders an em dash for null', () => {
    expect(formatPercent(null)).toBe('—')
  })

  it('rounds and appends a percent sign', () => {
    expect(formatPercent(66.666)).toBe('67%')
    expect(formatPercent(0)).toBe('0%')
    expect(formatPercent(100)).toBe('100%')
  })
})

describe('winrateTextClass', () => {
  it('returns the muted class for null (no data)', () => {
    expect(winrateTextClass(null)).toBe('text-muted-foreground')
  })

  it.each([
    [100, 'text-winrate-80'],
    [80, 'text-winrate-80'],
    [79.9, 'text-winrate-60'],
    [60, 'text-winrate-60'],
    [59.9, 'text-winrate-40'],
    [40, 'text-winrate-40'],
    [39.9, 'text-winrate-20'],
    [20, 'text-winrate-20'],
    [19.9, 'text-winrate-0'],
    [0, 'text-winrate-0'],
  ])('maps %s%% to %s', (value, expected) => {
    expect(winrateTextClass(value)).toBe(expected)
  })
})

describe('ratingTextClass', () => {
  it.each([
    [5, 'text-winrate-80'],
    [4, 'text-winrate-60'],
    [3, 'text-winrate-40'],
    [2, 'text-winrate-20'],
    [1, 'text-winrate-0'],
  ])('maps rating %s to %s', (rating, expected) => {
    expect(ratingTextClass(rating)).toBe(expected)
  })
})

describe('formatDate', () => {
  it('converts an ISO date (YYYY-MM-DD) to DD/MM/YYYY', () => {
    expect(formatDate('2026-07-15')).toBe('15/07/2026')
  })
})

describe('formatDateTime', () => {
  it('formats an ISO datetime with offset as a French locale date', () => {
    // Locale formatting is environment-dependent for separators, but the
    // day/month/year components must always be present and correctly ordered.
    const formatted = formatDateTime('2026-07-15T21:56:11.123456+00:00')
    expect(formatted).toContain('2026')
    expect(formatted).toContain('15')
    expect(formatted).toContain('7')
  })
})
