"""Terminal progress-bar rendering shared by `sweep.py` and
`scripts/top8_check_gaps.py` -- both render a live `\\r`-updating bar on
stderr while chunking through a batch of work, off by default (no
terminal on a scheduled/cron invocation) and opt-in via `--progress`.
"""

from collections.abc import Iterator

#: Clears the current terminal line and returns the cursor to its start.
CLEAR_LINE = "\x1b[2K\r"
#: Moves the cursor up one line -- combined with `CLEAR_LINE` by callers
#: that render a sub-bar under a persistent chunk-advancement bar (see
#: `sweep.sweep`) to drop the finished sub-bar and rewrite the line above
#: it in place.
CURSOR_UP = "\x1b[1A"


def format_eta(seconds: float) -> str:
    """`H:MM:SS` (or `MM:SS` under an hour) -- `str(timedelta(...))`'s
    format, minus the microseconds it appends for a non-integer count."""
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def render_progress(
    done: int,
    total: int,
    elapsed: float,
    *,
    failed: int | None = None,
    prefix: str = "",
    suffix: str = "",
    width: int = 30,
) -> str:
    """`\\r`-prefixed single-line bar -- overwrites in place, never scrolls.

    ETA is derived from the observed per-item rate so far (`elapsed /
    done` extrapolated over what's left) -- accurate once a handful of
    items have completed, hidden before that.

    `failed`, when given, is reported alongside `done`/`total` as
    `(N failed)` -- `sweep.sweep` tracks POST failures this way;
    `top8_check_gaps.scrape_gaps` has nothing comparable to count, so it
    leaves this unset and passes a `suffix` (e.g. `"chunks"`) instead.
    `prefix` distinguishes multiple bars on screen at once, e.g. a
    chunk-advancement bar from a per-chunk sub-bar (see `sweep.sweep`).
    """
    filled = int(width * done / total) if total else width
    bar = "#" * filled + "-" * (width - filled)
    stats = f"{done}/{total}"
    if failed is not None:
        stats += f" ({failed} failed)"
    if suffix:
        stats += f" {suffix}"
    if done:
        remaining = elapsed / done * (total - done)
        stats += f" eta {format_eta(remaining)}"
    return f"\r{prefix}[{bar}] {stats}"


def chunked[T](items: list[T], size: int) -> Iterator[list[T]]:
    """Yields `items` sliced into consecutive lists of at most `size`."""
    for start in range(0, len(items), size):
        yield items[start : start + size]
