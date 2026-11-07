# Operations: details + gotchas

Per-command nuances and the edge cases that bite. SKILL.md has the happy path; this file is for "wait, why isn't this working".

## Data

### `read`

`spreadsheets.values.get` for one range, `values:batchGet` for several (one API call).

| Flag | Default | Notes |
|---|---|---|
| `RANGE…` / `--range` (repeatable) | — | One range prints a bare 2D array; several print an object keyed by the range strings you passed |
| `--all-tabs` | off | Every tab in one call, keyed by tab title |
| `--render` | `formatted` | `formatted` = what the UI shows (`"$1,000.00"`, `"50%"`), `unformatted` = raw numbers (`1000`, `0.5`), `formula` = formula text for formula cells |
| `--pad` | off | Pads every row to the range's width (when the range names its columns) or the longest row; pads rows out to a bounded range's height |
| `--fill-merged` | off | Copies a merge's value into every cell it covers (the API returns it only in the top-left cell) |
| `--header-rows N` | 0 | Records keyed by the header path (`"AWS / prod 4719…"`), with merged header cells filled, `"\n"` in headers flattened, duplicate names suffixed with the column letter, `_row` = sheet row number, empty rows dropped |
| `--numbered` | off | `[{"_row": 7, "values": [...]}]` |

The response **trims trailing empty cells and rows**: `A1:E1` with D and E empty returns `[["a","b","c"]]`, and an empty row in the middle is `[]`. An empty range returns `[]`, which you can't tell apart from a range that missed its target. Check the tab name, or use `--pad` on a bounded range.

### `find` and `headers`

`find` reads the tab (or the `--within` range) once and returns every row with a matching cell:
- **How it matches:** `--value` (exact, trimmed), `--contains` (case-insensitive) or `--regex`.
- **Where it searches:** `--col A,C` by letter, `--col-header "AWS / prod"` by header text (needs `--header-rows N`), or both. By default it searches every column.
- **What it returns per hit:** `row`, then the `a1`, `value` and `header` of the first matching cell, plus `also` for other matching cells in the row. Add `--show TEXT` to list every cell in that row whose header contains TEXT, with A1 addresses and values. That is the "find the cell to edit by person and tool" lookup. Add `--record` for the whole row: keyed by header with `--header-rows`, as `values` without. `--record` is the default unless `--show` is given.

No match prints `[]` with exit 0, and "no matching rows" on stderr. When `--value` matches several rows, stderr notes it: tell them apart by another column before writing.

`headers --tab T --header-rows 2` prints `[{"col": "N", "header": "AWS / prod 4719…"}, …]`, with merged header cells filled. Use it to turn a header into a column letter.

### `write`

`spreadsheets.values.update` (PUT).

| Flag | Default | Notes |
|---|---|---|
| `--value-input-option` | `USER_ENTERED` | Parses like typing: formulas, dates, numbers, currencies. `RAW` stores strings literally: leading zeros and long IDs survive, and `"=1+2"` stays text |
| `--expect JSON\|@file` | — | Compare-and-set: refused (exit 3, diff on stderr) unless the range's current values equal this. Takes the output of `read` |
| `--expect-render` | `formatted` | Must match how the snapshot was read |
| `--skip-empty` | off | `""` becomes `null`, so those cells are left alone |
| `--verify` | off | Reads back and flags dropped leading zeros, 12-15-digit IDs turned into numbers, and formula errors (exit 4) |

- **Pass the top-left cell, not a bounded range.** Values that don't fit a bounded range are rejected with `400 … tried writing to row N`. `"Tab!A1"` grows to fit the payload.
- **Destructive only where values land.** Writing `[["a"], ["b"]]` at `A1` replaces A1 and A2. A3 is untouched, and so is formatting everywhere.
- **`null` skips a cell; `""` clears it.** Writing `""` into a column filled by an `ARRAYFORMULA` breaks the array (`#REF!`). Use `null` or `--skip-empty`.
- **`--expect` covers every cell the write touches,** from the anchor to the larger of the payload and the snapshot. Cells beyond the snapshot must be empty now, or the write is refused.
- **The status line's cell count** is the API's `updatedCells`, which counts only non-empty values. A 19-row payload with blank cells reports fewer.

### `batch-write`

`values:batchUpdate`: many ranges, one call, one `--value-input-option`. `--data` is `{"Tab!A1": [[…]], …}` or `[{"range": …, "values": […]}]`. `--expect` takes the same shape, so a multi-range `read` saved earlier is a valid snapshot.

### `append`

`spreadsheets.values.append` (POST). Sheets looks for "the table" around the range you give, and adds rows after the last row of the table it finds.

| Flag | Default | Notes |
|---|---|---|
| `--insert-data-option` | `INSERT_ROWS` | Inserts new rows, which shifts what's below. `OVERWRITE` writes into the cells under the table instead and can clobber data |

