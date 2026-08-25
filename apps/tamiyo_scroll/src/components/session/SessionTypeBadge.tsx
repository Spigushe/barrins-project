import type { ReactNode } from 'react'
import {
  sessionHueBadgeStyle,
  SESSION_TYPE_BADGE_VARIANT,
  SESSION_TYPE_LABELS,
} from '@/lib/mtg-format'
import type { SessionType } from '@/schemas/tamiyoScroll'
import { Badge } from '@/components/ui/badge'

/**
 * A session's type badge, tinted by its hue (S14) when set instead of the
 * type-based color — the single place every "session tag" in the app
 * (Sessions tab row/summary, archived-sessions list, Match journal tag)
 * gets its color from, so a hue consistently overrides the type color
 * everywhere it's shown rather than in just one spot.
 */
export function SessionTypeBadge({
  session,
  children,
}: {
  session: { type: SessionType; hue: number | null }
  children?: ReactNode
}) {
  const hueStyle = sessionHueBadgeStyle(session.hue)
  return (
    <Badge
      variant={hueStyle ? undefined : SESSION_TYPE_BADGE_VARIANT[session.type]}
      style={hueStyle}
    >
      {children ?? SESSION_TYPE_LABELS[session.type]}
    </Badge>
  )
}
