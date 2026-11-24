"""Student list filtering and ordering (accent- and case-insensitive)."""

import unicodedata
from collections.abc import Iterable

from report_generator.db.models import Student


def fold(text: str) -> str:
    """'López' -> 'lopez', so searches and sorting ignore accents and case."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def filter_students(students: Iterable[Student], query: str = "", cert: str = "") -> list[Student]:
    needle = fold(query.strip())
    matches = [
        s
        for s in students
        if (not needle or needle in fold(s.name)) and (not cert or s.certification == cert)
    ]
    return sorted(matches, key=lambda s: (fold(s.name), s.id or 0))
