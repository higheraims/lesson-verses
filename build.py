"""Build the single-file program with PyInstaller.

    python -m pip install -r requirements.txt -r requirements-dev.txt
    python build.py

Writes dist/Lesson Verses.exe on Windows (dist/Lesson Verses elsewhere). PyInstaller
builds for the system it runs on, so the Windows exe has to be built on Windows. The CI
workflow runs this same script.
"""

import os
from pathlib import Path

import PyInstaller.__main__

HERE = Path(__file__).resolve().parent

PyInstaller.__main__.run([
    str(HERE / "lesson_verses" / "__main__.py"),
    "--name", "Lesson Verses",
    "--onefile",
    "--windowed",               # no console window behind the dialogs
    "--noconfirm",
    "--clean",
    "--paths", str(HERE),
    "--add-data", f"{HERE / 'lesson_verses' / 'kjv.tsv'}{os.pathsep}lesson_verses",
    "--collect-data", "docx",   # python-docx's blank template, the base of every new file
])
