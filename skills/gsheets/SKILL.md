---
name: gsheets
description: Read, write, update, delete cells in a Google Sheet; create / rename / duplicate / delete worksheet tabs; style headers with bold + colored backgrounds; freeze rows or columns; set column widths and row heights; add basic filters and sort ranges; apply alternating-row banding (zebra stripes), conditional formatting, borders, and number formats; or push a CSV file into an existing Sheet. Use when the user asks to push data into a Google Sheet, sync a CSV / DataFrame / table to a Sheet, format or style a Sheet (header colors, filters, freeze, banding), add or rearrange tabs / worksheets, build a stakeholder review or dashboard Sheet, or do anything Sheets-API-shaped that the gdoc-sync skill does for Docs.
allowed-tools: Read, Write, Bash, Edit, Glob, Grep
---

# gsheets

A single-file Python CLI (`scripts/gsheets.py`) over the **Google Sheets API v4** covering data, tabs, structure, styling, filters/sort, and a raw-batchUpdate escape hatch. Sibling of [gdoc-sync](../gdoc-sync/SKILL.md) — same auth model, same retry semantics, different surface.

The script has one external dep beyond Python stdlib: `pip install google-auth` for service-account auth (recommended). Without it you can still use gcloud ADC, or install `cryptography` and the script will mint JWTs itself.

## Quick start

```bash
# One-time: share the target Sheet with your service account as Editor.
# Then:
scripts/gsheets.py info <SPREADSHEET_ID> --sa-key ~/sa.json
scripts/gsheets.py write <SPREADSHEET_ID> --range "Sheet1!A1" \
  --values-json '[["name","status"],["alpha","ok"],["beta","fail"]]' \
  --sa-key ~/sa.json
scripts/gsheets.py format-header <SPREADSHEET_ID> --tab Sheet1 \
  --bg "#1a73e8" --fg "#ffffff" --filter \
  --sa-key ~/sa.json
```

`SPREADSHEET_ID` is the long token in the URL: `https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit`.

Skip `--sa-key` to fall back to `gcloud auth application-default print-access-token` (needs prior `gcloud auth application-default login --scopes=...spreadsheets,...drive`). Service-account auth is more reliable — see [reference/auth-setup.md](reference/auth-setup.md).

## Conceptual model

A Google Sheets file is a **spreadsheet**. It contains one or more **sheets** (aka tabs or worksheets). Each sheet is a grid of cells. Three IDs / names matter:

| Identifier | Where from | Used by |
|---|---|---|
| **spreadsheetId** | URL: `/spreadsheets/d/<ID>/edit` | Every subcommand (first positional arg) |
| **sheet title** (e.g. `"Sheet1"`, `"Review"`) | What you see on the tab strip | A1-notation ranges (`"Review!A1:C10"`); `--tab` flag |
| **sheetId** (integer) | `list-tabs` output | The raw `batchUpdate` API — but the CLI resolves titles for you, so you rarely need it directly |

**A1 notation vs GridRange**: the `values.*` endpoints (read/write/append/clear) take A1 strings. Everything else (formatting, structure, filters) takes a numeric `GridRange` — but the CLI lets you pass A1 + `--tab` and translates it internally.

## Operations

Each row shows when to use a subcommand and a one-line example. Run `scripts/gsheets.py <cmd> --help` for full flags.

### Data

| Subcommand | When | Example |
|---|---|---|
| `read` | Pull a range out as JSON | `gsheets read $ID --range "Sheet1!A1:C10"` |
| `write` | Overwrite a range with values | `gsheets write $ID --range "Sheet1!A1" --csv data.csv` |
| `append` | Add rows after the last data row | `gsheets append $ID --range "Sheet1!A:Z" --values-json '[[..]]'` |
| `clear` | Wipe cell values, keep formatting | `gsheets clear $ID --range "Sheet1!A2:Z"` |

