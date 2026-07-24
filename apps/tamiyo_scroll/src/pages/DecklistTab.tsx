import { PersonalDecklistImportSection } from './metagame/PersonalDecklistImportSection'
import { CardTestsSection } from './suivi-bo3/CardTestsSection'
import { CurrentDecklistSection } from './decklist/CurrentDecklistSection'
import { VersionHistorySection } from './decklist/VersionHistorySection'

export function DecklistTab() {
  return (
    <>
      <PersonalDecklistImportSection />
      <CardTestsSection />
      <CurrentDecklistSection />
      <VersionHistorySection />
    </>
  )
}
