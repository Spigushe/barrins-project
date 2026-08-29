"""Shared slowapi Limiter instance.

Isolated in its own module so both app.main (registration on app.state)
and app.api.v1.auth (the @limiter.limit(...) decorator on POST /token)
can import it without a circular dependency.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
