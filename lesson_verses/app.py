"""Lesson Verses: the program around the conversion.

    Lesson Verses.exe                     choose the manuscript and where to save, in dialogs
    Lesson Verses.exe FILE.docx ...       the same, starting from the given file(s); this is
                                          what dropping files on the exe does
    Lesson Verses.exe --convert IN OUT    no windows: convert IN to OUT, exit 0 on success
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .manuscript import ManuscriptError, read_manuscript
from .scripture import Bible
from .verses_docx import MissingVerses, build

APP_NAME = "Lesson Verses"
KJV = Path(__file__).resolve().parent / "kjv.tsv"


class ConversionError(Exception):
    """A problem to show the user as it is, without a traceback."""


def convert(src: Path, dst: Path) -> list[str]:
    """Write the verses edition of `src` to `dst`. Returns notes about the manuscript."""
    if not src.is_file():
        raise ConversionError(f"{src} does not exist.")
    try:
        ms = read_manuscript(src)
        data = build(ms, Bible(KJV))
    except (ManuscriptError, MissingVerses) as exc:
        raise ConversionError(f"{src.name}: {exc}")
    try:
        dst.write_bytes(data)
    except PermissionError:
        raise ConversionError(f"Could not write {dst.name}. If it is open in Word, close it "
                              f"and try again.")
    return ms.notes


def default_output(src: Path) -> Path:
    return src.with_name(f"{src.stem} - Verses.docx")


def _say(message: str) -> None:
    # A --windowed build has no console, so sys.stderr is None there.
    if sys.stderr:
        print(message, file=sys.stderr)


def run_headless(src: str, dst: str) -> int:
    try:
        notes = convert(Path(src), Path(dst))
    except ConversionError as exc:
        _say(str(exc))
        return 1
    for note in notes:
        _say(f"note: {note}")
    return 0


def open_file(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def run_gui(paths: list[str]) -> int:
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.withdraw()
    if not paths:
        picked = filedialog.askopenfilename(
            title=f"{APP_NAME}: choose the lesson manuscript",
            filetypes=[("Word documents", "*.docx"), ("All files", "*.*")])
        if not picked:
            return 0
        paths = [picked]

    failed = 0
    for name in paths:
        src = Path(name)
        suggested = default_output(src)
        out = filedialog.asksaveasfilename(
            title=f"{APP_NAME}: save the verses edition of {src.name}",
            initialdir=str(suggested.parent), initialfile=suggested.name,
            defaultextension=".docx", filetypes=[("Word documents", "*.docx")])
        if not out:
            continue
        dst = Path(out)
        try:
            notes = convert(src, dst)
        except ConversionError as exc:
            failed += 1
            messagebox.showerror(APP_NAME, str(exc))
            continue
        except Exception as exc:    # a bug in this program: say so rather than vanish
            failed += 1
            messagebox.showerror(
                APP_NAME, f"Something went wrong converting {src.name}:\n\n"
                          f"{type(exc).__name__}: {exc}\n\nPlease send this message and the "
                          f"manuscript to whoever gave you this program.")
            continue
        message = f"Saved {dst.name}."
        if notes:
            message += "\n\nNotes on the manuscript:\n" + "\n".join(f"- {n}" for n in notes)
        if messagebox.askyesno(APP_NAME, message + "\n\nOpen it now?"):
            open_file(dst)
    root.destroy()
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--convert"]:
        if len(argv) != 3:
            _say("usage: --convert MANUSCRIPT.docx OUTPUT.docx")
            return 2
        return run_headless(argv[1], argv[2])
    return run_gui(argv)
