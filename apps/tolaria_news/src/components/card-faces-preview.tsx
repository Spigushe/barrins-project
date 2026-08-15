import { useState } from 'react'
import { API_BASE_URL } from '@/api/client'

/**
 * Renders a card's front face image, plus its back face when one exists
 * (MDFC/transform cards). Whether a back face exists isn't known from
 * the card data we expose — the back-face request is always attempted
 * and silently hidden on failure (single-faced cards 404 it).
 */
export function CardFacesPreview({
  scryfallId,
  name,
}: {
  scryfallId: string
  name: string
}) {
  const [hasBackFace, setHasBackFace] = useState(true)

  return (
    <div className="flex gap-1">
      <img
        src={`${API_BASE_URL}/api/v1/cards/${scryfallId}/image`}
        alt={name}
        className="w-64 rounded-(--radius-input)"
      />
      {hasBackFace && (
        <img
          src={`${API_BASE_URL}/api/v1/cards/${scryfallId}/image?face=back`}
          alt={`${name} (back face)`}
          className="w-64 rounded-(--radius-input)"
          onError={() => {
            setHasBackFace(false)
          }}
        />
      )}
    </div>
  )
}
