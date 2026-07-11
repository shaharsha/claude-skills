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
uv run --no-project --with docx2pdf python3 ~/.claude/skills/office-render/scripts/office_render.py \
    "/path/to/file.pptx" --out /tmp/render --dpi 150
```

`--no-project` is not optional cosmetics: without it, `uv run` tries to install
the *surrounding* directory as a project, and if the CWD (or any parent) holds a
`pyproject.toml` with no `[project]` table — common in tool-only repos — it aborts
with `No 'project' table found` before the script ever runs. `--no-project` tells
uv to just build an ephemeral env from `--with` and ignore whatever project it's
sitting inside. Harmless when there's no pyproject either, so always pass it.

It writes `file.pdf` + `file-1.jpg`, `file-2.jpg`, … into `--out` and prints the
paths. Then `Read` the JPGs. Options: `--format png`, `--pdf-only`, `--dpi N`
(150 is plenty; the page is small on screen). Works for `.docx`, `.pptx`, `.xlsx`.

One page often has trailing whitespace — crop to content before placing it
elsewhere (PIL: alpha/near-white bbox).

## One-time setup

Only **one** permission is required — Full Disk Access is NOT needed (the script
sidesteps the file-access sandbox entirely; see below):

1. **Automation** — lets the terminal control Office via Apple events.
   System Settings → Privacy & Security → **Automation** → enable **Microsoft
   Word / PowerPoint / Excel** under your terminal/IDE app (Terminal, iTerm,
   Ghostty, VS Code…). First run also pops a prompt — approve it once.

2. **File access — handled automatically, nothing to do.** Office apps are
   **sandboxed** and only freely read the standard folders (Downloads, Documents,
   Desktop); opening a file elsewhere would pop a "Grant File Access" powerbox.
   This script avoids that by **always running the Office app inside
   `~/Downloads`** — it copies INPUT there, exports the PDF there, then moves the
   PDF to `--out` with Python (which isn't sandboxed). So the powerbox never
   appears no matter where your files live or whether PowerPoint is already open,
   **without Full Disk Access**. (Optional: if you *manually* drive Office against
   arbitrary paths outside this script, granting the Office apps Full Disk Access
   avoids the powerbox there too — but this script doesn't need it.)

## Gotchas (each one cost real debugging — they're baked into the script)

| Symptom | Cause | Fix (in script) |
|---|---|---|
| `Message not understood` / "Grant File Access" dialog | Office **sandbox** can't read the file's folder | Shouldn't occur: the script **always** stages through `~/Downloads`. If you see it during *manual* Office use outside the script, give the app **Full Disk Access** or keep files in Downloads/Documents/Desktop. |
| `AppleEvent timed out (-1712)` | PDF export slower than the default Apple-event timeout | Wrap the save in `with timeout of 600 seconds` (script does this). |
| Word: `active document doesn't understand the "save as" message (-1708)` | Word's AppleScript `save as` is broken on several builds | Use **`docx2pdf`** for `.docx` (it uses a path that works), not raw `save as`. |
| `not allowed to send Apple events` | **Automation** permission not granted | Approve the first-run prompt / enable it in the Automation pane (≠ Full Disk Access on the terminal). |
| uv aborts: `No 'project' table found in …/pyproject.toml` | `uv run` adopted a stray `pyproject.toml` in the CWD/parent (tool-only repo, no `[project]` table) | Pass **`--no-project`** (see Usage) — build the env from `--with`, ignore the surrounding project. |
| Grid/table renders as a vertical list; wrong font | You used **LibreOffice** | Use this skill (real Office). LibreOffice ≠ faithful for complex layouts. |

## How it works (reference)

- **`.docx` → PDF:** `docx2pdf` (drives real Word). Raw AppleScript `save as` is unreliable per the table above.
- **`.pptx` → PDF:** `osascript`: `save active presentation in (POSIX file PDF) as save as PDF` inside `with timeout`.
- **`.xlsx` → PDF:** `osascript`: `save active workbook in PDF as PDF file format` (best-effort; spreadsheets paginate awkwardly — set print area in the file for clean output).
- **PDF → images:** `pdftoppm -jpeg -r 150` (poppler).

The script copies the input into `~/Downloads/.office-render`, quits the target
app for a clean state, converts **there** (so the sandbox never prompts), then
moves the PDF to `--out` and renders it. If the convert fails it reports the
exact fix (usually a missing Automation permission).
