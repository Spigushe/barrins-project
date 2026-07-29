from datetime import date, datetime

_DEFAULT_FORMATS = ["%m/%d/%Y", "%B %d, %Y"]
_FALLBACK_DATE = datetime(1993, 8, 5).date()


def parse_date(date_text: object, formats: list[str] | None = None) -> date:
    formats = formats if formats is not None else _DEFAULT_FORMATS
    try:
        # datetime is a subclass of date, so it must be checked first —
        # isinstance(a_datetime, date) is also true and would otherwise
        # return the datetime object itself instead of its .date().
        if isinstance(date_text, datetime):
            return date_text.date()
        if isinstance(date_text, date):
            return date_text
        if isinstance(date_text, str):
            for fmt in formats:
                try:
                    return datetime.strptime(date_text.strip(), fmt).date()
                except ValueError:
                    continue
    except Exception as e:
        print(f"Error parsing date from string: {e} // input={date_text!r}")
    return _FALLBACK_DATE


def get_month_range(date_from: date, date_to: date) -> list[tuple[int, int]]:
    date_tuples: list[tuple[int, int]] = []
    for year in range(date_from.year, date_to.year + 1):
        start_month = date_from.month if year == date_from.year else 1
        end_month = date_to.month if year == date_to.year else 12
        for month in range(start_month, end_month + 1):
            date_tuples.append((year, month))
    return date_tuples
