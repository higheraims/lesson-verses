"""Read a lesson manuscript DOCX into the parts the verses edition needs.

The manuscript is flat text: every paragraph has the same style, and the structure is in
how lines are written. This reader looks only at the lines it uses:

    2031                                  masthead: year,
    JAN-MAR                               months,
    Vol. 12, No. 1                        volume and number,
    ... Division                          end of the fixed publication lines,
    Theme / Subtitle                      then the theme and subtitle (either may run
                                          over two paragraphs)
    Contents
    1. Lesson Title <tab> 5               Contents entries with their page numbers
    Sabbath, January 4, 2031 <tab> Lesson 1
    Lesson Title
    1. <tab> Day Title <tab> Sun, Dec 29  a study day,
    a. <tab> Question? Proverbs 3:5.      its lettered questions
    6. <tab> Personal Reflection <tab> Fri, Jan 3    Friday, skipped: it has no verses
                                          (older issues: "Personal Review Questions")

Everything else (foreword, quotations, offerings, back matter) is passed over. Dates,
numbers and page numbers are taken as printed, not recalculated.

Tracked changes are read as accepted: inserted text is kept and deleted text dropped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from .scripture import NBSP, Passage, find_passages

MONTHS = {m[:3].lower(): m for m in (
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December")}

_YEAR = re.compile(r"^(\d{4})$")
_MONTH_RANGE = re.compile(r"^([A-Za-z]{3,9})\.?\s*[-–]\s*([A-Za-z]{3,9})\.?(?:\s+(\d{4}))?$")
_VOLUME = re.compile(r"\bVol\.?\s*(\d+),?\s*No\.?\s*(\d+)", re.I)
_CONTENTS_ENTRY = re.compile(r"^(\d+)\.\s*(.+?)\s*\t[\s.…]*(\d+)$")
_LESSON = re.compile(r"^(?:(Sabbath\b.*?)\s+)?Lesson\s+(\d+)$", re.I)
_REFLECTION = re.compile(r"^(?:\d\.\s*)?personal\s+(?:reflection|review)\b", re.I)
_DAY = re.compile(r"^(\d)\.\s*(.+?)\s+((?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)[a-z]*\.?,\s*.+)$")
_QUESTION = re.compile(r"^([a-z])\.\s+(.+)$")

_W_T, _W_TAB, _W_BR, _W_CR, _W_R = (qn(t) for t in ("w:t", "w:tab", "w:br", "w:cr", "w:r"))


class ManuscriptError(Exception):
    """The file is not a manuscript this reader understands."""


@dataclass
class Question:
    letter: str
    prompt: str
    passages: list[Passage]


@dataclass
class Day:
    number: int
    title: str
    date: str               # "Sun, Dec 29"
    questions: list[Question] = field(default_factory=list)


@dataclass
class Lesson:
    number: int
    sabbath: str            # "Sabbath, January 4, 2031"
    title: str = ""
    days: list[Day] = field(default_factory=list)


@dataclass
class ContentsEntry:
    number: int
    title: str
    page: str


@dataclass
class Manuscript:
    year: str = ""
    months: str = ""        # "January–March"
    volume: str = ""        # "Vol. 12, No. 1"
    theme: str = ""
    subtitle: str = ""
    contents: list[ContentsEntry] = field(default_factory=list)
    lessons: list[Lesson] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)   # oddities worth telling the user


def read_manuscript(path: str | Path) -> Manuscript:
    try:
        document = Document(str(path))
    except Exception as exc:
        raise ManuscriptError(f"{Path(path).name} could not be opened as a Word document ({exc}).")
    return parse_lines([_text(p._p) for p in document.paragraphs])


def _text(paragraph) -> str:
    """Paragraph text with tabs kept. Walks the runs directly because python-docx's own
    .text skips runs inside a tracked insertion; deleted text is w:delText, so it is
    never picked up."""
    out = []
    for run in paragraph.iter(_W_R):
        for node in run:
            if node.tag == _W_T:
                out.append(node.text or "")
            elif node.tag == _W_TAB:
                out.append("\t")
            elif node.tag in (_W_BR, _W_CR):
                out.append(" ")
    return "".join(out)


def _clean(line: str) -> str:
    """For matching only: NBSP as a plain space, ends trimmed."""
    return line.replace(NBSP, " ").strip()


def _tidy(text: str) -> str:
    """For printing: runs of spaces and tabs collapsed, NBSPs kept."""
    return re.sub(r"[ \t]+", " ", text).strip()


def parse_lines(lines: list[str]) -> Manuscript:
    """Build the Manuscript from paragraph texts in document order (blank lines allowed)."""
    lines = [line for line in lines if line.strip()]
    ms = Manuscript()
    i = _parse_masthead(lines, ms)
    lesson: Lesson | None = None
    day: Day | None = None
    in_contents = False
    while i < len(lines):
        raw, line = lines[i], _clean(lines[i])
        i += 1
        if line == "Contents":
            in_contents = True
        elif m := _LESSON.match(line):
            in_contents = False
            lesson = Lesson(number=int(m.group(2)), sabbath=_tidy(m.group(1) or ""))
            ms.lessons.append(lesson)
            day = None
            if i < len(lines):
                lesson.title = _tidy(lines[i])
                i += 1
        elif in_contents and (m := _CONTENTS_ENTRY.match(raw.strip())):
            ms.contents.append(ContentsEntry(int(m.group(1)), _tidy(m.group(2)), m.group(3)))
        elif lesson is None:
            continue
        elif _REFLECTION.match(line):
            day = None
        elif m := _DAY.match(raw.strip()):
            day = Day(number=int(m.group(1)), title=_tidy(m.group(2)), date=_tidy(m.group(3)))
            lesson.days.append(day)
        elif day is not None and (m := _QUESTION.match(raw.strip())):
            text = m.group(2)
            # A stray paragraph break can split a question; the second half then starts
            # in lowercase ("Although it rained," / "what did they do? Genesis 7:7.").
            while (i < len(lines) and _clean(lines[i])[:1].islower()
                   and not _QUESTION.match(_clean(lines[i]))):
                text += " " + lines[i]
                i += 1
                ms.notes.append(f"Lesson {lesson.number}, day {day.number}, question "
                                f"{m.group(1)} runs over two paragraphs; read as one.")
            prompt, passages = find_passages(_tidy(text))
            day.questions.append(Question(m.group(1), prompt, passages))

    if not ms.year or not ms.months:
        raise ManuscriptError("The year and months were not found at the top of the file.")
    if not ms.lessons:
        raise ManuscriptError("No lessons were found (expected lines like "
                              "\"Sabbath, January 4, 2031 <tab> Lesson 1\").")
    _check_contents(ms)
    _check_letters(ms)
    return ms


def _check_letters(ms: Manuscript) -> None:
    """Note a day whose questions aren't lettered a, b, c… The edition prints the letters
    as the manuscript has them, so a slip there shows up here rather than being hidden."""
    for lesson in ms.lessons:
        for day in lesson.days:
            letters = [q.letter for q in day.questions]
            if letters != [chr(ord("a") + k) for k in range(len(letters))]:
                ms.notes.append(f"Lesson {lesson.number}, day {day.number}: questions are "
                                f"lettered {', '.join(letters)}.")


def _check_contents(ms: Manuscript) -> None:
    """Note where the Contents and the lesson headers disagree. The edition prints the
    lesson headers' titles; the Contents supplies only the page numbers."""
    if ms.contents and len(ms.contents) != len(ms.lessons):
        ms.notes.append(f"The Contents lists {len(ms.contents)} lessons but the file has "
                        f"{len(ms.lessons)}.")
    titles = {lesson.number: lesson.title for lesson in ms.lessons}
    for entry in ms.contents:
        title = titles.get(entry.number)
        if title is not None and entry.title != title:
            ms.notes.append(f"Lesson {entry.number} is \"{title}\" but the Contents has "
                            f"\"{entry.title}\".")


