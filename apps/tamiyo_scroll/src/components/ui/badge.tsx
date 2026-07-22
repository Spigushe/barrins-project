import type { ComponentProps } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-(--radius-input) border px-2 py-0.5 text-[11.5px] font-semibold uppercase tracking-[0.04em] w-fit',
  {
    variants: {
      variant: {
        default: 'border-border bg-input text-foreground',
        accent: 'border-accent/35 bg-accent/12 text-accent',
        warning: 'border-warning/40 bg-warning/12 text-warning',
        destructive: 'border-destructive/40 bg-destructive/12 text-destructive',
        success: 'border-success/40 bg-success/12 text-success',
      },
    },
    defaultVariants: { variant: 'default' },
  },
)

interface BadgeProps extends ComponentProps<'span'>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant, className }))} {...props} />
}

export { Badge, badgeVariants }
