"""ORM models for MTGJSON reference data (S8): sets, cards, import runs.

Populated from MTGJSON's `AllPrintings.json` (`app/services/mtgjson/`).
Tables are `mj_`-prefixed, matching this codebase's `bs_*`/`ts_*`
domain-prefix convention (2026-08-09 rename -- originally shipped
unprefixed as `sets`/`cards`, fixed before either table held real data,
see the rename migration).

Unlike `bs_*`/`ts_*`, `mj_sets`/`mj_cards` primary keys are the upstream
data's own natural identifiers rather than a generated surrogate:

- `Set.code` (e.g. "ZNR") is MTGJSON's own stable set code.
- `Card.id` is MTGJSON's own per-printing-per-face `uuid` -- already a
  permanent, globally unique identifier for exactly the row we store one
  of, unlike e.g. a scraped tournament URL (`bs_tournaments.url`), which
  is why those tables *do* use a generated UUID plus a natural-key unique
  constraint instead. `MTGJSONImportRun` (`mj_import_runs`) is the odd one
  out: it's an operational log of import attempts, not reference data, so
  it gets a generated UUID like `bs_*`/`ts_*` -- there's no natural key
  for "one run of the importer".

A multi-face card (MDFC, transform, ...) is one row per face in MTGJSON's
own data already -- `face_name`/`side` distinguish faces of the same
`name`, `other_face_ids` links them -- so per-face type data (`type_line`,
`types`, ...) falls out of storing one row per MTGJSON `uuid`, no extra
modeling needed.

No image fields: MTGJSON ships no images. `scryfall_id`/
`scryfall_oracle_id` are stored as-is so a future feature (S4) can derive
an image URL when it actually needs one -- deciding the image-hosting
strategy itself is out of this item's scope (2026-08-05 decision).

Price data (`GET /cards/{id}/prices`, documented in `auth_roles.md` before
this item existed) is deliberately not built here -- `AllPrices.json` is a
separate MTGJSON file this item never imports; see F8's doc-correction
task.
"""

import uuid
from datetime import date as date_type
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MTGSet(Base):
    """A Magic set (`mj_sets` table, `Set` in MTGJSON's own data model).

    Named `MTGSet`, not `Set`, to avoid shadowing the builtin.
    """

    __tablename__ = "mj_sets"

    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    release_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    block: Mapped[str | None] = mapped_column(String(255), nullable=True)
    base_set_size: Mapped[int] = mapped_column(Integer, nullable=False)
    total_set_size: Mapped[int] = mapped_column(Integer, nullable=False)
    keyrune_code: Mapped[str] = mapped_column(String(16), nullable=False)
    is_online_only: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


#: MTGJSON `layout` values whose *back* face is independently castable, i.e.
#: can be cast/played as its own spell rather than only reached by
#: transforming/unlocking the front face. Both faces are legitimate names for
#: the same card here (Adventure's instant half, a modal DFC's either face, a
#: split card's either half) so both are valid search keys. Every other
#: layout (`transform`, `prepare`, plain `normal`, and anything not yet
#: enumerated) is treated as front-face-only: its back face's name (e.g.
#: "Insectile Aberration", "Ancestral Recall") is real card text but not a
#: name you'd use to reference the card on its own, so `GET
#: /cards/search-by-name/{name}` never matches on it — only that layout's
#: front-face name or the card's full combined name do.
CASTABLE_BOTH_FACES_LAYOUTS: frozenset[str] = frozenset(
    {
        "adventure",
        "modal_dfc",
        "split",
    }
)


class Card(Base):
    """One printing+face of a card (`mj_cards` table).

    `id` is MTGJSON's own `uuid` (see module docstring) -- set explicitly
    on insert, never generated here.
    """

    __tablename__ = "mj_cards"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    set_code: Mapped[str] = mapped_column(
        String(8),
        ForeignKey("mj_sets.code", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    face_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    side: Mapped[str | None] = mapped_column(String(1), nullable=True)
    layout: Mapped[str] = mapped_column(
        String(32), nullable=False, default="normal", server_default="normal"
    )
    other_face_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    type_line: Mapped[str] = mapped_column(Text, nullable=False)
    types: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    supertypes: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    subtypes: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    mana_cost: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mana_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    colors: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    color_identity: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    rarity: Mapped[str] = mapped_column(String(32), nullable=False)
    number: Mapped[str] = mapped_column(String(16), nullable=False)
    scryfall_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    scryfall_oracle_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class MTGJSONImportRun(Base):
    """One `import_all_printings` attempt (`mj_import_runs` table).

    Written through its own short-lived session, independent of the main
    import transaction (`app/services/mtgjson/importer.py`'s
    `_ImportRunTracker`) -- `import_all_printings` only commits its
    sets/cards writes once at the end, so a status poll needs a separately
    and immediately committed row to see progress mid-run rather than
    nothing until the whole import finishes.
    """

    __tablename__ = "mj_import_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sets_upserted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    cards_upserted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
