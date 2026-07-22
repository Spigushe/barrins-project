import { type FormEvent, useState } from 'react'
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
  const importMoxfield = useImportMoxfield()
  const createVersion = useCreateDecklistVersion()

  if (!canEdit) return null

  if (activeDeckId === null) {
    return (
      <Card>
        <CardTitle>Decklist personnelle</CardTitle>
        <CardDescription className="mt-1">
          Sélectionnez ou créez un deck personnel ci-dessus pour importer une decklist.
        </CardDescription>
      </Card>
    )
  }
  const deckId = activeDeckId

  async function handleImport(event: FormEvent) {
    event.preventDefault()
    if (!moxfieldUrl.trim()) return
    await importMoxfield.mutateAsync({ deckId, moxfieldUrl: moxfieldUrl.trim() })
    setMoxfieldUrl('')
  }

  async function handleSaveRaw(event: FormEvent) {
    event.preventDefault()
    if (!rawText.trim()) return
    await createVersion.mutateAsync({ deckId, content: rawText.trim() })
    setRawText('')
  }

  return (
    <Card>
      <CardTitle>Decklist personnelle</CardTitle>
      <CardDescription className="mt-1">
        Importez un lien Moxfield (scrap via l&apos;API) ou collez le texte brut de la
        liste pour créer une nouvelle version du deck sélectionné ci-dessus.
      </CardDescription>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <form
          className="flex flex-col gap-2"
          onSubmit={(event) => {
            void handleImport(event)
          }}
        >
          <Label htmlFor="moxfield-url">Lien Moxfield</Label>
          <Input
            id="moxfield-url"
            placeholder="https://moxfield.com/decks/…"
            value={moxfieldUrl}
            onChange={(event) => {
              setMoxfieldUrl(event.target.value)
            }}
          />
          <Button type="submit" disabled={importMoxfield.isPending} className="w-fit">
            {importMoxfield.isPending ? 'Import en cours…' : 'Importer depuis Moxfield'}
          </Button>
        </form>

        <form
          className="flex flex-col gap-2"
          onSubmit={(event) => {
            void handleSaveRaw(event)
          }}
        >
          <Label htmlFor="raw-decklist">Texte brut</Label>
          <Textarea
            id="raw-decklist"
            rows={4}
            value={rawText}
            onChange={(event) => {
              setRawText(event.target.value)
            }}
          />
          <Button type="submit" disabled={createVersion.isPending} className="w-fit">
            Enregistrer cette version
          </Button>
        </form>
      </div>
    </Card>
  )
}
