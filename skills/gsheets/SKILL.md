---
name: gsheets
description: Read, find, write and format Google Sheets from the command line. Covers reading ranges as JSON or as header-keyed records, finding a row by its content, guarded compare-and-set edits on Sheets other people also edit, writing many ranges in one call, one-call table layout (header, number formats, freeze, filter, widths, banding), tabs, dropdowns, notes, conditional formatting, inspecting a tab's formatting, merges, validation and charts, renaming the spreadsheet, exporting PDF or PNG for a visual check, and raw batchUpdate with A1 ranges. Use when the user asks to read, update, append to, sync a CSV into, look someone up in, style, build a dashboard in, or check a Google Sheet, or when another skill says to use the gsheets skill.
---

# gsheets

`scripts/gsheets.py` is a single-file CLI over the Google Sheets API v4. It runs on a bare `python3` with no packages installed, and it finds the service-account key by itself.

## Quick start

Define a shell **function**, not a variable: zsh doesn't word-split `$G`, so `G="python3 …"; $G read …` fails with "no such file or directory". An agent's Bash calls each start a fresh shell, so define the function in the same command as the calls that use it, or call `python3 …/gsheets.py` directly.

```bash
gsheets() { python3 ~/.claude/skills/gsheets/scripts/gsheets.py "$@"; }

gsheets info  <ID>                                  # title, owner, last editor, tabs
gsheets read  <ID> "Tab!A1:H40"                     # bare JSON 2D array
gsheets write <ID> "Tab!B7" --values-json '[["new value"]]'
```

`<ID>` is the token in `https://docs.google.com/spreadsheets/d/<ID>/edit`. A range is A1 notation, either positional or `--range`. Quote tab names that have spaces: `"'My Tab'!A1:C10"`.

**Auth, first match wins:** `--sa-key PATH`, then `$GOOGLE_SA_KEY`, then `~/.config/gdoc-sync/sa-key.json`, then gcloud ADC. Without google-auth installed, the script signs the token with `cryptography` or the `openssl` CLI. `--sa-key` and `--dry-run` work before or after the subcommand. The file must be shared with the service account's email (`client_email` in the key): Editor to write, Viewer to read. Setup is in [reference/auth-setup.md](reference/auth-setup.md).

**Output contract:**
- Data commands print JSON on stdout. Status lines start with `✓`.
- On error, stdout is empty, the API's message and a `hint:` go to stderr, and the exit code is non-zero: 2 for usage, 3 when `--expect` refuses, 4 when `--verify` finds a problem.
- Check the exit code before you parse stdout. An empty `[]` is a valid read of an empty range.

## What `read` prints

| Call | Output |
|---|---|
| `read ID "Tab!A1:C3"` | `[["a","b","c"],["d"]]`, a bare 2D array |
| several ranges, or `--range` repeated | `{"Tab!A1:C3": [[…]], "Other!A1": [[…]]}`, keyed by the range you passed |
| `--all-tabs` | `{"Tab1": [[…]], "Tab2": [[…]]}` |
| `--header-rows 2` | `[{"_row": 3, "AWS / Account": "x", …}, …]`. These are records keyed by the header path; merged header cells are filled, and `_row` is the sheet row number |
| `--numbered` | `[{"_row": 1, "values": [...]}, …]` |

What the API does to the raw data:
- It trims trailing empty cells and trailing empty rows, so rows are ragged and an empty row is `[]`. `--pad` makes the grid rectangular, out to the range you asked for.
- A merged cell's value comes back only in its top-left cell. `--fill-merged` copies it into every cell the merge covers.
- By default you get the values shown in the UI (`"$1,000.00"`, `"50%"`). Use `--render unformatted` for raw numbers and `--render formula` for formula text.

## Editing a Sheet other people also edit

Find the cell by its content, read it, then write with a compare-and-set guard:

```bash
gsheets find  <ID> --tab Access --col A --value "Dana Levi" --header-rows 2 --show "AWS"
#  → [{"row": 8, "a1": "'Access'!A8", "value": "Dana Levi", "header": "Person / Name",
#      "cells": [{"header": "AWS / prod 4719…", "a1": "'Access'!N8", "value": "..."}, …]}]
gsheets read  <ID> "'Access'!N8" > /tmp/before.json
gsheets write <ID> "'Access'!N8" --values-json '[["AWSPowerUserAccess"]]' --expect @/tmp/before.json
#  exit 3 + a cell-by-cell diff on stderr if someone changed N8 since the read
```

