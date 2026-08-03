import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DecklistTab } from '@/pages/DecklistTab'
import { MetagameTab } from '@/pages/MetagameTab'
import { SessionsTab } from '@/pages/SessionsTab'
import { SuiviBo3Tab } from '@/pages/SuiviBo3Tab'
import { DemoModeProvider } from './DemoModeProvider'
import { DemoTeamsSection } from './DemoTeamsSection'
import { DemoTour } from './DemoTour'
import { type DemoTabKey } from './tourSteps'

// Order and labels match the real app's tab strip (`AppShell.tsx`'s `TABS`).
const TAB_LABELS: Record<DemoTabKey, string> = {
  tracker: 'BO3 Tracking',
  metagame: 'Metagame',
  decklist: 'My decklist',
  sessions: 'Sessions',
  team: 'Teams',
}

/**
 * Public `/demo` route (S7, extended to 5 tabs). `MetagameTab`/`SuiviBo3Tab`/
 * `DecklistTab`/`SessionsTab` are the exact same components used by the real
 * app; `DemoModeProvider` is the only thing that differs from a normal
 * signed-in session. `DemoTeamsSection` is demo-only — the real "Teams" tab
 * navigates via `/app/team/*` routes, which don't exist under `/demo` (see
 * its own doc comment).
 */
export function DemoPage() {
  const [activeTab, setActiveTab] = useState<DemoTabKey>('metagame')
  const [tourOpen, setTourOpen] = useState(false)

  return (
    <DemoModeProvider>
      <div className="mx-auto max-w-[1400px] px-8 pt-7 pb-20">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-[22px] font-extrabold text-foreground">
              Tamiyo Scroll — Demo
            </h1>
            <p className="text-[13px] text-muted-foreground">
              Competitive · Test tracking · Duel Commander
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setTourOpen(true)
              }}
            >
              Take the guided tour
            </Button>
            <Button type="button" asChild>
              <Link to="/login">Log in / Create account</Link>
            </Button>
          </div>
        </header>

        <p className="mt-4 rounded-(--radius-input) border border-border-dashed bg-input-inline px-4 py-2 text-[12.5px] text-muted-foreground">
          You are viewing sample data in demo mode. Anything you add, edit or delete here
          disappears the moment you reload the page — nothing is sent to any server.
        </p>

        <Tabs
          className="mt-6"
          value={activeTab}
          onValueChange={(value) => {
            setActiveTab(value as DemoTabKey)
          }}
        >
          <TabsList>
            {(Object.keys(TAB_LABELS) as DemoTabKey[]).map((key) => (
              <TabsTrigger key={key} value={key}>
                {TAB_LABELS[key]}
              </TabsTrigger>
            ))}
          </TabsList>

          <div className="mt-7 flex flex-col gap-7">
            <TabsContent value="tracker">
              <SuiviBo3Tab />
            </TabsContent>
            <TabsContent value="metagame">
              <MetagameTab />
            </TabsContent>
            <TabsContent value="decklist">
              <DecklistTab />
            </TabsContent>
            <TabsContent value="sessions">
              <SessionsTab />
            </TabsContent>
            <TabsContent value="team">
              <DemoTeamsSection />
            </TabsContent>
          </div>
        </Tabs>
      </div>

      <DemoTour
        open={tourOpen}
        onOpenChange={setTourOpen}
        activeTab={activeTab}
        onNavigateTab={setActiveTab}
      />
    </DemoModeProvider>
  )
}
