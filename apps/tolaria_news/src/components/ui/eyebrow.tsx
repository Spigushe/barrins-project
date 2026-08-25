import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'

/** The dot+chip pattern from the design handoff's landing banner — reused
 * everywhere a section/page starts (DESIGN_SYSTEM.md § Components). */
function Eyebrow({ className, children, ...props }: ComponentProps<'span'>) {
  return (
    <span
      className={cn(
        'inline-flex w-fit items-center gap-2.5 rounded-(--radius-pill) border border-border bg-white/3 px-[11px] py-1.5 font-mono text-[11px] uppercase tracking-[0.04em] text-muted-foreground',
        className,
      )}
      {...props}
    >
      <span className="size-1.5 shrink-0 rounded-full bg-accent shadow-[0_0_8px_var(--color-accent)]" />
      {children}
    </span>
  )
}

export { Eyebrow }