- `find` takes exactly one of `--value` (exact match), `--contains` (case-insensitive) or `--regex`.
  - Choose where it searches with `--col A,C` or `--col-header "AWS / prod"` (by header text), and limit the range with `--within A1:BZ500`.
  - Choose what it returns with `--show TEXT`: the A1 address and value of each of the row's cells whose header contains TEXT. `--record` returns the whole row.
  - `a1`, `value` and `header` describe the first cell that matched.
- To answer "who has X in column Y", use `find --contains X --col-header Y --header-rows 2`. `headers <ID> --tab Access --header-rows 2` maps column letters to header paths.
- When `find --value` returns more than one row (two "GitHub" rows with different scopes), tell them apart by another column before you write.
- `--expect` accepts exactly what `read` printed. The guard covers every cell the write touches. Cells the write covers but the snapshot doesn't are expected to be empty, so read the same range you are about to write. Keep both narrow, just the cells you change, so that volatile cells such as GOOGLEFINANCE don't raise false alarms.
- `batch-write <ID> --data '{"Tab!B7": [["x"]], "Log!A90:C90": [["2026-11-06","grant","AWS"]]}' --expect @snapshot.json` writes many ranges in one call, with the same guard. A snapshot is `read` run on those ranges.
- `null` in the values leaves a cell untouched; `""` clears it. `--skip-empty` turns every `""` into `null`. Use it when writing a row across an `ARRAYFORMULA` column: writing `""` over that column breaks the formula.
- `info` shows `lastModifyingUser`, and `revisions` lists who edited and when. Neither can show what changed, so diff against your own snapshot.
- The guard re-reads just before writing. That leaves a window of about a second, so it is a guard, not a lock.

## Values: USER_ENTERED vs RAW

`write`, `append` and `batch-write` default to `--value-input-option USER_ENTERED`, which parses input as if typed into the UI:
- `"=SUM(A:A)"` becomes a formula, `"2026-11-01"` becomes a date, and `"1,000"` becomes 1000.
- `"074920"` becomes 74920, which loses the leading zero, and a 12-digit account ID becomes a number. Digit strings longer than 15 digits stay text.

| Data | Use |
|---|---|
| IDs, account numbers, SHAs, phone numbers, status text | `--value-input-option RAW` (JSON numbers still land as numbers) |
| Formulas and IDs in the same write | USER_ENTERED, with a leading `'` on each ID: `"'022671037545"` |
| Money and percentages | Write full precision and round with a number format. Rounded inputs make a formula total differ from the source by a cent |

`--verify` reads the cells back after writing. It exits 4 on dropped leading zeros, IDs turned into numbers, or formula errors (`#REF!`, `#NAME?`).

## Commands

Run `gsheets <command> --help` for the flags. Every write command accepts `--dry-run`, which prints the request body it would send and stops. The `--expect` check still runs live first, so a dry run also tells you whether the guard would pass.

| Group | Commands |
|---|---|
| Data | `read` · `find` · `headers` · `write` · `batch-write` · `append` · `clear [--formats \| --all]` |
| Tabs | `list-tabs` · `add-tab [--index --color --sheet-id --rtl]` · `delete-tab` · `rename-tab` · `duplicate-tab` · `move-tab --index` · `set-title` (renames the spreadsheet file) |
| Structure | `freeze` · `resize-cols (--width \| --widths 40,180,90 \| --auto)` · `resize-rows` · `merge` · `unmerge` · `insert-rows/cols [--inherit before\|after]` · `delete-rows/cols` |
| Styling | `format RANGE…` (several ranges in one call) · `format-header [--row N] [--filter]` · `borders` · `banding` · `conditional-format` · `validation` · `note` · `copy-format --from --to [--what format\|validation\|conditional]` |
| Layout | `table`: write a table and lay it out in one atomic batch (below) |
| Inspect | `info` · `inspect --tab [--cells A1:H40]` · `revisions` · `export --format pdf\|png\|csv\|xlsx` |
| Escape | `batch-update --requests @file.json`: raw requests, with A1 strings allowed (below) |