`--values-json` accepts inline JSON 2D arrays OR `@file.json`. `--csv` reads a file. `--values-stdin` reads CSV from stdin (useful for pipes).

### Tabs

| Subcommand | Example |
|---|---|
| `list-tabs` | `gsheets list-tabs $ID` |
| `add-tab` | `gsheets add-tab $ID --title Review --color "#fbbc04"` |
| `delete-tab` | `gsheets delete-tab $ID --title Scratch` |
| `rename-tab` | `gsheets rename-tab $ID --from Sheet1 --to Q3Data` |
| `duplicate-tab` | `gsheets duplicate-tab $ID --from Template --to "Q3 (copy)"` |

### Structure

| Subcommand | Example |
|---|---|
| `freeze` | `gsheets freeze $ID --tab Q3Data --rows 1 --cols 1` |
| `resize-cols` | `gsheets resize-cols $ID --tab Q3Data --cols A:E --width 140` |
| `resize-cols --auto` | `gsheets resize-cols $ID --tab Q3Data --cols A:E --auto` |
| `resize-rows` | `gsheets resize-rows $ID --tab Q3Data --rows 1:1 --height 32` |
| `merge` / `unmerge` | `gsheets merge $ID --range "Q3Data!A1:C1"` |
| `insert-rows` / `delete-rows` | `gsheets insert-rows $ID --tab Q3Data --rows 5:7` |
| `insert-cols` / `delete-cols` | `gsheets delete-cols $ID --tab Q3Data --cols B:B` |

### Styling

| Subcommand | When | Example |
|---|---|---|
| `format-header` | Quick header styling (bold + color + freeze, optional filter) | `gsheets format-header $ID --tab Q3 --bg "#1a73e8" --fg "#fff" --filter` |
| `format` | Generic cell formatting (bg/fg/bold/italic/size/align/wrap/number) | `gsheets format $ID --range "Q3!E2:E" --number-format "0.00%%"` |
| `borders` | Add borders | `gsheets borders $ID --range "Q3!A1:E10" --all --color "#dadce0"` |
| `banding` | Alternating row colors (zebra stripes) | `gsheets banding $ID --range "Q3!A1:Z"` |
| `conditional-format` | Highlight cells matching a condition | `gsheets conditional-format $ID --range "Q3!E2:E" --condition NUMBER_GREATER --value 100 --bg "#fce8e6"` |

### Filter / sort

| Subcommand | Example |
|---|---|
| `add-filter` | `gsheets add-filter $ID --range "Q3!A1:Z"` |
| `clear-filter` | `gsheets clear-filter $ID --tab Q3` |
| `sort` | `gsheets sort $ID --range "Q3!A2:E" --by "B:desc,C:asc"` |

### Escape hatch

When the wrappers above don't cover something (charts, data validation, protected ranges, named ranges, pivot tables…), drop to raw Sheets `batchUpdate`:

```bash
gsheets batch-update $ID --requests @my-requests.json
```

`my-requests.json` is an array of [Request](https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/request) objects. See [reference/batch-update.md](reference/batch-update.md) for worked examples (data validation dropdown, protected range, chart, pivot).

## Best-practice recipes

### 1. "Make this Sheet look professional" — header + freeze + filter + autofit + banding

The cheap, atomic way: one batched call that you compose with the wrappers. All five effects below are pleasant defaults out of the box; you only pass a color if you want to override.

```bash
ID=1tRMIvLQM85UraW7eZF1gbdKp4bhPWXOuaaJ9xlDyf3c
TAB=Review

# 1. Write data
gsheets write   $ID --range "$TAB!A1" --csv data.csv
# 2. Header styling: bold white-on-blue + frozen row 1 + filter dropdowns
gsheets format-header $ID --tab "$TAB" --filter
# 3. Auto-fit columns to content
gsheets resize-cols $ID --tab "$TAB" --cols A:Z --auto
# 4. Alternating row colors below the header
gsheets banding $ID --range "$TAB!A1:Z"
```

