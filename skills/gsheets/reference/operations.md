# Operations: details + gotchas

Per-subcommand nuances and the edge cases that bite. SKILL.md has the happy-path summaries; this file is for the "wait, why isn't this working" moments.

## Data: `read` / `write` / `append` / `clear`

### `read`

Uses `spreadsheets.values.get`. Returns a 2D array printed as JSON.

| Flag | Default | Notes |
|---|---|---|
| `--value-render` | `FORMATTED_VALUE` | What you see in the UI. Use `UNFORMATTED_VALUE` for raw numbers (e.g., 0.5 instead of "50%") or `FORMULA` to read the formula text instead of the computed value. |
| `--major-dimension` | `ROWS` | Set to `COLUMNS` to transpose the response — rare. |

The response **trims trailing empty cells**. `read --range "Sheet1!A1:E1"` returns `[["a","b","c"]]` if D and E are empty, NOT `[["a","b","c","",""]]`. Pad in caller code if you need rectangular shape.

### `write`

Uses `spreadsheets.values.update` (PUT).

| Flag | Default | Notes |
|---|---|---|
| `--value-input-option` | `USER_ENTERED` | The Sheet parses formulas, dates, currencies — what a human typing would get. `RAW` inserts literal strings (preserves leading zeros, `=1+2` stays as the string "=1+2"). |

**Destructive within the range.** If you write `[["a"], ["b"]]` to `A1`, A1 becomes "a" and A2 becomes "b" — A3 is untouched, but anything that was in A1/A2 is gone.

**The range tells Sheets where to start, not where to stop.** If you write 100 rows but pass `--range "Sheet1!A1:A10"`, only the first 10 rows of your values land. To force all 100, write to `A1` (no end bound) or `A1:A`.

**Empty cells in the values array stay empty (write `""` to clear) or get skipped.** Use `null` in your JSON to skip a cell entirely; use `""` to clear it.

### `append`

Uses `spreadsheets.values.append` (POST). Looks for the "table" in the range and adds rows after the last non-empty row.

| Flag | Default | Notes |
|---|---|---|
| `--insert-data-option` | `INSERT_ROWS` | Adds new rows. Use `OVERWRITE` to write into existing rows below the table (rarely what you want — destructive). |

The range should encompass the table's columns: `"Sheet1!A:Z"` (whole sheet by column) or `"Sheet1!A1:Z"` (start row 1, all rows below).

### `clear`

Uses `spreadsheets.values.clear`. **Clears values only — keeps cell formatting, number formats, conditional rules.** To remove the rows themselves use `delete-rows`.

## Tabs

### `add-tab`

`--rows` / `--cols` set the *initial* dimensions; the sheet grows automatically as data is written past them. Default is 1000 × 26 (the same defaults the UI uses for new tabs).

`--color "#hex"` sets the tab strip color (the colored bar under the tab name).

### `delete-tab`

Resolves `--title` → numeric sheetId by listing tabs first (one extra GET, cached for the process). If you pass an unknown title, the script lists available titles in the error.

You can't delete the last tab. Sheets requires at least one. Add a new one first, then delete.

### `rename-tab` / `duplicate-tab`

`duplicate-tab` copies the source tab's content + formatting into a new tab. `--index` controls where the copy lands (0 = first). Useful for templated dashboards: keep a hidden `_template` tab and `duplicate-tab` each month.

## Structure

### `freeze`

Sets `gridProperties.frozenRowCount` and/or `frozenColumnCount`. `--rows 0` unfreezes. **Frozen rows stay visible when you scroll** — the classic use is `--rows 1` to pin the header.

### `resize-cols` / `resize-rows`

Two modes:

- `--width N` / `--height N` — explicit pixel size. Sheets' default column width is 100px. Comfortable text columns: 140-180px. Number columns: 80-100px.
- `--auto` — autoresize to content. Most useful right after writing data. The API is `autoResizeDimensions`; it computes the width needed to display the widest cell in each column at the current font.

Auto-resize is per-column-independently — autosizing `A:E` may set each column to a different width.

### `merge` / `unmerge`

`--merge-type MERGE_ALL` (default) collapses the range into one big cell. `MERGE_COLUMNS` merges each column independently (gives you horizontal bands of merged cells, one per column). `MERGE_ROWS` is the row-wise version.

**The merged cell takes its value from the top-left of the original range.** Other values in the merged range are discarded. Unmerging restores the cells but NOT their original values.

