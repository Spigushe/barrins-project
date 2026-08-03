import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { CardDescription, CardTitle } from '@/components/ui/card'
import { Popover, PopoverAnchor, PopoverContent } from '@/components/ui/popover'
import { type DemoTabKey, TOUR_STEPS } from './tourSteps'

/** Finds the `<h2>` (`CardTitle`) whose text matches a tour step's `heading`. */
function findHeading(text: string): HTMLElement | null {
  const headings = document.querySelectorAll<HTMLElement>('h2')
  for (const heading of headings) {
    if (heading.textContent?.trim() === text) return heading
  }
  return null
}

interface DemoTourProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  activeTab: DemoTabKey
  onNavigateTab: (tab: DemoTabKey) => void
}

/**
 * Guided-tour overlay: a highlight ring plus a `Popover` anchored to whatever
 * on-screen heading the current step targets. No tour library, no new
 * dependency — just `popover.tsx`/`card.tsx`, already installed for the rest
 * of the app, and a plain highlight box for the ring.
 */
export function DemoTour({
  open,
  onOpenChange,
  activeTab,
  onNavigateTab,
}: DemoTourProps) {
  const [stepIndex, setStepIndex] = useState(0)
  const [rect, setRect] = useState<DOMRect | null>(null)
  const step = TOUR_STEPS[stepIndex]

  // Reset to the first step whenever the tour is (re)opened.
  useEffect(() => {
    if (open) setStepIndex(0)
  }, [open])

  // Switch to the tab the current step targets.
  useEffect(() => {
    if (open && step.tab !== activeTab) {
      onNavigateTab(step.tab)
    }
  }, [open, step, activeTab, onNavigateTab])

  // Once the right tab is showing, locate the target heading on screen.
  // Switching tabs remounts that tab's section components (Radix Tabs
  // unmounts inactive content), so their data reloads — poll a few frames
  // rather than assuming the heading is already in the DOM on the first one.
  useEffect(() => {
    if (!open || step.tab !== activeTab) {
      setRect(null)
      return
    }

    let cancelled = false
    let frame = 0
    let attempts = 0

    function tick() {
      if (cancelled) return
      const target = findHeading(step.heading)
      if (target) {
        // `behavior: 'auto'` (never 'smooth'): a smooth scroll animates over
        // several frames, so a `getBoundingClientRect()` read on the very
        // next line — as below — captures the heading's *pre-scroll*
        // position. The ring/popover would render offset from the real
        // heading until something else (e.g. a window resize) forced a
        // re-measure, since nothing here listens for the scroll finishing.
        // An instant scroll lands synchronously, so the immediate read is
        // already correct.
        target.scrollIntoView({ block: 'center', behavior: 'auto' })
        setRect(target.getBoundingClientRect())
        return
      }
      attempts += 1
      if (attempts < 30) {
        frame = window.requestAnimationFrame(tick)
      } else {
        setRect(null)
      }
    }
    frame = window.requestAnimationFrame(tick)

    function handleResize() {
      const target = findHeading(step.heading)
      setRect(target ? target.getBoundingClientRect() : null)
    }
    window.addEventListener('resize', handleResize)

    return () => {
      cancelled = true
      window.cancelAnimationFrame(frame)
      window.removeEventListener('resize', handleResize)
    }
  }, [open, step, activeTab])

  if (!open) return null

  function goNext() {
    if (stepIndex < TOUR_STEPS.length - 1) {
      setStepIndex(stepIndex + 1)
    } else {
      onOpenChange(false)
    }
  }

  function goPrev() {
    if (stepIndex > 0) setStepIndex(stepIndex - 1)
  }

  return (
    <>
      {rect && (
        <div
          aria-hidden="true"
          className="pointer-events-none fixed z-40 rounded-md ring-2 ring-accent transition-all duration-300"
          style={{
            top: rect.top - 4,
            left: rect.left - 4,
            width: rect.width + 8,
            height: rect.height + 8,
          }}
        />
      )}

      <Popover
        open={rect !== null}
        onOpenChange={(next) => {
          if (!next) onOpenChange(false)
        }}
      >
        <PopoverAnchor asChild>
          <div
            className="pointer-events-none fixed z-40"
            style={
              rect
                ? {
                    top: rect.top,
                    left: rect.left,
                    width: rect.width,
                    height: rect.height,
                  }
                : { top: 16, left: 16, width: 1, height: 1 }
            }
          />
        </PopoverAnchor>
        <PopoverContent
          className="z-50 p-4"
          side="bottom"
          align="start"
          onOpenAutoFocus={(event) => {
            event.preventDefault()
          }}
        >
          <p className="text-[11.5px] font-semibold text-muted-foreground">
            Step {stepIndex + 1} of {TOUR_STEPS.length}
          </p>
          <CardTitle className="mt-1">{step.title}</CardTitle>
          <CardDescription className="mt-2">{step.description}</CardDescription>
          <div className="mt-4 flex items-center justify-between gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                onOpenChange(false)
              }}
            >
              Skip tour
            </Button>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={stepIndex === 0}
                onClick={goPrev}
              >
                Back
              </Button>
              <Button type="button" size="sm" onClick={goNext}>
                {stepIndex === TOUR_STEPS.length - 1 ? 'Finish' : 'Next'}
              </Button>
            </div>
          </div>
        </PopoverContent>
      </Popover>
    </>
  )
}