Examples of the less obvious ones:

```bash
gsheets validation <ID> "Jobs!E2:E" --one-of "Open,Applied,Interview,Rejected"
gsheets validation <ID> "Access!D3:D" --one-of-range "=Roles!\$A\$2:\$A\$30"
gsheets validation <ID> "Tasks!F2:F" --checkbox
gsheets note       <ID> "Access!D1" --text "Source: admin export, 2026-10-22"
gsheets format     <ID> "Sales!D2:D" "Sales!F2:F" --number-format '"$"#,##0.00'
gsheets format     <ID> "Sales!G2:G" --number-format "0.0%"        # one %, not %%
gsheets conditional-format <ID> "Jobs!B2:B" --condition TEXT_STARTS_WITH --value P1 --bg "#fce8e6"
gsheets export     <ID> --tab Summary --format png --out /tmp/summary.png   # look at it
```

## One-call table layout

`table` replaces about ten calls per tab, all in one atomic `batchUpdate`. It writes the values, styles the header, freezes it, applies number formats per column, sets widths, wrap, filter and banding. `--replace` first resets the tab: values, formats, notes, validation, merges, banding, conditional formats and the filter.

```bash
gsheets table <ID> --tab Payments --create --replace --values-json @payments.json \
  --col-format "D:E=#,##0.00" --col-format "F=yyyy-mm-dd" --col-format "A=TEXT" \
  --widths 120,90,200,100,100,95 --filter --banding --wrap
```

Values from JSON are written typed, in the same atomic batch: numbers stay numbers, `"=…"` is a formula, every other string is literal, and leading zeros survive. `--input user-entered` (the default for `--csv`) parses them like typing instead. That mode can't be atomic, so it runs in a safe order: grow the grid and reset formatting, write the values, lay out, then clear old values outside the new table. A failure part-way never leaves the tab empty. The grid grows to fit the table. It starts at `--at` (default A1), and freezing through the header is the default when it starts on row 1.

## Raw batch-update with A1 ranges

```bash
gsheets batch-update <ID> --requests '[
  {"repeatCell": {"range": "Summary!A12:E12",
                  "cell": {"userEnteredFormat": {"textFormat": {"bold": true}, "backgroundColor": "#f1f3f4"}},
                  "fields": "userEnteredFormat(textFormat.bold,backgroundColor)"}},
  {"updateBorders": {"range": "Summary!A12:E12", "top": {"style": "SOLID", "color": "#5f6368"}}},
  {"insertDimension": {"range": "Access!12:13", "inheritFromBefore": true}}
]'
```

The CLI translates these before sending:
- `"range": "Tab!A1:C3"` becomes a GridRange. Inside dimension requests, `"Tab!3:5"` or `"Tab!A:C"` becomes a DimensionRange.
- `"ranges": [...]` strings become GridRanges, and `"sheetId": "Tab"` becomes the numeric id.
- Any `*Color` or `*ColorStyle` given as `"#hex"` becomes RGB.

It prints a one-line summary plus the replies that carry data; add `--full` for the raw response. To merge several wrapper calls into one atomic batch, run each with `--dry-run`, concatenate the `requests` arrays, and send them with `batch-update`. Cookbook for charts, validation, protected ranges, pivots and Tables: [reference/batch-update.md](reference/batch-update.md).

## Recipes

**Extend a styled block** (for example, add columns or rows to the Access matrix):
1. Run `inspect --tab Access --cells A1:AH5`. It lists merges, conditional-format rules with their ranges, validation, number formats, column widths, column groups and notes, with colors as hex.
2. Insert rows or columns *inside* the block, not at its edge (see Gotchas).
3. Copy the look across with `copy-format --from "Access!E1:E40" --to "Access!F1:F40"`. On a header with partial merges, copy the merged top-left cell on its own, then `merge` again.

**Rules that keep covering new rows:** give conditional formats, validation and filters an open-ended range such as `B2:B` (no end row), not `B2:B14`. Sheets stores it as running to the grid's last row (`B2:B1000`), so rows you fill in later are covered. A bounded rule stops at its last row, and re-adding it every time the table grows piles up duplicate rules. Rows appended past the end of the grid still fall outside, so insert inside the range instead (see Gotchas).