Table detection can surprise. `"Sheet1"` may pick the last block on the tab. Point the range at the block's columns (`"Log!A:H"`) and check the printed `table detected at …` (the API's `tableRange`). When you need the exact row number, `read` the column, compute the next row, and `write` that explicit range.

### `clear`

`values:clear`: **values only**. Formatting, number formats, notes, validation and conditional rules stay. `--formats` also clears formatting, and `--all` clears values, formatting, notes and validation (via `updateCells`). To remove the rows themselves, use `delete-rows`. To reset a whole tab, including banding, conditional formats and the filter, use `table --replace`.

## Tabs

- `add-tab`: `--rows`/`--cols` set the starting size (default 1000 × 26), and the sheet grows as you write past it. `--sheet-id N` fixes the numeric id so later GridRanges can use it. `--rtl` makes a right-to-left tab.
- `delete-tab`: you can't delete the last tab.
- `duplicate-tab`: copies content and formatting. Keep a hidden `_template` tab and duplicate it each month.
- `move-tab --title X --index 0`: 0 is the first position.
- `set-title`: renames the spreadsheet file, which is what Drive and the browser tab show. A new file made in the UI is called "Untitled spreadsheet" until you do this.

## Structure

- `freeze --rows 0` unfreezes.
- `resize-cols` takes `--width N` for every column, `--widths 40,180,90` for one width per column starting at the first, or `--auto`. `--auto` fits the widest cell in each column, *including long note or prose rows*, which can make a column huge.
- `merge`: the merged cell keeps the top-left value and discards the rest. Unmerging doesn't bring them back.
- `insert-rows --rows 5:7` inserts 3 rows before row 5. New rows copy the formatting of the row above (`--inherit before`, the default unless you insert at row 1) or of the row below (`--inherit after`).

### Inserting at the edge of a range

Formula ranges (`SUM(B2:B20)`, `SUMIF`), chart sources, conditional-format and validation ranges grow only when you insert **strictly inside** them:

| Insert at | Extends `B2:B20`? |
|---|---|
| Row 21 (just below the last row) | **No**: the new row is outside every range |
| Row 2 (above the first data row) | **No** |
| Rows 3-20 | Yes |

To add rows at the end, insert before the last data row (row 20), then move the last row's values down. Or define ranges as open-ended (`B2:B`) from the start.

## Styling

### `format`

Pass any combination of `--bg`, `--fg`, `--bold/--no-bold`, `--italic`, `--font-size`, `--font`, `--align`, `--valign`, `--wrap/--no-wrap`, `--number-format`. The field mask covers only what you pass, so `--bg` alone keeps the cell's bold, font and number format. Several ranges in one call share the same format: `format ID "T!D2:D" "T!F2:F" --number-format "#,##0"`.

`--number-format` infers the type from the pattern: `%` → PERCENT, `y`/`d`/`mmm` → DATE, `h`/`:ss` → TIME, `"$"`/`€`/`₪` → CURRENCY, otherwise NUMBER. `TEXT` makes the cells plain text.

| Pattern | Renders | Use for |
|---|---|---|
| `#,##0.00` | `1,234.50` | Thousands separator |
| `0.00%` | 0.5 → `50.00%` | Percentages. The input is the fraction, and it takes **one** `%` on the command line |
| `"$"#,##0.00` | `$1,234.50` | USD. Quote the `$` inside the pattern and single-quote the whole pattern in the shell: `'"$"#,##0.00'` |
| `[$₪-40D] #,##0` | `₪ 1,234` | Shekels (locale-tagged) |
| `yyyy-mm-dd` | `2026-05-26` | ISO dates |
| `TEXT` | as typed | IDs you will also type into the UI |

### `format-header`

Bundles bold + colors on header row `--row N` (default 1), a freeze through that row (`--no-freeze` to skip) and an optional `--filter`, all in one atomic call. Re-running it is idempotent.

### `banding`

Zebra stripes via `addBanding`. Start the range at the header row to get a styled header band. Cell fills override band colors. Banding fails on a range that overlaps existing banding: list it with `inspect`, then remove it with `deleteBanding` or `table --replace`.

### `conditional-format`

Convenience flags for boolean rules: `--condition TYPE [--value V]… --bg/--fg/--bold`. Repeat `--value` for two-value conditions such as `NUMBER_BETWEEN`. Common types are `NUMBER_GREATER`, `NUMBER_LESS`, `NUMBER_BETWEEN`, `TEXT_EQ`, `TEXT_CONTAINS`, `TEXT_STARTS_WITH`, `DATE_BEFORE`, `BLANK`, `NOT_BLANK` and `CUSTOM_FORMULA` (`--value '=$C2="Offboarded"'`). `--rule @rule.json` takes any raw `ConditionalFormatRule`, including gradients.

Each call **adds** a rule. Nightly scripts that re-add rules pile up duplicates, so list existing rules with `inspect` and delete them with `deleteConditionalFormatRule` (by index) via `batch-update`, or rebuild with `table --replace`.

