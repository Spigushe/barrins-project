import '@testing-library/jest-dom/vitest'

// jsdom doesn't implement these — Radix UI's Select/Popover/Dialog call them
// on pointer interaction, so any test that opens one throws without a stub.
Element.prototype.hasPointerCapture ??= () => false
Element.prototype.releasePointerCapture ??= () => {}
Element.prototype.scrollIntoView ??= () => {}

// jsdom doesn't implement ResizeObserver either — cmdk (the Command palette
// behind the personal-deck combobox) uses it to measure its list.
class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= MockResizeObserver
