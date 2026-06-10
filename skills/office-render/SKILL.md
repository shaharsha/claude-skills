---
name: office-render
description: Use when you need to SEE how a Microsoft Office file actually renders on macOS — preview/screenshot/convert a Word .docx, PowerPoint .pptx, or Excel .xlsx to PDF or page images, visually QA a generated Office document, check fonts/tables/slide layout, or read a doc's real appearance. Renders with the REAL Office apps (Word/PowerPoint/Excel), which is far more faithful than LibreOffice for fonts, complex tables, RTL/Hebrew, and slide layouts. macOS only.
---

# Office Render (macOS, real Microsoft Office)

## Overview

To verify how a `.docx`/`.pptx`/`.xlsx` looks, render it with the **installed
Microsoft Office app**, not LibreOffice. LibreOffice substitutes fonts and
re-flows complex layouts — it renders a 3-across team grid as a vertical list and
swaps the typeface, so what you "see" isn't what the user sees. Word/PowerPoint
produce the exact, pixel-faithful page; then convert the PDF to images you can read.

**Pipeline:** Office file → (real Word/PowerPoint/Excel) → PDF → (`pdftoppm`) → page JPGs.

## When to use

- "Show me / screenshot / preview this Word doc (or deck, or spreadsheet)."
- Visually QA a `.docx`/`.pptx` you just generated (python-docx, python-pptx) — confirm fonts, tables, images, and slide layout look right.
- A LibreOffice render looks wrong (substituted font, broken table/grid, RTL flipped) and you need the true rendering.
- Read a doc whose *layout* matters (not just text — for text, `markitdown`/`pandoc` is fine).

Skip when you only need the **text** (use `pandoc -t plain` / `python -m markitdown`), or you're not on macOS / Office isn't installed (fall back to `soffice --headless --convert-to pdf`, accepting lower fidelity).

## Usage

```bash
uv run --with docx2pdf python3 ~/.claude/skills/office-render/scripts/office_render.py \
    "/path/to/file.pptx" --out /tmp/render --dpi 150
```

It writes `file.pdf` + `file-1.jpg`, `file-2.jpg`, … into `--out` and prints the
paths. Then `Read` the JPGs. Options: `--format png`, `--pdf-only`, `--dpi N`
(150 is plenty; the page is small on screen). Works for `.docx`, `.pptx`, `.xlsx`.

One page often has trailing whitespace — crop to content before placing it
elsewhere (PIL: alpha/near-white bbox).

## One-time setup (do this once, then it's silent)

Two **separate** macOS permissions are involved — and Full Disk Access on your
*terminal* is NOT one of them (that confuses people):

1. **Automation** — lets the terminal control Office via Apple events.
   System Settings → Privacy & Security → **Automation** → enable **Microsoft
   Word / PowerPoint / Excel** under your terminal/IDE app (Terminal, iTerm,
   Ghostty, VS Code…). First run also pops a prompt — approve it once.

2. **File access** — Office apps are **sandboxed** and only read standard folders
   (Downloads, Documents, Desktop). Opening a file elsewhere (e.g. `/tmp`) pops a
   "Grant File Access" dialog and the convert fails. To use *any* path freely,
   give the Office apps themselves **Full Disk Access**: System Settings →
   Privacy & Security → **Full Disk Access** → "+" → add `/Applications/Microsoft
   Word.app` (and PowerPoint, Excel). Note: FDA on **the Office app**, not the
   terminal. **FDA only takes effect after the app is fully quit and
   relaunched** — if Office was already open when you flipped the switch, the
   running instance never picked it up and keeps prompting; quit it once (⌘Q or
   `killall "Microsoft PowerPoint"`). The script quits the app before each run,
   so it relaunches with FDA. (It also auto-stages through `~/Downloads` as a
   fallback if you skip FDA entirely.)

## Gotchas (each one cost real debugging — they're baked into the script)

| Symptom | Cause | Fix (in script) |
|---|---|---|
| `Message not understood` / "Grant File Access" dialog | Office **sandbox** can't read the file's folder (e.g. `/tmp`) | Give the Office app **Full Disk Access**, or keep files in Downloads/Documents/Desktop. Script auto-stages via `~/Downloads`. |
| `AppleEvent timed out (-1712)` | PDF export slower than the default Apple-event timeout | Wrap the save in `with timeout of 600 seconds` (script does this). |
| Word: `active document doesn't understand the "save as" message (-1708)` | Word's AppleScript `save as` is broken on several builds | Use **`docx2pdf`** for `.docx` (it uses a path that works), not raw `save as`. |
| `not allowed to send Apple events` | **Automation** permission not granted | Approve the first-run prompt / enable it in the Automation pane (≠ Full Disk Access on the terminal). |
| Grid/table renders as a vertical list; wrong font | You used **LibreOffice** | Use this skill (real Office). LibreOffice ≠ faithful for complex layouts. |

## How it works (reference)

- **`.docx` → PDF:** `docx2pdf` (drives real Word). Raw AppleScript `save as` is unreliable per the table above.
- **`.pptx` → PDF:** `osascript`: `save active presentation in (POSIX file PDF) as save as PDF` inside `with timeout`.
- **`.xlsx` → PDF:** `osascript`: `save active workbook in PDF as PDF file format` (best-effort; spreadsheets paginate awkwardly — set print area in the file for clean output).
- **PDF → images:** `pdftoppm -jpeg -r 150` (poppler).

The script quits the target app first for a clean state, then converts, then
renders. If a convert fails it retries once via `~/Downloads` and reports the
exact fix if it still fails.
