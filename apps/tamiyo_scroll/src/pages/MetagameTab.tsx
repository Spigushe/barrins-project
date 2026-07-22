import {
  ExpectedMetagameSection,
  MetaDecksRosterSection,
} from './metagame/MetaDecksSections'
import { ArchetypeSummarySection, MatchupSummarySection } from './metagame/StatsSections'

export function MetagameTab() {
  return (
    <>
      <MetaDecksRosterSection />
      <ExpectedMetagameSection />
      <ArchetypeSummarySection />
      <MatchupSummarySection />
    </>
  )
}