### `validation`

`--one-of "a,b,c"` (dropdown), `--one-of-range "=Roles!$A$2:$A$30"`, `--checkbox`, `--formula '=LEN(A2)<=40'`, or `--clear`. `--no-strict` warns instead of rejecting. Use open-ended ranges (`E2:E`) so new rows are covered.

**Except checkboxes:** every empty checkbox cell reads back as `FALSE`. A checkbox column over `H2:H` makes all ~1000 grid rows non-empty, so `read` returns them all, and `append` and table detection land after the grid's last row. Bound checkbox ranges to the data rows, and extend them as the table grows.

### `note`, `copy-format`

`note RANGE --text …` / `--clear` sets the same note on every cell in the range. `copy-format --from SRC --to DST` runs a `copyPaste`, and the source repeats to fill a larger destination. `--what` is `format` (default), `validation`, `conditional`, `values`, `formulas`, `all` or `no-borders`. Copying over a destination where only some cells are merged can fail or mis-merge: copy the merged top-left cell on its own, then `merge`.

### `table`

One atomic `batchUpdate`: `updateCells` (typed values) + header style + freeze + `--col-format` per column + `--widths`/`--auto-width` + `--wrap` + `--filter` + `--banding`. With `--replace` it first unmerges, clears values, formats, notes and validation, removes the filter, and deletes banding and conditional-format rules. `--create` adds the tab, and the grid grows to fit the table, both in the same batch. `--input user-entered` (the default for `--csv`) needs a separate `values.update`, so it runs in steps: grow the grid and reset formatting, write the values, lay out, then clear the old values outside the new table. Old values are never cleared before the new ones are in. Column letters in `--col-format` are sheet columns, not table-relative ones.

## Inspect / export

- `inspect --tab T` lists the frozen panes, column widths (and hidden columns), merges, conditional-format rules with their A1 ranges, banding, the basic filter, filter views, protected ranges, row and column groups, and charts with their source ranges. `--cells A1:H40` adds per-cell number formats, notes and validation, grouped into vertical runs. Colors print as hex; pass `--raw` for API objects you can paste into `batch-update`.
- `export --tab T --format png --out x.png` renders page 1 through the PDF export, then converts it with `pdftoppm` or macOS `sips`. `--format pdf|xlsx|csv` downloads the file. `--cells A1:H40` limits it to a range. Use it to look at the result: a share link needs a Google sign-in, which a headless browser doesn't have.
- `revisions` lists recent Drive revisions (time and user). Drive can't show what changed in a Sheet revision.

## Escape hatch: `batch-update`

Raw [Request](https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/request) objects, with A1 strings allowed (`"range": "Tab!A1:C3"`, `"sheetId": "Tab"`, `"backgroundColor": "#1a73e8"`). Both `[{…}]` and `{"requests":[{…}]}` work. It prints a summary; `--full` prints the whole reply. See [batch-update.md](batch-update.md).

## Cross-cutting

### Atomicity

Every command built on `batchUpdate` commits all of its requests or none: that is everything except `read`, `write`, `batch-write`, `append` and `clear` without flags. Bundle related changes into one call (`table`, or `--dry-run` outputs concatenated into one `batch-update`) to avoid half-applied states.

### Quota

60 read requests and 60 write requests per minute per user, and 300 of each per minute per project, with no daily cap. A service account is **one user**: several agents sharing a key share 60/min, and a burst of parallel reads can stall for a minute or more. The script retries 429s with backoff and jitter (5 attempts, up to ~32 s apart). It also retries 5xx and timeouts, but only for calls that are safe to repeat: reads, `values.update`, `batch-write`, `clear`, and `batchUpdate`s with no inserts, deletes or added rules. A retry of `append` or `insert-rows` after a timeout could add the rows twice, so those fail instead. Re-read and decide. Make fewer calls with `read RANGE RANGE…`, `--all-tabs`, `batch-write` and `table`.

### Idempotency

| Operation | Re-run safe? |
|---|---|
| `format`, `format-header`, `borders`, `freeze`, `resize-*`, `validation`, `note`, `copy-format`, `set-title`, `move-tab` | Yes |
| `add-filter`, `merge` | Yes (last call wins) |
| `table --replace` | Yes (resets then rebuilds) |
| `table` without `--replace` | Mostly: it fails if `--banding` overlaps the previous run's banding |
| `add-tab` with an existing title | No (duplicate name) |
| `conditional-format` | **No**: each call adds a rule |
| `banding` over existing banding | **No**: overlapping band ranges |

### Not wrapped (use `batch-update`)

Charts (`addChart`), protected ranges, named ranges, pivot tables, filter views, the Sheets Tables feature (`addTable`), developer metadata, hyperlinks in cells (write `=HYPERLINK("url","label")`), deleting a conditional-format rule, themes. Templates for the common ones are in [batch-update.md](batch-update.md).
