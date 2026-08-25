"""Opaque cursor helpers for Tolaria News BFF list routes.

Keyset pagination, not `OFFSET`/`LIMIT`: `bs_*` keeps growing as new
tournaments are ingested, and an offset-based page 2 would silently skip
or repeat rows once new data lands underneath an in-progress paginated
scan. The cursor encodes the sort key(s) of the last row returned; the
next page filters strictly past it.
"""

import base64

_SEP = "\x1f"  # ASCII unit separator -- never appears in a UUID/date/name.


def encode_cursor(*parts: str) -> str:
    return base64.urlsafe_b64encode(_SEP.join(parts).encode()).decode()


def decode_cursor(cursor: str) -> list[str]:
    return base64.urlsafe_b64decode(cursor.encode()).decode().split(_SEP)
