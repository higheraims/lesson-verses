# Lesson Verses

A Windows program that turns a lesson manuscript (a Word file) into its verses edition:
the lesson questions, each followed by its Bible references written out in full from the
King James Version.

## Using it

1. Get `Lesson Verses.exe` from whoever maintains this repository. They download it from
   the latest release, or from the newest build's artifacts on the Actions page.
2. Double-click it, choose the manuscript, then choose where to save the edition.
   Dropping a manuscript onto the exe does the same thing, starting from that file.

Nothing is installed and nothing goes online. The KJV text is inside the exe.

The exe is not code-signed, so the first run may show "Windows protected your PC". Click
**More info**, then **Run anyway**.

If a reference doesn't match a KJV verse (a typo such as `Jhon 3:16`, or a verse that
doesn't exist), the program stops and lists every such reference rather than producing an
edition with gaps. After a successful conversion it may also list notes on the
manuscript: question letters out of order, a question broken across two paragraphs, or a
lesson title that differs from the Contents. The edition is still written; the notes are
for fixing the manuscript.

## What it reads

The manuscript is flat text, with structure carried by how lines are written. The
program uses only these lines and passes over everything else:

| Line | Example |
| --- | --- |
| Year, months, volume | `2031`, `JAN-MAR`, `Vol. 12, No. 1` |
| Theme and subtitle | the lines after the one ending `Division` |
| Contents entry | `1. Lesson Title <tab> 5` |
| Lesson header, then title | `Sabbath, January 4, 2031 <tab> Lesson 1` |
| Study day | `1. <tab> Day Title <tab> Sun, Dec 29` |
| Question | `a. <tab> Question text? Proverbs 3:5, 6.` |
| Friday (skipped) | `6. Personal Reflection` or `PERSONAL REVIEW QUESTIONS` |

Dates, numbers and page numbers are printed as the manuscript has them. If the publisher
changes the layout, `lesson_verses/manuscript.py` is the file to teach; the output
layout is in `lesson_verses/verses_docx.py`.

## The code

| Path | What it is |
| --- | --- |
| `lesson_verses/app.py` | Dialogs, and `--convert IN OUT` for running without them |
| `lesson_verses/manuscript.py` | Reads the manuscript |
| `lesson_verses/scripture.py` | Finds references in a question and looks up their verses |
| `lesson_verses/verses_docx.py` | Writes the edition |
| `lesson_verses/kjv.tsv` | The KJV, one verse per line: book, chapter, verse, text |
| `tests/sample.py` | Writes a made-up manuscript with the known quirks, and checks its edition |

Run it from source with `python -m lesson_verses` (add `--convert IN OUT` to skip the
dialogs). The only dependency is `python-docx`.

### Testing

```sh
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest
```

### Releasing

Every push to `main` runs the tests on a Windows runner, builds the exe, converts the
sample manuscript with it, and attaches the exe to the run as an artifact. Pushing a tag
such as `v1.0.0` also publishes it as a release:

```sh
git tag v1.0.0
git push origin v1.0.0
```

To build locally, run `python build.py`. PyInstaller builds for the system it runs on, so
the Windows exe has to be built on Windows.
