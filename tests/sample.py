"""A made-up manuscript in the publisher's layout, and a check of its converted edition.

    python tests/sample.py write sample.docx
    python tests/sample.py check edition.docx

The text is invented apart from the KJV references. It includes the quirks seen in real
manuscripts: a theme split over two paragraphs, the publication and division on one line,
a stray letter after the issue number, Contents with dot leaders, the newer Friday header
("6. Personal Reflection") and the older one ("PERSONAL REVIEW QUESTIONS"), a question
broken over two paragraphs, a non-breaking space in "1 John", and tracked changes.
"""

from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

NBSP = "\xa0"

LINES = [
    "2031 ",
    "JAN-MAR",
    "Vol. 12, No. 1x",
    "Example Lessons Example Division",
    "Lessons in ",
    "Testing",
    "A made-up quarter for checking the converter",
    "Contents",
    "1. The First Example \t.......    5",
    "2. The Second Example \t10",
    "This paragraph stands for the masthead small print and is skipped.",
    "Foreword",
    "The foreword is skipped as well.",
    "Sabbath, January 4, 2031\tLesson 1",
    "The First Example",
    "MEMORY VERSE: “Trust in the LORD with all thine heart” (Proverbs 3:5).",
    "1. \tTHE FIRST DAY \tSun, Dec 29",
    "a. \tWhat is the first instruction? Proverbs 3:5–7.",
    "“A quotation paragraph, which the edition leaves out.”—Some Book, p.\xa05.",
    "b. \tWhat name was given? Exodus 3:14, 15; 1" + NBSP + "John 4:8.",
    "2. \tTHE WORD \tMon, Dec 30",
    "a. \tAs Hebrews 4:12 shows, how is the word described?",
    "b. \tWhat does the psalmist say? Psalm 119:105 (first part); 23:1.",
    "3. \tA LONG QUESTION \tTue, Dec 31",
    "a. \tThough this question was broken by a stray paragraph mark,",
    "\twhat does it still ask for? Jude 24, 25.",
    "6. \tPersonal Reflection \tFri, Jan 3",
    "a. \tA reflection question, with no references, which the edition leaves out.",
    "Sabbath, January 11, 2031\t Lesson 2",
    "The Second Example",
    "1. \tA CROSS-CHAPTER RANGE \tSun, Jan 5",
    "a. \tWhat follows across the chapter break? Colossians 3:23–4:1, 5.",
    "PERSONAL REVIEW QUESTIONS \tFri, Jan 10",
    "a. \tAn older-style Friday question.",
]


def write_sample(path: Path) -> None:
    doc = Document()
    for line in LINES:
        doc.add_paragraph(line)
        doc.add_paragraph()
    # A tracked change in lesson 2's question: "break" inserted, "gap" deleted.
    target = next(p for p in doc.paragraphs if "across the chapter break" in p.text)
    for run in list(target.runs):
        run._r.getparent().remove(run._r)
    target._p.append(_run("a. \tWhat follows across the chapter "))
    target._p.append(_tracked("w:ins", _run("break")))
    target._p.append(_tracked("w:del", _run("gap", deleted=True)))
    target._p.append(_run("? Colossians 3:23–4:1, 5."))
    doc.save(str(path))


def _run(text: str, deleted: bool = False):
    r = OxmlElement("w:r")
    for i, part in enumerate(text.split("\t")):
        if i:
            r.append(OxmlElement("w:tab"))
        t = OxmlElement("w:delText" if deleted else "w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = part
        r.append(t)
    return r


def _tracked(tag: str, run):
    el = OxmlElement(tag)
    el.set(qn("w:id"), "1" if tag == "w:ins" else "2")
    el.set(qn("w:author"), "Reviewer")
    el.append(run)
    return el


# Lines the converted edition must contain, each matched against the start of a paragraph.
EXPECTED = [
    "Lessons in Testing",
    "A made-up quarter for checking the converter",
    "January–March 2031\t\tVol. 12, No. 1",
    "1. The First Example\t\t5",
    "2. The Second Example\t\t10",
    "Sabbath, January 4, 2031\tLesson 1",
    "1. THE FIRST DAY \tSun, Dec 29",
    "a.\tWhat is the first instruction?",
    "Proverbs 3:5–7 Trust in the LORD with all thine heart; and lean not unto thine own understanding. 6 In all thy ways",
    "Exodus 3:14, 15 And God said unto Moses, I AM THAT I AM",
    "1" + NBSP + "John 4:8 He that loveth not knoweth not God; for God is love.",
    "a.\tAs Hebrews 4:12 shows, how is the word described?",
    "Hebrews 4:12 For the word of God is quick",
    "Psalm 119:105 (first part) Thy word is a lamp unto my feet",
    "Psalm 23:1 The LORD is my shepherd; I shall not want.",
    "a.\tThough this question was broken by a stray paragraph mark, what does it still ask for?",
    "Jude 24, 25 Now unto him that is able to keep you from falling",
    "a.\tWhat follows across the chapter break?",
    "Colossians 3:23–4:1, 5 And whatsoever ye do, do it heartily",
]
# Text that must not appear anywhere in the edition.
UNEXPECTED = [
    "A quotation paragraph", "reflection question", "older-style Friday", "foreword is skipped",
    "chapter gap", "MEMORY VERSE", "Mortify therefore",   # Colossians 3:5, not 4:5
]


def check_edition(path: Path) -> list[str]:
    """Problems with a converted sample, or [] if it is right."""
    paragraphs = [p.text for p in Document(str(path)).paragraphs]
    text = "\n".join(paragraphs)
    problems = [f"missing: {e!r}" for e in EXPECTED
                if not any(p.startswith(e) for p in paragraphs)]
    problems += [f"should not be there: {u!r}" for u in UNEXPECTED if u in text]
    colossians = next((p for p in paragraphs if p.startswith("Colossians")), "")
    if "5 Walk in wisdom" not in colossians:
        problems.append("Colossians 3:23–4:1, 5 should end with 4:5 (\"Walk in wisdom\")")
    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in ("write", "check"):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    if argv[0] == "write":
        write_sample(Path(argv[1]))
        return 0
    problems = check_edition(Path(argv[1]))
    for problem in problems:
        print(problem, file=sys.stderr)
    if not problems:
        print(f"{argv[1]}: all {len(EXPECTED)} expected lines present")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
