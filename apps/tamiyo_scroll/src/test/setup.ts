import '@testing-library/jest-dom/vitest'

// jsdom doesn't implement these — Radix UI's Select/Popover/Dialog call them
// on pointer interaction, so any test that opens one throws without a stub.
Element.prototype.hasPointerCapture ??= () => false
Element.prototype.releasePointerCapture ??= () => {}
Element.prototype.scrollIntoView ??= () => {}
