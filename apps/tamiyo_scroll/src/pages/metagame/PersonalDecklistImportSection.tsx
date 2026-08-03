import { type FormEvent, useState } from 'react'
import { ApiError } from '@/api/client'
import { useActiveDeck } from '@/contexts/active-deck-context'
import { useCreateDecklistVersion, useImportMoxfield } from '@/hooks/useDecklistVersions'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'

export function PersonalDecklistImportSection() {
  const { activeDeckId, canEdit } = useActiveDeck()
  const [moxfieldUrl, setMoxfieldUrl] = useState('')
  const [rawText, setRawText] = useState('')
  const [importError, setImportError] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [staleWarning, setStaleWarning] = useState(false)
  const importMoxfield = useImportMoxfield()
  const createVersion = useCreateDecklistVersion()

  if (!canEdit) return null

  if (activeDeckId === null) return null
  const deckId = activeDeckId

  async function handleImport(event: FormEvent) {
    event.preventDefault()
    if (!moxfieldUrl.trim()) return
    setImportError(null)
    setStaleWarning(false)
    try {
      const version = await importMoxfield.mutateAsync({
        deckId,
        moxfieldUrl: moxfieldUrl.trim(),
      })
      setStaleWarning(version.moxfield_deck_changed_since_last_import === true)
      setMoxfieldUrl('')
    } catch (err) {
      setImportError(err instanceof ApiError ? err.message : 'An error occurred.')
    }
  }

  async function handleSaveRaw(event: FormEvent) {
    event.preventDefault()
    if (!rawText.trim()) return
    setSaveError(null)
    try {
      await createVersion.mutateAsync({ deckId, content: rawText.trim() })
      setRawText('')
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : 'An error occurred.')
    }
  }

  return (
    <Card>
      <CardTitle>Decklist personnelle</CardTitle>
      <CardDescription className="mt-1">
        Import a Moxfield link (scraped via the API) or paste the raw decklist text to
        create a new version of the deck selected above.
      </CardDescription>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <form
          className="flex flex-col gap-2"
          onSubmit={(event) => {
            void handleImport(event)
          }}
        >
          <Label htmlFor="moxfield-url">Moxfield link</Label>
          <Input
            id="moxfield-url"
            placeholder="https://moxfield.com/decks/…"
            value={moxfieldUrl}
            onChange={(event) => {
              setMoxfieldUrl(event.target.value)
            }}
          />
          <Button type="submit" disabled={importMoxfield.isPending} className="w-fit">
            {importMoxfield.isPending ? 'Importing…' : 'Import from Moxfield'}
          </Button>
          {importError !== null && (
            <p className="text-[12.5px] text-destructive">{importError}</p>
          )}
          {staleWarning && (
            <p className="text-[12.5px] text-warning">
              This deck has changed on Moxfield since your last import from there.
            </p>
          )}
        </form>

        <form
          className="flex flex-col gap-2"
          onSubmit={(event) => {
            void handleSaveRaw(event)
          }}
        >
          <Label htmlFor="raw-decklist">Raw text</Label>
          <Textarea
            id="raw-decklist"
            rows={4}
            value={rawText}
            onChange={(event) => {
              setRawText(event.target.value)
            }}
          />
          <Button type="submit" disabled={createVersion.isPending} className="w-fit">
            Save this version
          </Button>
          {saveError !== null && (
            <p className="text-[12.5px] text-destructive">{saveError}</p>
          )}
        </form>
      </div>
    </Card>
  )
}
