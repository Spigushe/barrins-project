import type { ComponentProps, ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'

interface ConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: ReactNode
  description?: ReactNode
  /** Extra content rendered between the description and the action buttons — e.g. the invite-code retype step in `TeamMembershipCard` (delete team). */
  children?: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  onConfirm: () => void
  variant?: NonNullable<ComponentProps<typeof Button>['variant']>
  confirmDisabled?: boolean
}

/**
 * Shared confirm-before-destructive-action dialog (S13). Built on the
 * existing `Dialog` primitive — no `@radix-ui/react-alert-dialog` added.
 */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  confirmLabel = 'Delete',
  cancelLabel = 'Cancel',
  onConfirm,
  variant = 'destructive',
  confirmDisabled = false,
}: ConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {open && (
        <DialogContent>
          <DialogTitle>{title}</DialogTitle>
          {description && <p className="text-sm text-muted-foreground">{description}</p>}
          {children}
          <div className="mt-4 flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                onOpenChange(false)
              }}
            >
              {cancelLabel}
            </Button>
            <Button
              type="button"
              variant={variant}
              disabled={confirmDisabled}
              onClick={onConfirm}
            >
              {confirmLabel}
            </Button>
          </div>
        </DialogContent>
      )}
    </Dialog>
  )
}