### `insert-rows` / `delete-rows` / `insert-cols` / `delete-cols`

Half-open ranges in row/col numbers (1-indexed). `--rows 5:7` inserts/deletes rows 5 through 7 (inclusive); 3 rows total. `--rows 5` is a single row.

Insert is *before* the start index. `--rows 5:7` shifts existing rows 5+ downward by 3.

## Styling

### `format`

Generic cell formatting. Pass any combination of `--bg`, `--fg`, `--bold`, `--italic`, `--font-size`, `--font`, `--align`, `--valign`, `--wrap`, `--number-format`.

The `--fields` mask is built dynamically — only the properties you set are sent to the API. This means `format` is **non-destructive to other formatting**. If you only pass `--bg`, the existing text formatting (bold, size, etc.) stays.

`--number-format` patterns:

| Pattern | Renders | Use for |
|---|---|---|
| `0.00` | 1234.5 → `1234.50` | Plain decimals |
| `#,##0.00` | 1234.5 → `1,234.50` | Thousands separator |
| `0.00%` | 0.5 → `50.00%` | Percentages (input must be the fraction, not 50) |
| `$#,##0.00` | 1234.5 → `$1,234.50` | USD |
| `[$€-2] #,##0.00` | 1234.5 → `€ 1,234.50` | EUR (locale-aware) |
| `yyyy-mm-dd` | date → `2026-05-26` | ISO dates |
| `mmm d, yyyy` | date → `May 26, 2026` | Human dates |

In Bash, escape the percent if you used `--number-format "0.00%"`: it's not Bash-special, just a heads-up that argparse needs `%%` in its own help string (not in CLI input).

### `format-header`

Convenience wrapper that bundles:

1. Bold + colored row 1 (via `repeatCell`)
2. Freeze row 1 (via `updateSheetProperties.gridProperties.frozenRowCount = 1`)
3. (Optional) `--filter` adds a basic filter on row 1 (dropdown arrows)

All three in one atomic `batchUpdate` call (1 API call against quota, not 3).

Defaults: blue `#1a73e8` background + white text. Pass `--bg` / `--fg` to override.

**Re-running is idempotent.** Re-formatting an already-styled header is a no-op; you can call this in a script without checking state.

### `borders`

`--all` shorthand sets every side + inner. Otherwise pick individual sides: `--top --bottom --left --right --inner`.

`--style`:
- `SOLID` (default) — 1px
- `SOLID_MEDIUM` — 2px
- `SOLID_THICK` — 3px
- `DOTTED` / `DASHED` / `DOUBLE` — visual variants
- `NONE` — removes borders

