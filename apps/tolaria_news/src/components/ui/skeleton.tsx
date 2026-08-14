import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'

function Skeleton({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      className={cn('animate-pulse rounded-(--radius-input) bg-input', className)}
      {...props}
    />
  )
}

export { Skeleton }