### 2. CSV-driven review Sheet for stakeholders

This is the workflow the user's project script (`sync_fixtures_to_gsheet.py`) was inching toward — now first-class:

```bash
gsheets write $ID --range "Review!A1" --csv fixtures.csv --value-input-option USER_ENTERED
gsheets format-header $ID --tab Review --bg "#0b8043" --fg "#ffffff" --filter
gsheets resize-cols $ID --tab Review --cols A:Z --auto
gsheets conditional-format $ID --range "Review!D2:D" \
  --condition TEXT_EQ --value "fail" --bg "#fce8e6" --fg "#b71c1c"
gsheets conditional-format $ID --range "Review!D2:D" \
  --condition TEXT_EQ --value "pass" --bg "#e6f4ea" --fg "#137333"
```

Use `USER_ENTERED` (the default) so numbers, dates, and formulas parse like the user typed them in the UI. Use `RAW` only if you specifically want literal strings (e.g., to preserve a leading zero on phone numbers).

### 3. Multi-tab dashboard

```bash
gsheets add-tab    $ID --title "Summary" --index 0 --color "#1a73e8"
gsheets add-tab    $ID --title "Raw"     --index 1
gsheets add-tab    $ID --title "Notes"   --index 2 --color "#fbbc04"

gsheets write          $ID --range "Raw!A1"     --csv raw.csv
gsheets format-header  $ID --tab Raw            --filter
gsheets write          $ID --range "Summary!A1" --values-json '[["KPI","Value"],["MRR","=SUM(Raw!C:C)"]]'
gsheets format-header  $ID --tab Summary
gsheets freeze         $ID --tab Summary --rows 1 --cols 1
```

The `=SUM(Raw!C:C)` only works because `--value-input-option` defaults to `USER_ENTERED` — Sheets evaluates the formula.

### 4. Conditional formatting via the convenience flags vs raw rule JSON

Simple boolean rules use the convenience flags:

```bash
gsheets conditional-format $ID --range "Sales!E2:E" \
  --condition NUMBER_GREATER --value 10000 --bg "#fff8e1" --bold
```

For a gradient (color scale), use the escape hatch with a raw `gradientRule`:

```bash
cat > /tmp/heat.json <<'JSON'
[{
  "addConditionalFormatRule": {
    "index": 0,
    "rule": {
      "ranges": [{"sheetId": <SHEET_ID>, "startColumnIndex": 4, "endColumnIndex": 5, "startRowIndex": 1}],
      "gradientRule": {
        "minpoint": {"type": "MIN",         "colorStyle": {"rgbColor": {"red": 0.98, "green": 0.94, "blue": 0.94}}},
        "midpoint": {"type": "PERCENTILE", "value": "50", "colorStyle": {"rgbColor": {"red": 0.98, "green": 0.73, "blue": 0.41}}},
        "maxpoint": {"type": "MAX",         "colorStyle": {"rgbColor": {"red": 0.85, "green": 0.20, "blue": 0.20}}}
      }
    }
  }
}]
JSON
# look up the sheetId first
gsheets list-tabs $ID    # → copy the sheetId for "Sales", paste into the JSON
gsheets batch-update $ID --requests @/tmp/heat.json
```

### 5. Hebrew / RTL data

The script doesn't auto-apply RTL paragraph direction (Sheets handles bidirectional text per-cell). For a full RTL sheet, set the tab's right-to-left flag via the escape hatch:

```bash
gsheets batch-update $ID --requests '[{
  "updateSheetProperties": {
    "properties": {"sheetId": <SHEET_ID>, "rightToLeft": true},
    "fields": "rightToLeft"
  }
}]'
```

## Color cheatsheet

Sensible defaults for headers — all WCAG-AA contrast against white text:

