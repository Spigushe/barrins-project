"""Request/response contract for `POST /internal/karn/ingest` (ADR-13).

The request body *is* the payload
`apps/karn_tablets/karn_tablets/push.py::_payload` builds — defined
independently here (Constitution §4.3: API contracts are owned by the API
that exposes them, not imported from the caller). `apps/karn_tablets`'s
`tests/test_push.py` pins this shape; it must not drift.

`format` is the one addition the pipeline does not send today: it is
optional, and the ingester stamps `INGEST_DEFAULT_FORMAT`
("Duel Commander") when it is absent. A future multi-format pipeline can
start sending it with no breaking change.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.karn import KTWindowKind
from app.schemas.responses_base import BaseResponse

#: `kt_clustering_runs.format` / `kt_archetypes.format` are `String(120)`.
_FORMAT_MAX_LENGTH = 120
#: `kt_clustering_runs.algorithm` is `String(32)`.
_ALGORITHM_MAX_LENGTH = 32
#: `kt_clustering_runs.pipeline_version` is `String(32)`.
_PIPELINE_VERSION_MAX_LENGTH = 32
#: `kt_clustering_runs.window_label` is `String(64)`.
_WINDOW_LABEL_MAX_LENGTH = 64


class KarnIngestWindow(BaseModel):
    kind: KTWindowKind
    date_from: date
    date_to: date
    label: str = Field(max_length=_WINDOW_LABEL_MAX_LENGTH)


class KarnIngestArchetype(BaseModel):
    cluster_id: int
    deck_count: int = Field(ge=0)
    share: float = Field(ge=0.0, le=1.0)
    representative_mainboard: dict[str, int]
    representative_sideboard: dict[str, int]


class KarnIngestRequest(BaseModel):
    window: KarnIngestWindow
    algorithm: str = Field(max_length=_ALGORITHM_MAX_LENGTH)
    total_decks: int = Field(ge=0)
    pipeline_version: str = Field(max_length=_PIPELINE_VERSION_MAX_LENGTH)
    generated_at: datetime
    archetypes: list[KarnIngestArchetype] = []
    #: Not sent by the pipeline today — the ingester falls back to
    #: `INGEST_DEFAULT_FORMAT` when this is `None`.
    format: str | None = Field(default=None, max_length=_FORMAT_MAX_LENGTH)


class ResponseKarnIngest(BaseResponse):
    run_id: uuid.UUID
    #: Clusters in this run matched to an already-known archetype.
    archetypes_matched: int
    #: Clusters in this run that created a new archetype identity.
    archetypes_created: int
