import type { ComponentProps } from 'react'
import * as TabsPrimitive from '@radix-ui/react-tabs'
import { cn } from '@/lib/utils'

const Tabs = TabsPrimitive.Root

function TabsList({ className, ...props }: ComponentProps<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      className={cn('flex items-end gap-1 border-b border-border', className)}
      {...props}
    />
  )
}

function TabsTrigger({
  className,
  ...props
}: ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        'rounded-t-(--radius-input) px-4 py-2.5 text-sm font-semibold text-muted-foreground transition-colors cursor-pointer',
        'border-b-2 border-transparent -mb-px',
        'hover:text-foreground',
        'data-[state=active]:border-accent data-[state=active]:bg-card data-[state=active]:text-foreground',
        className,
      )}
      {...props}
    />
  )
}

function TabsContent({
  className,
  ...props
}: ComponentProps<typeof TabsPrimitive.Content>) {
  return <TabsPrimitive.Content className={cn('outline-none', className)} {...props} />
}

export { Tabs, TabsList, TabsTrigger, TabsContent }
