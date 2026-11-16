import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    # Built with PyInstaller. python-docx finds its blank template as
    # docx/parts/../templates, but docx/parts is compiled into the bundle, so the folder
    # doesn't exist on disk and Linux and macOS can't resolve the "..". Create it.
    (Path(sys._MEIPASS) / "docx" / "parts").mkdir(parents=True, exist_ok=True)

from lesson_verses.app import main  # noqa: E402

sys.exit(main())
