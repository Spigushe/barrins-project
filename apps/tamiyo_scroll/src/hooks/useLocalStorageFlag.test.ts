import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { useLocalStorageFlag } from './useLocalStorageFlag'

describe('useLocalStorageFlag', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('defaults to the provided value when nothing is stored', () => {
    const { result } = renderHook(() => useLocalStorageFlag('test-flag', true))
    expect(result.current[0]).toBe(true)
  })

  it('reads a previously stored value over the default', () => {
    localStorage.setItem('test-flag', 'false')
    const { result } = renderHook(() => useLocalStorageFlag('test-flag', true))
    expect(result.current[0]).toBe(false)
  })

  it('persists the value to localStorage when toggled', () => {
    const { result } = renderHook(() => useLocalStorageFlag('test-flag', false))

    act(() => {
      result.current[1](true)
    })

    expect(result.current[0]).toBe(true)
    expect(localStorage.getItem('test-flag')).toBe('true')
  })

  it('syncs two hook instances reading the same key within the same tab', () => {
    const a = renderHook(() => useLocalStorageFlag('shared-flag', false))
    const b = renderHook(() => useLocalStorageFlag('shared-flag', false))

    act(() => {
      a.result.current[1](true)
    })

    expect(a.result.current[0]).toBe(true)
    expect(b.result.current[0]).toBe(true)
  })

  it('keeps independent keys independent', () => {
    const a = renderHook(() => useLocalStorageFlag('flag-a', false))
    const b = renderHook(() => useLocalStorageFlag('flag-b', false))

    act(() => {
      a.result.current[1](true)
    })

    expect(a.result.current[0]).toBe(true)
    expect(b.result.current[0]).toBe(false)
  })
})
