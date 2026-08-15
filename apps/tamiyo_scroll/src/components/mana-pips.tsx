import { parseManaCost } from '@/lib/mana-symbols'

export function ManaPips({ manaCost }: { manaCost: string | null }) {
  const tokens = parseManaCost(manaCost)
  if (tokens.length === 0) return null
  return (
    <span className="flex flex-wrap gap-0.5">
      {tokens.map((token, index) => (
        <span
          key={`${String(index)}-${token}`}
          className="flex size-4 items-center justify-center rounded-full bg-input text-[10px] font-medium text-foreground"
        >
          {token}
        </span>
      ))}
    </span>
  )
}
