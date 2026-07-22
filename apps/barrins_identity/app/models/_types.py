"""SQLAlchemy types compatible with PostgreSQL JSONB and SQLite JSON.

Copied from apps/barrins_api/app/models/_types.py — small, self-contained
utility, duplicated per app rather than shared (same rationale as
identity_client, see platform.md §4).
"""

import json
from typing import Literal, cast, overload

from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import MappedColumn, mapped_column
from sqlalchemy.types import TypeEngine

JsonPrimitive = str | int | float | bool | None
JsonValue = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]


class JSONBCompat(TypeDecorator[JsonValue]):
    """SQLAlchemy type compatible with PostgreSQL JSONB and SQLite JSON.

    On PostgreSQL: uses JSONB (binary storage, GIN-indexable).
    On any other dialect (e.g. SQLite): falls back to standard JSON.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[JsonValue]:
        if dialect.name == "postgresql":
            return cast(
                TypeEngine[JsonValue],
                dialect.type_descriptor(postgresql.JSONB(astext_type=JSON())),
            )
        return cast(TypeEngine[JsonValue], dialect.type_descriptor(JSON()))

    def process_bind_param(
        self, value: JsonValue | None, dialect: Dialect
    ) -> JsonValue | None:
        if value is None:
            return None
        try:
            json.dumps(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"JSONBCompat: type not JSON-serializable "
                f"(received type: {type(value).__name__})"
            ) from exc
        return value

    def process_result_value(
        self, value: JsonValue | None, dialect: Dialect
    ) -> JsonValue | None:
        return value


@overload
def jsonb_column(
    *, default: JsonValue | None = ..., nullable: Literal[False]
) -> MappedColumn[JsonValue]: ...


@overload
def jsonb_column(
    *, default: JsonValue | None = ..., nullable: Literal[True]
) -> MappedColumn[JsonValue | None]: ...


def jsonb_column(
    *,
    default: JsonValue | None = None,
    nullable: bool = False,
) -> MappedColumn[JsonValue] | MappedColumn[JsonValue | None]:
    """Create a ``mapped_column`` of type ``JSONBCompat``."""
    if default is not None:
        return mapped_column(JSONBCompat, default=default, nullable=nullable)
    return mapped_column(JSONBCompat, nullable=nullable)
