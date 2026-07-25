# office-render

Render a Microsoft Office file (`.docx` / `.pptx` / `.xlsx`) to PDF and then to page images using the **real** installed Office app on macOS — pixel-faithful, unlike LibreOffice, which substitutes fonts and re-flows complex tables and slide grids. One command produces page JPGs an agent can actually read.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

If you generate a `.docx` with python-docx or a `.pptx` with python-pptx, you have no idea what it looks like. The obvious check — `soffice --headless --convert-to pdf` — is worse than no check, because it renders *a* document rather than *your* document: LibreOffice substitutes fonts it doesn't have and re-flows layouts it can't reproduce. A 3-across team grid comes out as a vertical list, in a typeface nobody chose. You then "verify" a page the recipient will never see.

Word and PowerPoint produce the exact page. Driving them from a script, though, walks straight into four macOS-specific traps that each cost real debugging — all of them now handled inside the script:

- **The Office sandbox.** Office apps only freely read Downloads / Documents / Desktop. Opening a file anywhere else pops a "Grant File Access" powerbox that blocks an automated run forever. The usual advice is to grant Full Disk Access; this script instead **always stages through `~/Downloads`** — copies the input there, exports the PDF there, then moves it out with Python (which isn't sandboxed). The powerbox never appears, wherever your files live, and **no Full Disk Access is needed**.
- **`AppleEvent timed out (-1712)`** on any PDF export slower than the default timeout.
- **Word's AppleScript `save as` is broken** on several builds — `active document doesn't understand the "save as" message (-1708)`.
- **`uv run` adopting a stray `pyproject.toml`** from the CWD or a parent and aborting before the script runs.

## What it does

```
file.docx/.pptx/.xlsx ──▶ stage into ~/Downloads ──▶ real Word/PowerPoint/Excel
                                                              │
                                                              ▼
                                                          file.pdf
                                                              │
                                              pdftoppm -r 150 ─┘
                                                              ▼
                                        file-1.jpg, file-2.jpg, … (readable)
```

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install utilities@shaharsha-skills
```

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/office-render" ~/.claude/skills/office-render
```

## Requirements

- **macOS** with **Microsoft Office** installed (Word / PowerPoint / Excel, whichever you're rendering).
- `poppler` for `pdftoppm` (`brew install poppler`).
- `uv` (the invocation below builds an ephemeral env with `docx2pdf`).

### One-time setup — one permission, not two

**Automation** is the only permission required. System Settings → Privacy & Security → **Automation** → enable **Microsoft Word / PowerPoint / Excel** under your terminal or IDE (Terminal, iTerm, Ghostty, VS Code…). The first run also pops a prompt — approve it once.

**File access needs nothing.** The staging-through-Downloads trick above sidesteps the sandbox entirely, so Full Disk Access is *not* required. (If you separately drive Office by hand against arbitrary paths, granting the Office apps Full Disk Access avoids the powerbox there too — but this script doesn't need it.)

## Quick start

```bash
uv run --no-project --with docx2pdf python3 scripts/office_render.py \
    "/path/to/file.pptx" --out /tmp/render --dpi 150
```

It writes `file.pdf` plus `file-1.jpg`, `file-2.jpg`, … into `--out` and prints the paths. Then read the JPGs.

**`--no-project` is not cosmetic.** Without it, `uv run` tries to install the *surrounding* directory as a project; if the CWD or any parent holds a `pyproject.toml` with no `[project]` table — common in tool-only repos — it aborts with `No 'project' table found` before the script ever runs. It's harmless when there's no pyproject either, so always pass it.

## Flags

| Flag | Default | Description |
|---|---|---|
| `--out DIR` | — | Where the PDF and page images land |
| `--dpi N` | `150` | Rasterization DPI; 150 is plenty on screen |
| `--format png` | `jpeg` | Page-image format |
| `--pdf-only` | off | Skip rasterization |

## When to use it — and when not

Use it to preview or screenshot a Word doc, deck, or spreadsheet; to visually QA a `.docx`/`.pptx` you just generated; when a LibreOffice render looks wrong (substituted font, broken grid, flipped RTL); or to read a doc whose *layout* matters.

Skip it when you only need the **text** — `pandoc -t plain` or `python -m markitdown` is faster — or when you're not on macOS / Office isn't installed, in which case fall back to `soffice --headless --convert-to pdf` and accept the lower fidelity.

## Gotchas

| Symptom | Cause | Resolution |
|---|---|---|
| `Message not understood` / "Grant File Access" dialog | Office sandbox can't read the file's folder | Shouldn't occur — the script always stages through `~/Downloads`. If you hit it during *manual* Office use, grant that app Full Disk Access or keep files in Downloads/Documents/Desktop. |
| `AppleEvent timed out (-1712)` | PDF export slower than the default timeout | Wrapped in `with timeout of 600 seconds` (the script does this) |
| Word: `doesn't understand the "save as" message (-1708)` | Word's AppleScript `save as` is broken on several builds | Uses **`docx2pdf`** for `.docx`, which takes a path that works |
| `not allowed to send Apple events` | Automation permission not granted | Approve the first-run prompt, or enable it in the Automation pane (≠ Full Disk Access) |
| `No 'project' table found in …/pyproject.toml` | `uv run` adopted a stray pyproject | Pass **`--no-project`** |
| Grid renders as a vertical list; wrong font | You used LibreOffice | Use this skill |

One page often has trailing whitespace — crop to content before placing it elsewhere (PIL: alpha or near-white bbox).

## How it works

- **`.docx` → PDF:** `docx2pdf` (drives real Word).
- **`.pptx` → PDF:** `osascript`: `save active presentation in (POSIX file PDF) as save as PDF`, inside `with timeout`.
- **`.xlsx` → PDF:** `osascript`: `save active workbook in PDF as PDF file format` — best-effort; spreadsheets paginate awkwardly, so set a print area in the file for clean output.
- **PDF → images:** `pdftoppm -jpeg -r 150`.

The script copies the input into `~/Downloads/.office-render`, quits the target app for a clean state, converts there, then moves the PDF to `--out` and renders it. On failure it reports the exact fix — usually a missing Automation permission.

## Related skills

- [narrating-pptx](../narrating-pptx) — uses this for its "no repair dialog" validation pass.
- [deck-to-video](../deck-to-video) — consumes the PDF this produces, rasterized at 200 dpi.
- [self-presenting-decks](../self-presenting-decks) — the orchestration map both sit inside.

## License

MIT — see [LICENSE](../../LICENSE).
