#!/usr/bin/env python3
"""
office_render.py — render a Microsoft Office file (.docx/.pptx/.xlsx) to PDF and
then to page images, using the REAL installed Office app on macOS (Word /
PowerPoint / Excel) for a pixel-faithful result Claude Code can read.

Why real Office and not LibreOffice: LibreOffice substitutes fonts and lays out
complex tables/slides differently (e.g. it renders a 3-across team grid as a
vertical list, and shows the wrong typeface). Word/PowerPoint render exactly
what the user sees.

Usage:
  uv run --with docx2pdf python3 office_render.py INPUT [--out DIR] [--dpi 150]
                                                  [--format jpeg|png] [--pdf-only]

Output: writes PAGE images (INPUT-1.jpg, INPUT-2.jpg, ...) into --out (default:
alongside the input), and the intermediate PDF. Prints the image paths.

Requires (see SKILL.md for the one-time setup):
  - Microsoft Word/PowerPoint/Excel installed + signed in.
  - poppler for pdftoppm:  brew install poppler
  - For .docx: docx2pdf (run via `uv run --with docx2pdf`).
  - macOS Automation permission granted to the controlling terminal (one-time).
  - Either the Office app has Full Disk Access, OR the file lives in a folder
    the Office sandbox can read (Downloads/Documents/Desktop). This script
    auto-stages through ~/Downloads if a direct convert hits the sandbox.
"""
from __future__ import annotations
import argparse, os, shutil, subprocess, sys, tempfile
from pathlib import Path

APP = {".docx": "Microsoft Word", ".doc": "Microsoft Word",
       ".pptx": "Microsoft PowerPoint", ".ppt": "Microsoft PowerPoint",
       ".xlsx": "Microsoft Excel", ".xls": "Microsoft Excel"}


def osa(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(["osascript", "-e", script], capture_output=True, text=True)


def quit_app(app: str):
    osa(f'tell application "{app}" to quit saving no')


def applescript_to_pdf(ext: str, inp: str, pdf: str) -> subprocess.CompletedProcess:
    """PowerPoint/Excel export. `with timeout` is REQUIRED — the export easily
    exceeds the default Apple-event timeout and otherwise dies with -1712."""
    if ext in (".pptx", ".ppt"):
        return osa(f'''tell application "Microsoft PowerPoint"
    activate
    open POSIX file "{inp}"
    with timeout of 600 seconds
        save active presentation in (POSIX file "{pdf}") as save as PDF
    end timeout
    close active presentation saving no
end tell''')
    else:  # Excel
        return osa(f'''tell application "Microsoft Excel"
    open POSIX file "{inp}"
    with timeout of 600 seconds
        save active workbook in "{pdf}" as PDF file format
    end timeout
    close active workbook saving no
end tell''')


def convert_once(ext: str, inp: str, pdf: str):
    """Single conversion attempt at the given (already-decided) paths."""
    if ext in (".docx", ".doc"):
        # Word's AppleScript `save as` is broken on several Word builds (error
        # -1708 "doesn't understand save as"); docx2pdf uses a path that works.
        from docx2pdf import convert
        convert(inp, pdf)
        if not os.path.exists(pdf):
            raise RuntimeError("docx2pdf produced no output")
    else:
        r = applescript_to_pdf(ext, inp, pdf)
        if r.returncode != 0 or not os.path.exists(pdf):
            raise RuntimeError((r.stderr or "applescript failed").strip())


def to_pdf(inp: Path, pdf: Path):
    ext = inp.suffix.lower()
    if ext not in APP:
        sys.exit(f"unsupported file type: {ext}")
    quit_app(APP[ext])  # start from a clean app state
    try:
        convert_once(ext, str(inp), str(pdf))
        return
    except Exception as e1:
        # Most common cause: the Office sandbox can't read INPUT's folder (e.g.
        # /tmp) and pops a "Grant File Access" dialog -> the convert errors
        # ("Message not understood"). Stage through ~/Downloads, which the
        # sandbox can reach, then move the PDF back.
        stage = Path.home() / "Downloads" / ".office-render"
        stage.mkdir(parents=True, exist_ok=True)
        sin = stage / inp.name
        spdf = stage / (inp.stem + ".pdf")
        shutil.copy2(inp, sin)
        try:
            quit_app(APP[ext])
            convert_once(ext, str(sin), str(spdf))
            shutil.move(str(spdf), str(pdf))
        except Exception as e2:
            sys.exit(f"conversion failed.\n  direct: {e1}\n  staged: {e2}\n"
                     f"Fix: grant '{APP[ext]}' Full Disk Access "
                     f"(System Settings > Privacy & Security > Full Disk Access), "
                     f"or keep the file in Downloads/Documents/Desktop.")
        finally:
            sin.unlink(missing_ok=True)


def to_images(pdf: Path, out: Path, dpi: int, fmt: str) -> list[str]:
    if not shutil.which("pdftoppm"):
        sys.exit("pdftoppm not found — install poppler:  brew install poppler")
    stem = pdf.stem
    prefix = out / stem
    flag = "-png" if fmt == "png" else "-jpeg"
    subprocess.run(["pdftoppm", flag, "-r", str(dpi), str(pdf), str(prefix)], check=True)
    ext = "png" if fmt == "png" else "jpg"
    return sorted(str(p) for p in out.glob(f"{stem}-*.{ext}"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out", default=None, help="output dir (default: next to input)")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--format", choices=["jpeg", "png"], default="jpeg")
    ap.add_argument("--pdf-only", action="store_true")
    a = ap.parse_args()

    inp = Path(a.input).expanduser().resolve()
    if not inp.exists():
        sys.exit(f"not found: {inp}")
    out = Path(a.out).expanduser().resolve() if a.out else inp.parent
    out.mkdir(parents=True, exist_ok=True)
    pdf = out / (inp.stem + ".pdf")

    to_pdf(inp, pdf)
    print(f"PDF: {pdf}")
    if a.pdf_only:
        return
    imgs = to_images(pdf, out, a.dpi, a.format)
    print(f"{len(imgs)} page image(s):")
    for p in imgs:
        print(p)


if __name__ == "__main__":
    main()
