import type { ComponentProps } from 'react'
import * as LabelPrimitive from '@radix-ui/react-label'
import { cn } from '@/lib/utils'

function Label({ className, ...props }: ComponentProps<typeof LabelPrimitive.Root>) {
  return (
    <LabelPrimitive.Root
      className={cn(
        'text-[11.5px] font-medium uppercase tracking-[0.04em] text-muted-foreground select-none',
        className,
      )}
      {...props}
    />
  )
}

export { Label }
