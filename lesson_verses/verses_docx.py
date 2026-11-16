"""Write the verses edition: the lesson questions with every reference written out in full.

Layout:

* US Letter, 0.5" margins, Times New Roman 12 pt, justified, 1.2 line spacing.
* No page breaks, footers or page numbers. Blank paragraphs do the spacing, with four
  between one lesson and the next.
* Cover: theme (18 pt bold), subtitle (14 pt italic), then "January–March 2031" and
  "Vol. 12, No. 1" separated by two tabs, all centred.
* Contents: the lesson titles with the page numbers from the manuscript's own Contents,
  dot-leadered.
  Plain text rather than a Word TOC field, because the numbers point into the printed
  manuscript and Word would renumber a field against this file.
* Each lesson: "SABBATH, JANUARY 4, 2031 <tab> LESSON 1" in bold caps, then the title
  centred in 20 pt bold italic.
* Each study day: a grey-highlighted band "1. DAY TITLE <tab> Sun, Dec 29", each question
  in bold as "a. <tab> prompt", and one paragraph per reference: the reference bold and
  underlined, then the verse text. Verse numbers are superscript, except the first verse
  of a passage, which the reference already names.
"""

from __future__ import annotations

from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor, Twips

from .manuscript import Day, Lesson, Manuscript
from .scripture import Bible, Passage, printed_label

RIGHT_TAB = Twips(10773)        # 7.48", just inside the 7.5" text width
PROMPT_TAB = Twips(504)         # 0.35"
LEADER_TAB = Twips(5900)        # Contents: dots run to 4.10" ...
PAGE_NUMBER_TAB = Twips(6240)   # ... and the page number is right-aligned at 4.33"
LESSON_GAP = 4                  # blank paragraphs between lessons


class MissingVerses(Exception):
    """References that matched no verse. The edition is not written with gaps in it."""


def unresolved(ms: Manuscript, bible: Bible) -> list[str]:
    return [f"Lesson {lesson.number}, day {day.number}, question {q.letter}: {p.label}"
            for lesson in ms.lessons for day in lesson.days for q in day.questions
            for p in q.passages if not bible.verses(p)]


def build(ms: Manuscript, bible: Bible) -> bytes:
    """The finished .docx as bytes. Raises MissingVerses listing every bad reference."""
    bad = unresolved(ms, bible)
    if bad:
        raise MissingVerses("These references don't match any KJV verse. Fix them in the "
                            "manuscript and try again:\n\n" + "\n".join(bad))
    doc = _new_document()
    _cover(doc, ms)
    _contents(doc, ms)
    for lesson in ms.lessons:
        _lesson(doc, lesson, bible)
    out = BytesIO()
    doc.save(out)
    return out.getvalue()


def _new_document():
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    section.left_margin = section.right_margin = Inches(0.5)
    section.top_margin = section.bottom_margin = Inches(0.5)
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    pf = normal.paragraph_format
    pf.line_spacing = 1.2
    pf.space_before = pf.space_after = Pt(0)
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    # Widow/orphan control off, so Word paginates the edition predictably.
    widow = OxmlElement("w:widowControl")
    widow.set(qn("w:val"), "0")
    normal.element.get_or_add_pPr().insert(0, widow)
    return doc


def _run(paragraph, text="", *, bold=False, italic=False, underline=False, caps=False,
         size=None, highlight=None, tab_before=False):
    run = paragraph.add_run()
    if tab_before:
        run.add_tab()
    if text:
        run.add_text(text)
    run.bold = bold or None
    run.italic = italic or None
    run.underline = underline or None
    if caps:
        run.font.all_caps = True
    if size:
        run.font.size = size
    if highlight is not None:
        run.font.highlight_color = highlight
    return run


def _blank(doc, n=1):
    for _ in range(n):
        doc.add_paragraph()


def _centred(doc, text, **fmt):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(p, text, **fmt)
    return p


def _cover(doc, ms: Manuscript) -> None:
    if ms.theme:
        _centred(doc, ms.theme, bold=True, size=Pt(18))
    if ms.subtitle:
        _centred(doc, ms.subtitle, italic=True, size=Pt(14))
    _blank(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(p, f"{ms.months} {ms.year}")
    if ms.volume:
        _run(p, tab_before=True)
        _run(p, ms.volume, tab_before=True)


def _contents(doc, ms: Manuscript) -> None:
    pages = {e.number: e.page for e in ms.contents}
    _blank(doc, 2)
    head = doc.add_paragraph()
    head.paragraph_format.line_spacing = 1.0
    _run(head, "Contents", bold=True).font.name = "Arial"
    _blank(doc)
    for lesson in ms.lessons:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        tabs = p.paragraph_format.tab_stops
        tabs.add_tab_stop(LEADER_TAB, WD_TAB_ALIGNMENT.LEFT, WD_TAB_LEADER.DOTS)
        tabs.add_tab_stop(PAGE_NUMBER_TAB, WD_TAB_ALIGNMENT.RIGHT)
        _run(p, f"{lesson.number}. {lesson.title}")
        _run(p, tab_before=True)
        _run(p, pages.get(lesson.number, ""), tab_before=True)
    _blank(doc)


def _lesson(doc, lesson: Lesson, bible: Bible) -> None:
    _blank(doc, LESSON_GAP)
    band = doc.add_paragraph()
    band.alignment = WD_ALIGN_PARAGRAPH.LEFT
    band.paragraph_format.line_spacing = 1.0
    band.paragraph_format.tab_stops.add_tab_stop(RIGHT_TAB, WD_TAB_ALIGNMENT.RIGHT)
    _run(band, lesson.sabbath or "Sabbath", bold=True, caps=True)
    _run(band, f"Lesson {lesson.number}", bold=True, caps=True, tab_before=True)
    title = _centred(doc, lesson.title, bold=True, italic=True, size=Pt(20))
    title.paragraph_format.line_spacing = 1.0
    title.paragraph_format.space_before = Inches(0.2)
    for day in lesson.days:
        _day(doc, day, bible)


def _day(doc, day: Day, bible: Bible) -> None:
    _blank(doc)
    band = doc.add_paragraph()
    band.paragraph_format.tab_stops.add_tab_stop(RIGHT_TAB, WD_TAB_ALIGNMENT.RIGHT)
    grey = WD_COLOR_INDEX.GRAY_25
    # The trailing spaces carry the highlight a character past the text at each end.
    _run(band, f"{day.number}. {day.title.upper()} ", bold=True, caps=True, highlight=grey)
    _run(band, bold=True, caps=True, highlight=grey, tab_before=True)
    _run(band, f"{day.date} ", bold=True, highlight=grey)
    for q in day.questions:
        _blank(doc)
        p = doc.add_paragraph()
        p.paragraph_format.tab_stops.add_tab_stop(PROMPT_TAB, WD_TAB_ALIGNMENT.LEFT)
        _run(p, f"{q.letter}.", bold=True)
        _run(p, q.prompt, bold=True, tab_before=True)
        for passage in q.passages:
            _passage(doc, passage, bible)


def _passage(doc, passage: Passage, bible: Bible) -> None:
    _blank(doc)
    p = doc.add_paragraph()
    p.paragraph_format.tab_stops.add_tab_stop(PROMPT_TAB, WD_TAB_ALIGNMENT.LEFT)
    _run(p, printed_label(passage), bold=True, underline=True)
    _run(p, " ", bold=True)
    verses = bible.verses(passage)
    for i, (number, text) in enumerate(verses):
        if i:
            p.add_run(str(number)).font.superscript = True
            text = " " + text
        p.add_run(text if i == len(verses) - 1 else text + " ")
