import { useEffect, useState } from 'react'
import { useTelemetry } from '@/hooks/useTelemetry'
import { FOOTER_ROW_CLASS } from './footerRow'

const MS_PER_DAY = 86_400_000

const parisDateFormatter = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Europe/Paris',
})

/** `YYYY-MM-DD` in Europe/Paris -- used both to detect "is today the day
 * the banlist takes effect" and, parsed back via `Date.parse`, to diff two
 * Paris-local calendar dates without DST/time-of-day skew. */
function parisDateString(d: Date): string {
  return parisDateFormatter.format(d)
}

const relativeTimeFormatter = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })

function formatSyncedAgo(sourceSyncedAt: string, now: Date): string {
  const diffMs = new Date(sourceSyncedAt).getTime() - now.getTime()
  const diffMinutes = Math.round(diffMs / 60_000)
  if (Math.abs(diffMinutes) < 60) {
    return relativeTimeFormatter.format(diffMinutes, 'minute')
  }
  const diffHours = Math.round(diffMinutes / 60)
  if (Math.abs(diffHours) < 24) {
    return relativeTimeFormatter.format(diffHours, 'hour')
  }
  return relativeTimeFormatter.format(Math.round(diffHours / 24), 'day')
}

function formatCountdown(msRemaining: number): string {
  const totalSeconds = Math.max(0, Math.floor(msRemaining / 1000))
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`
}

function BanlistCountdown({
  nextBanlistAt,
  now,
  className,
}: {
  nextBanlistAt: string
  now: Date
  className?: string
}) {
  const nextDate = new Date(nextBanlistAt)
  const isBanlistDay = parisDateString(now) === parisDateString(nextDate)

  if (!isBanlistDay) {
    const daysUntil = Math.round(
      (Date.parse(parisDateString(nextDate)) - Date.parse(parisDateString(now))) /
        MS_PER_DAY,
    )
    return (
      <span className={className}>
        Next banlist in {daysUntil} day{daysUntil === 1 ? '' : 's'}
      </span>
    )
  }

  if (now.getTime() >= nextDate.getTime()) {
    return <span className={className}>Announcement published</span>
  }

  return (
    <span className={className}>
      Next banlist in {formatCountdown(nextDate.getTime() - now.getTime())}
    </span>
  )
}

/**
 * Persistent, contextual telemetry row -- season, banlist countdown,
 * last-sync -- mounted once in `AppShell`'s footer. Renders nothing while
 * `useTelemetry()` is loading or errored: ambient chrome, not worth a
 * skeleton or error banner.
 */
export function BottomRail() {
  const telemetry = useTelemetry()
  const nextBanlistAt = telemetry.data?.data.next_banlist_at

  // Only ticks (re-renders every second) on the calendar day the banlist
  // actually takes effect -- every other day the countdown is a static
  // day-count computed once per render, no timer needed.
  const [now, setNow] = useState(() => new Date())
  const isBanlistDay =
    nextBanlistAt !== undefined &&
    parisDateString(now) === parisDateString(new Date(nextBanlistAt))

  useEffect(() => {
    if (!isBanlistDay) return
    const id = setInterval(() => {
      setNow(new Date())
    }, 1000)
    return () => {
      clearInterval(id)
    }
  }, [isBanlistDay])

  if (!telemetry.data) return null

  const { season_year, season_number } = telemetry.data.data

  return (
    <div className={`border-t-[0.5px] border-border ${FOOTER_ROW_CLASS}`}>
      <span className="sm:text-left">
        Season · {season_year}-{season_number}
      </span>
      {nextBanlistAt && (
        <BanlistCountdown
          nextBanlistAt={nextBanlistAt}
          now={now}
          className="sm:text-center"
        />
      )}
      <span className="sm:text-right">
        {telemetry.data.meta.source_synced_at
          ? `Synced ${formatSyncedAgo(telemetry.data.meta.source_synced_at, now)}`
          : 'No data yet'}
      </span>
    </div>
  )
}
