import { Link } from 'react-router-dom'
import { usePlatformMetrics } from '@/hooks/useAdmin'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'

const STAT_TILES: {
  key: 'total_accounts' | 'total_personal_decks' | 'total_matches'
  label: string
}[] = [
  { key: 'total_accounts', label: 'Accounts created' },
  { key: 'total_personal_decks', label: 'Personal decks created' },
  { key: 'total_matches', label: 'Matches recorded' },
]

/** Admin-only usage/metrics dashboard (S6). Exactly the three v2.0.0 staged
 * adoption signals — nothing more (deeper metrics are explicitly deferred,
 * see docs/project/v2.0.0-bump/s6-admin-metrics-dashboard/index.md). */
export function AdminMetricsPage() {
  const { data, isLoading, isError } = usePlatformMetrics()

  return (
    <div className="mx-auto max-w-[900px] px-8 pt-7 pb-20">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-extrabold text-foreground">Usage metrics</h1>
          <p className="text-[13px] text-muted-foreground">
            Admin only · aggregate counts
          </p>
        </div>
        <Link to="/app/tracker" className="text-sm text-muted-foreground hover:underline">
          Back to app
        </Link>
      </header>

      <div
        className="mt-6 grid gap-4"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}
      >
        {isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}
        {isError && (
          <p className="text-sm text-destructive">Could not load usage metrics.</p>
        )}
        {data &&
          STAT_TILES.map((tile) => (
            <Card key={tile.key}>
              <CardTitle>{data[tile.key].value.toLocaleString()}</CardTitle>
              <CardDescription>{tile.label}</CardDescription>
            </Card>
          ))}
      </div>
    </div>
  )
}