**Header that is not on row 1:** `format-header --tab Summary --row 4` styles row 4 and freezes rows 1-4. Pass `--no-freeze` to skip the freeze.

**Hebrew / RTL tab:** `add-tab --title "דוח" --rtl`. For an existing tab, use `batch-update` with `updateSheetProperties` `{"sheetId": "Tab", "rightToLeft": true}` and `"fields": "rightToLeft"`.

## Gotchas

- **Inserting at the edge of a range doesn't extend it.** Rows inserted right below the last data row, or above the first, land outside every `SUM`/`SUMIF` range, chart source, conditional-format rule and validation range. Insert *before* the last data row, strictly inside the range, then move the values.
- **`write` overwrites only where your values land.** It never clears cells outside the payload, and it doesn't touch formatting. `clear` keeps formatting too: old number formats stay on columns whose meaning changed. Use `clear --formats`, or `table --replace`.
- **`write`'s "API counted N cells in M rows"** counts only non-empty values, so it is lower than the payload's size when there are blank cells or empty rows. That is not an error; use `--verify` to check the result.
- **`append` finds "the table" itself.** Point the range at the block you mean, for example `"Log!A:H"`, and check the printed `table detected at` range. For exact row numbers, `read` to find the last row and `write` an explicit range instead.
- **Each `conditional-format` call adds another rule,** and `banding` fails on a range that already has banding. List the existing ones with `inspect`; `table --replace` deletes them.
- **An empty checkbox reads as `FALSE`.** `validation --checkbox` on an open-ended column makes every grid row look filled, which affects `read`, `append` and table detection. Bound checkbox ranges to the data rows.
- **`resize-cols --auto` sizes to the widest cell,** including long note rows. Use `--widths` for tabs with prose rows.
- **Quota: 60 reads and 60 writes per minute per user**, and 300 per project. A service account counts as one user, so parallel agents sharing it share 60/min. The script retries 429s with backoff. Use `batch-write`, several `--range` values, or `table` to make fewer calls. Don't fan out ten agents that each read the same Sheet.
- **A1 ranges with no row bounds (`A:Z`) span every row:** fine for `clear` or `add-filter`, heavy for `format`.

## Using it as a library

```python
import os, sys
sys.path.insert(0, os.path.expanduser("~/.claude/skills/gsheets/scripts"))
import gsheets as g
tok = g.get_token()                                  # same key resolution as the CLI
rows = g.fetch_values(tok, ID, ["Tab!A1:C10"])[0][1]   # [(api_range, values)]
g.batch_update(tok, ID, [{"addSheet": {"properties": {"title": "New"}}}])
g.api(tok, "GET", f"{g.SHEETS_BASE}/{ID}?fields=sheets.properties")  # api(token, method, url, body=None)
```

`api()` refuses a URL that isn't `https://…`. If you pass the arguments in the wrong order, it fails without echoing the token.

## When NOT to use

| Scenario | Use instead |
|---|---|
| Push markdown into a Google Doc | [gdoc-sync](../gdoc-sync/SKILL.md) |
| Push a `.pptx` into Google Slides | [gslides-sync](../gslides-sync/SKILL.md) |
| Heavy analysis of Sheet data | `read` it, then use pandas or DuckDB, then write back the results |
| Real-time two-way sync | An Apps Script trigger plus a webhook; one-shot CLI calls are the wrong shape |
| Create a brand-new spreadsheet | Create it in the UI and share it with the service account, which cannot create files |

## Files

```
gsheets/
├── SKILL.md                 # this file
├── scripts/gsheets.py       # the CLI (stdlib only; google-auth used when present)
├── scripts/README.md        # flag reference by command
└── reference/
    ├── auth-setup.md        # service account, API enablement, sharing, ADC fallback
    ├── operations.md        # per-command details and edge cases
    └── batch-update.md      # raw request cookbook
```

Related: [gdoc-sync](../gdoc-sync/SKILL.md) and [gslides-sync](../gslides-sync/SKILL.md) use the same service account and key path.