Color defaults to black; override with `--color "#hex"`. For subtle table grids, use a light gray like `#dadce0` (Google Material's outline color).

### `banding`

Adds zebra-striped alternating rows via `addBanding`. Defaults are tasteful: blue header (`#1a73e8`), white first band, light-gray second band (`#f1f3f4`).

**The range should start at row 1 (the header)** if you want a styled header band — otherwise the first row of your range becomes the "first band" instead of the header.

**Banding and `format-header` aren't a great combination.** Banding's header color overrides whatever `format-header` set. If you want both, use ONLY banding (it includes a header band) OR ONLY `format-header` (no zebra).

### `conditional-format`

Two ways to use it:

**Convenience flags** for boolean rules:

```bash
gsheets conditional-format $ID --range "Sales!E2:E" \
  --condition NUMBER_GREATER --value 10000 \
  --bg "#fff8e1" --fg "#5f6368" --bold
```

Supported condition types (a subset — see [the Sheets API ConditionType enum](https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/other#ConditionType) for the full list):

| Condition | Takes `--value`? | Matches when |
|---|---|---|
| `NUMBER_GREATER` | Yes | Cell > value |
| `NUMBER_GREATER_THAN_EQ` | Yes | Cell ≥ value |
| `NUMBER_LESS` | Yes | Cell < value |
| `NUMBER_LESS_THAN_EQ` | Yes | Cell ≤ value |
| `NUMBER_EQ` | Yes | Cell = value |
| `NUMBER_NOT_EQ` | Yes | Cell ≠ value |
| `NUMBER_BETWEEN` | (pair via raw rule) | Cell in [min, max] — use `--rule` |
| `TEXT_CONTAINS` | Yes | Substring match |
| `TEXT_NOT_CONTAINS` | Yes | No substring match |
| `TEXT_STARTS_WITH` | Yes | Prefix |
| `TEXT_ENDS_WITH` | Yes | Suffix |
| `TEXT_EQ` | Yes | Exact text |
| `DATE_BEFORE` | Yes (`"2026-01-01"`) | Date older |
| `DATE_AFTER` | Yes | Date newer |
| `BLANK` | No | Empty cell |
| `NOT_BLANK` | No | Any non-empty cell |
| `CUSTOM_FORMULA` | Yes (`"=A2>B2"`) | Formula evaluates truthy |

**Raw rule JSON** for anything else (color scales / gradients, multiple ranges, complex compound formats):

```bash
gsheets conditional-format $ID --range "..." --rule @rule.json
```

Where `rule.json` is a complete [ConditionalFormatRule](https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/conditional#ConditionalFormatRule). The `--range` flag is still required (used to derive sheetId) but the rule's own `ranges` take precedence if present.

## Filter / sort

### `add-filter`

Adds a basic filter on a range — dropdown arrows on the header row.

**A sheet can have only ONE basic filter at a time.** `add-filter` replaces any existing filter without warning. Use `clear-filter` first if you need to know that it existed.

For filter views (multiple saved filter configs that don't affect other viewers), drop to the escape hatch: `addFilterView` request.

### `clear-filter`

Removes the basic filter from a tab. No-op if no filter exists (Sheets returns success).

### `sort`

Sorts a range in-place. `--by` is a comma-separated list:

```bash
--by "B:desc"           # one column, desc
--by "B:desc,C:asc"     # two columns, primary then secondary
--by "B"                # default order: ascending
```

**The range must not include your header row** if the header has different formatting — sorting reorders the header, which is rarely what you want. Use `Sheet1!A2:Z` (skip row 1) for header-less sort.

## Escape hatch: `batch-update`

When the wrappers don't cover something, drop to raw [Request](https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/request) objects. See [batch-update.md](batch-update.md) for a cookbook.

```bash
gsheets batch-update $ID --requests @file.json
gsheets batch-update $ID --requests '[{"unmergeCells":{"range":{"sheetId":0}}}]'
```

Both `[{...}]` and `{"requests":[{...}]}` are accepted on input.

## Cross-cutting

### Atomicity

Every wrapper that uses `batchUpdate` (everything except the four `values.*` data operations) is **atomic**: all requests in a single CLI call commit together or none commit. Use this for related multi-step changes — bundle into one `batch-update` call instead of N separate CLI invocations.

### Quota

Sheets API limits: **60 writes/user/minute, 300 writes/project/minute**. Each `batchUpdate` call counts as 1, regardless of how many requests it contains. The script auto-retries 429s with truncated exponential backoff + jitter (up to ~32s, 5 attempts).

If you're sustaining bulk writes, batch them: 100 small updates → 1 `values.batchUpdate` call instead of 100 `values.update` calls.

### Idempotency

Most operations are idempotent on the second call:

| Operation | Idempotent? |
|---|---|
| `format`, `format-header`, `borders` | Yes — re-applies the same formatting |
| `freeze`, `resize-cols`, `resize-rows` | Yes |
| `add-tab` with existing title | No — API rejects with "duplicate name" |
| `delete-tab` with already-deleted title | No — script errors with "tab not found" |
| `add-filter` | Yes (last call wins, but state ends up the same) |
| `merge` on already-merged range | Yes |
| `conditional-format` | NO — each call adds a NEW rule. Track manually or delete old rules first via raw `deleteConditionalFormatRule`. |
| `banding` on a range with existing banding | NO — rejects with "overlapping band ranges". Delete old bandings first or pick a non-overlapping range. |

The non-idempotent cases are the main footguns. For dashboard automation that runs nightly, prefer destructive-and-recreate (delete-tab + add-tab) over additive-and-hope (which leaves stale rules accumulating).

### Things this CLI does NOT do

These exist in the API but aren't first-class subcommands. Use `batch-update`:

- Charts (`addChart` / `updateChartSpec`)
- Data validation rules / dropdowns (`setDataValidation`)
- Protected ranges (`addProtectedRange`)
- Named ranges (`addNamedRange`)
- Pivot tables (live inside `updateCells` requests)
- Filter views (`addFilterView`)
- Developer metadata
- Per-cell hyperlink / note assignment (use values.update with `userEnteredValue.formulaValue = "=HYPERLINK(...)"`)
- Conditional format DELETION (use `deleteConditionalFormatRule` with the rule's index)
- Color schemes / themes

See [batch-update.md](batch-update.md) for templates of the common ones.