| Vibe | Header bg | Header fg | Banding second-row |
|---|---|---|---|
| Google blue (default) | `#1a73e8` | `#ffffff` | `#f1f3f4` |
| Forest green | `#0b8043` | `#ffffff` | `#e6f4ea` |
| Warm amber | `#f9ab00` | `#202124` (dark) | `#fef7e0` |
| Deep slate | `#202124` | `#ffffff` | `#f8f9fa` |
| Muted teal | `#129eaf` | `#ffffff` | `#e0f7fa` |

If you change the header bg, sanity-check contrast at [webaim.org/resources/contrastchecker](https://webaim.org/resources/contrastchecker/). Stakeholder Sheets get printed and screenshotted — accessible colors matter.

## Auth

Two paths. Service account is recommended (same reasons as gdoc-sync — works in CI, no consent-screen friction, shareable). See [reference/auth-setup.md](reference/auth-setup.md) for full setup including the "this app is blocked" workaround and the org-policy-blocks-key-creation case.

## Gotchas

The full list lives in [reference/operations.md](reference/operations.md). The big ones:

- **`write` is destructive within its range.** It doesn't merge with existing data; it overwrites. To extend a table, use `append`.
- **`clear` keeps formatting; `delete-rows` deletes the row.** Choose based on whether you want the rows gone or just their values gone.
- **`values.*` writes do NOT trigger formatting updates.** Setting a header's background is a separate `format` / `format-header` call.
- **Per-batch atomicity.** Anything you do via `batch-update` (which all structure/styling commands use under the hood) is atomic — either every request commits or none do. Use this to your advantage: bundle several structural changes into one `batch-update` call to avoid partial-state races and to save quota.
- **Quota: 60 writes/user/minute, 300 writes/project/minute.** Each batched call counts as 1. The script auto-retries 429s with exponential backoff + jitter.
- **A1 column-only ranges (`A:Z`) include every row in the sheet** — fine for `clear` or `add-filter`, expensive for `format` (formats a million cells). Bound the rows when formatting.

## When NOT to use this skill

| Scenario | Use instead |
|---|---|
| Round-trip editing (Sheet → local CSV) | `read` covers the read direction; pair with your favorite CSV writer. |
| Real-time bidirectional sync | Build a proper integration (Apps Script trigger + webhook). One-shot scripts aren't the right shape. |
| Heavy data analysis on Sheet contents | Pull the data with `read`, analyze in pandas / DuckDB, write back results. Sheets is a UI, not a query engine. |
| Charts / pivots / data validation lists / protected ranges / named ranges | First-class wrappers not provided — use `batch-update` with raw JSON; see [reference/batch-update.md](reference/batch-update.md). |
| Sync a CSV to **Google Docs** | [gdoc-sync](../gdoc-sync/SKILL.md). |
| Sync a `.pptx` to Google Slides | [gslides-sync](../gslides-sync/SKILL.md). |

## Script layout

```
gsheets/
├── SKILL.md                  # this file
├── scripts/
│   ├── gsheets.py            # the CLI (single Python file)
│   └── README.md             # per-flag reference
└── reference/
    ├── auth-setup.md         # SA + gcloud setup, "this app is blocked" fix
    ├── operations.md         # per-operation gotchas + nuances
    └── batch-update.md       # raw batchUpdate cookbook (charts, validation, etc.)
```

## Dependencies

- **Python 3.9+** (stdlib only for HTTP via `urllib.request`)
- **Service-account auth** (recommended): `pip install google-auth`
  - Fallback: `pip install cryptography` — the script mints JWTs itself
- **gcloud ADC auth**: `gcloud` CLI on `$PATH`

## Related skills

- [gdoc-sync](../gdoc-sync/SKILL.md) — markdown → Google Doc.
- [gslides-sync](../gslides-sync/SKILL.md) — `.pptx` → Google Slides.

All three share the same auth model: service-account JSON shared as Editor on the target file, with gcloud ADC as a friction-heavy fallback.
