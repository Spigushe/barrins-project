import '@testing-library/jest-dom/vitest'

// jsdom doesn't implement matchMedia — the landing page's NodeGraph/Starfield
// check `prefers-reduced-motion` before starting their rAF loops.
window.matchMedia ??=
  ((query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as ReturnType<typeof window.matchMedia>) as typeof window.matchMedia