def _parse_masthead(lines: list[str], ms: Manuscript) -> int:
    """Read the lines before "Contents" (or before the first lesson, if there is no
    Contents); return the index where the masthead ends."""
    end = next((i for i, line in enumerate(lines)
                if _clean(line) == "Contents" or _LESSON.match(_clean(line))), len(lines))
    rest_from = 0
    for i, raw in enumerate(lines[:end]):
        line = _clean(raw)
        if m := _YEAR.match(line):
            ms.year = m.group(1)
        elif (m := _MONTH_RANGE.match(line)) and m.group(1)[:3].lower() in MONTHS:
            first, last = MONTHS[m.group(1)[:3].lower()], MONTHS.get(m.group(2)[:3].lower(), "")
            ms.months = f"{first}–{last}" if last else first
            ms.year = m.group(3) or ms.year
        elif m := _VOLUME.search(line):
            ms.volume = f"Vol. {m.group(1)}, No. {m.group(2)}"
            rest_from = max(rest_from, i + 1)
        elif line.endswith("Division"):
            rest_from = i + 1

    # Theme and subtitle follow the publication lines. A paragraph that ends in a space
    # continues on the next one ("Rivers and " + "Mountains").
    parts: list[str] = []
    joining = False
    for raw in lines[rest_from:end]:
        line = _clean(raw)
        if _YEAR.match(line) or _MONTH_RANGE.match(line) or _VOLUME.search(line):
            continue
        if joining:
            parts[-1] += " " + line
        else:
            parts.append(line)
        joining = raw != raw.rstrip()
    parts = [_tidy(p) for p in parts]
    ms.theme = parts[0] if parts else ""
    ms.subtitle = parts[1] if len(parts) > 1 else ""
    for extra in parts[2:]:
        ms.notes.append(f"Ignored an extra line under the subtitle: \"{extra}\".")
    return end
