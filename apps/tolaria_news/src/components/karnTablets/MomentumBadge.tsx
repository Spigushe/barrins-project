import { Badge } from '@/components/ui/badge'
import type { ArchetypeMomentum } from '@/schemas/karnTablets'

/** Renders a backend-supplied `momentum` classification (rising / falling /
 * stable / new) as a coloured chip. The classification and the
 * `deck_share_delta` are both computed server-side — this component only
 * chooses the icon/colour and formats the delta as percentage points.
 *
 * PROVISIONAL — see src/schemas/karnTablets.ts. */
export function MomentumBadge({
  momentum,
  deckShareDelta,
}: {
  momentum: ArchetypeMomentum
  deckShareDelta: number | null
}) {
  const deltaPp =
    deckShareDelta == null
      ? null
      : `${deckShareDelta >= 0 ? '+' : '−'}${(Math.abs(deckShareDelta) * 100).toFixed(1)} pp`

  if (momentum === 'new') {
    return (
      <Badge variant="accent" title="New this period — no cluster in the previous run">
        {'✦'} new
      </Badge>
    )
  }
  if (momentum === 'rising') {
    return (
      <Badge
        variant="success"
        title={`Rising — deck share ${deltaPp ?? ''} vs the previous period`}
      >
        {'▲'} {deltaPp}
      </Badge>
    )
  }
  if (momentum === 'falling') {
    return (
      <Badge
        variant="destructive"
        title={`Falling — deck share ${deltaPp ?? ''} vs the previous period`}
      >
        {'▼'} {deltaPp}
      </Badge>
    )
  }
  return (
    <Badge
      variant="default"
      title={
        deltaPp
          ? `Stable — deck share ${deltaPp} vs the previous period, within the noise band`
          : 'Stable — no previous period to compare against'
      }
    >
      {'–'} steady
    </Badge>
  )
}
