/**
 * Splits a MTGJSON-style mana cost string ("{2}{U}{U}") into tokens
 * ("2", "U", "U") for pip rendering. No mana icon font is vendored in
 * this app — pips render as small styled text badges, not glyphs.
 */
export function parseManaCost(manaCost: string | null): string[] {
  if (!manaCost) return []
  return [...manaCost.matchAll(/\{([^}]+)\}/g)].map((m) => m[1])
}
