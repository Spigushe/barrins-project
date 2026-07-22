import type { ComponentProps } from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-(--radius-button) text-sm font-semibold transition-colors disabled:pointer-events-none disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed',
  {
    variants: {
      variant: {
        default: 'bg-accent text-accent-foreground hover:opacity-90',
        outline: 'border border-border bg-transparent text-foreground hover:bg-input',
        destructive:
          'border border-destructive text-destructive bg-transparent hover:bg-destructive hover:text-destructive-foreground',
        ghost: 'bg-transparent text-foreground hover:bg-input',
        link: 'bg-transparent text-accent underline-offset-4 hover:underline p-0',
      },
      size: {
        default: 'h-9 px-4 py-2',
        sm: 'h-8 rounded-(--radius-input) px-3 text-xs',
        icon: 'size-8',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

interface ButtonProps
  extends ComponentProps<'button'>, VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

function Button({ className, variant, size, asChild = false, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : 'button'
  return <Comp className={cn(buttonVariants({ variant, size, className }))} {...props} />
}

export { Button, buttonVariants }
