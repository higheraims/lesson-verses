"""Scripture references: find them in a question and look up their KJV text.

A question ends with its references, as the manuscript prints them:

    What does the psalmist say about the shepherd? Psalm 23:1, 2; John 10:11.

find_passages() splits that into the prompt ("What does … the shepherd?") and one Passage
per reference ("Psalm 23:1, 2", "John 10:11"). A later reference with no book
name ("Exodus 20:8; 31:13") takes the book of the one before it. A note in parentheses
("Mark 4:3 (compare verse 14)") stays in the printed label but is not looked up.

Bible.verses() turns a Passage into its verses, from kjv.tsv next to this file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

NBSP = "\xa0"
EN_DASH = "–"

BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth",
    "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
    "Nehemiah", "Esther", "Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon",
    "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah",
    "Malachi", "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians",
    "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians", "1 Thessalonians",
    "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James",
    "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation",
]

# Other spellings, lowercase. Every name in BOOKS is also accepted as written.
_ALIASES = {
    "psalm": "Psalms", "song of songs": "Song of Solomon", "canticles": "Song of Solomon",
    "revelations": "Revelation",
    "gen": "Genesis", "ex": "Exodus", "exo": "Exodus", "lev": "Leviticus", "num": "Numbers",
    "deut": "Deuteronomy", "josh": "Joshua", "judg": "Judges", "1 sam": "1 Samuel",
    "2 sam": "2 Samuel", "1 chr": "1 Chronicles", "2 chr": "2 Chronicles", "neh": "Nehemiah",
    "est": "Esther", "ps": "Psalms", "psa": "Psalms", "prov": "Proverbs",
    "eccl": "Ecclesiastes", "isa": "Isaiah", "jer": "Jeremiah", "lam": "Lamentations",
    "eze": "Ezekiel", "ezek": "Ezekiel", "dan": "Daniel", "hos": "Hosea", "obad": "Obadiah",
    "jon": "Jonah", "mic": "Micah", "nah": "Nahum", "hab": "Habakkuk", "zeph": "Zephaniah",
    "hag": "Haggai", "zech": "Zechariah", "mal": "Malachi", "matt": "Matthew", "mt": "Matthew",
    "mk": "Mark", "lk": "Luke", "jn": "John", "rom": "Romans", "1 cor": "1 Corinthians",
    "2 cor": "2 Corinthians", "gal": "Galatians", "eph": "Ephesians", "phil": "Philippians",
    "col": "Colossians", "1 thess": "1 Thessalonians", "2 thess": "2 Thessalonians",
    "1 tim": "1 Timothy", "2 tim": "2 Timothy", "tit": "Titus", "phlm": "Philemon",
    "heb": "Hebrews", "jas": "James", "1 pet": "1 Peter", "2 pet": "2 Peter", "rev": "Revelation",
}
BOOK_NAMES = {**{b.lower(): b for b in BOOKS}, **_ALIASES}

# Books with one chapter: "Jude 14" is verse 14, not chapter 14.
SINGLE_CHAPTER = {"Obadiah", "Philemon", "2 John", "3 John", "Jude"}

# Longest first, so "1 John" wins over "John" and "Song of Solomon" over "Song".
_BOOK = "(?:" + "|".join(re.escape(k) for k in sorted(BOOK_NAMES, key=len, reverse=True)) + r")\b"
_BOOK_RE = re.compile(_BOOK, re.IGNORECASE)

# A run of references: a book and a number, then nothing but more references. Prose words
# end the run, so a reference in the middle of a sentence doesn't swallow the rest of it.
_REF_RUN = re.compile(
    _BOOK + r"\s*\d(?:\s*" + _BOOK + r"|\s*\([^)]*\)|[\d:,\-–;]|\s(?=[\d(]))*",
    re.IGNORECASE)

_NUMBERED_BOOK = re.compile(r"^([1-3]) ")
_DIGIT_RANGE = re.compile(r"(?<=\d)\s*[-–]\s*(?=\d)")
_NOTE = re.compile(r"\s*\([^)]*\)")

# A whole-chapter reference asks for verses 1 to 176 (Psalm 119, the longest chapter) and
# keeps the ones that exist, so the lookup needs no table of chapter lengths.
_LONGEST_CHAPTER = 176


@dataclass
class Passage:
    label: str      # as printed: "Psalm 23:1, 2", book name as the manuscript wrote it
    book: str       # canonical name from BOOKS
    locations: str  # the chapter/verse part, notes removed: "1:29, 30"


def find_passages(question: str) -> tuple[str, list[Passage]]:
    """Split a question into the prompt to print and the passages to write out under it.

    A reference list at the end is removed from the prompt. A reference inside the
    sentence ("As Micah 6:8 says, …") stays in the prompt; its verses are written
    out only when the question has no reference list at the end."""
    text = question.strip()
    plain = text.replace(NBSP, " ")     # same length, so offsets carry over to `text`
    runs = list(_REF_RUN.finditer(plain))
    if not runs:
        return text, []
    last = runs[-1]
    if plain[last.end():].strip(" .") == "":
        # Keep the prompt's own "?" or "." and drop only a separator left before the list.
        prompt = text[:last.start()].rstrip().rstrip(";,").rstrip()
        return prompt, split_passages(last.group())
    return text, [p for run in runs for p in split_passages(run.group())]


def split_passages(refs: str) -> list[Passage]:
    """"Exodus 20:8; 31:13; John 3:16" -> one Passage per reference, book carried forward."""
    out: list[Passage] = []
    typed_book = book = None
    for part in _split_top_level(refs.replace(NBSP, " ")):
        part = part.strip().rstrip(".").strip()
        core = _NOTE.sub("", part).strip()
        if not core:
            continue
        m = _BOOK_RE.match(core)
        if m:
            typed_book, book = m.group(), BOOK_NAMES[m.group().lower()]
            locations = core[m.end():].strip()
        elif book and core[0].isdigit():
            locations, part = core, f"{typed_book} {part}"
        else:
            continue
        out.append(Passage(label=part, book=book, locations=locations))
    return out


def _split_top_level(refs: str) -> list[str]:
    """Split on ";" and on a comma that starts a new book, but never inside parentheses."""
    parts, start, depth = [], 0, 0
    for i, ch in enumerate(refs):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif depth == 0 and (ch == ";" or (ch == "," and _BOOK_RE.match(refs, i + 1 + _spaces(refs, i + 1)))):
            parts.append(refs[start:i])
            start = i + 1
    parts.append(refs[start:])
    return parts


def _spaces(s: str, i: int) -> int:
    return len(s[i:]) - len(s[i:].lstrip())


def printed_label(passage: Passage) -> str:
    """The label as it goes on the page: en dash in ranges, "1 John" kept on one line."""
    label = _DIGIT_RANGE.sub(EN_DASH, passage.label)
    return _NUMBERED_BOOK.sub(r"\1" + NBSP, label)


def verse_keys(passage: Passage) -> list[tuple[int, int]]:
    """Every (chapter, verse) the passage asks for, in order. Verses that don't exist (the
    tail of a whole-chapter request) are dropped by the lookup, not here."""
    out: list[tuple[int, int]] = []
    chapter = 1 if passage.book in SINGLE_CHAPTER else None
    for item in passage.locations.replace(EN_DASH, "-").split(","):
        start, _, end = (s.strip() for s in item.partition("-"))
        c1, v1 = _chapter_verse(start, chapter)
        if c1 is None:
            continue
        chapter = c1
        if v1 is None:                                  # "Genesis 1": the whole chapter
            out += [(c1, v) for v in range(1, _LONGEST_CHAPTER + 1)]
            continue
        if not end:
            out.append((c1, v1))
            continue
        c2, v2 = _chapter_verse(end, c1)
        if c2 is None or v2 is None or (c2, v2) < (c1, v1):
            continue
        for c in range(c1, c2 + 1):                     # "4:31-5:2" crosses a chapter
            first = v1 if c == c1 else 1
            last = v2 if c == c2 else _LONGEST_CHAPTER
            out += [(c, v) for v in range(first, last + 1)]
        chapter = c2
    return out


def _chapter_verse(token: str, chapter: int | None) -> tuple[int | None, int | None]:
    """"4:31" -> (4, 31). A bare "10" is a verse once a chapter is known, else a chapter."""
    m = re.fullmatch(r"(\d+)(?::(\d+))?", token)
    if not m:
        return None, None
    if m.group(2):
        return int(m.group(1)), int(m.group(2))
    if chapter is not None:
        return chapter, int(m.group(1))
    return int(m.group(1)), None


class Bible:
    """The KJV, loaded once from a tab-separated file: book, chapter, verse, text."""

    def __init__(self, path: Path | str):
        self._text: dict[tuple[str, int, int], str] = {}
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                book, chapter, verse, text = line.rstrip("\n").split("\t", 3)
                self._text[(book, int(chapter), int(verse))] = text

    def verses(self, passage: Passage) -> list[tuple[int, str]]:
        """(verse number, text) for every verse of the passage that exists."""
        return [(v, self._text[(passage.book, c, v)]) for c, v in verse_keys(passage)
                if (passage.book, c, v) in self._text]
