# `gsheets.py`: CLI reference

One Python file with no install step. It uses `google-auth` when that is importable, and otherwise signs the service-account token with `cryptography` or the `openssl` CLI, so a bare `python3` works. `uv run gsheets.py …` also works; the dependencies are declared inline.

```
gsheets.py [--sa-key PATH] [--dry-run] <command> <SPREADSHEET_ID> [RANGE…] [flags…]
```

`--sa-key` and `--dry-run` go before or after the command. Run `gsheets.py <command> --help` for every flag.

In zsh, wrap it in a function rather than a variable: zsh doesn't word-split `$G`.

```bash
gsheets() { python3 ~/.claude/skills/gsheets/scripts/gsheets.py "$@"; }
```

## Commands at a glance

```
Data       read          RANGE… [--all-tabs] [--render formatted|unformatted|formula]
                         [--pad] [--fill-merged] [--header-rows N] [--numbered]
           find          --tab T (--value V | --contains V | --regex R) [--col A,C]
                         [--header-rows N [--col-header TEXT] [--show TEXT]] [--record]
                         [--within A1:Z500]
           headers       --tab T [--header-rows N]           (column letter ↔ header path)
           write         RANGE (--values-json|--csv|--values-stdin) [--value-input-option RAW]
                         [--expect @snap.json] [--skip-empty] [--verify]
           batch-write   --data '{"T!A1": [[..]], ...}' [--expect @snap.json] [--verify]
           append        RANGE (--values-json|--csv) [--insert-data-option INSERT_ROWS|OVERWRITE]
           clear         RANGE [--formats | --all]

Tabs       list-tabs | add-tab --title [--index --color --sheet-id --rtl --rows --cols]
           delete-tab --title | rename-tab --from --to | duplicate-tab --from --to [--index]
           move-tab --title --index | set-title --title          (renames the file)

Structure  freeze --tab [--rows N] [--cols N]
           resize-cols --tab --cols A:F (--width N | --widths 40,180,90 | --auto)
           resize-rows --tab --rows 1:3 (--height N | --auto)
           merge RANGE [--merge-type] | unmerge RANGE
           insert-rows|insert-cols --tab --rows 5:7|--cols B:D [--inherit before|after]
           delete-rows|delete-cols --tab --rows 5:7|--cols B:D

Styling    format RANGE… [--bg --fg --bold --italic --font-size --font --align --valign
                          --wrap/--no-wrap --number-format]
           format-header --tab [--row N] [--bg --fg] [--no-freeze] [--filter]
           borders RANGE (--all | --top --bottom --left --right --inner) [--style --color]
           banding RANGE [--header-bg --first-bg --second-bg --footer-bg]
           conditional-format RANGE (--condition TYPE [--value V]… [--bg --fg --bold] | --rule @r.json)
           validation RANGE (--one-of a,b | --one-of-range =T!$A$2:$A$30 | --checkbox
                             | --formula F | --clear) [--no-strict] [--help-text]
           note RANGE (--text T | --clear)
           copy-format --from RANGE --to RANGE [--what format|validation|conditional|...]
           table --tab T (--values-json|--csv) [--at A1] [--create] [--replace]
                 [--header-rows 1] [--col-format COLS=PATTERN]… [--widths ..|--auto-width]
                 [--wrap] [--filter] [--banding] [--freeze-cols N] [--input typed|user-entered]

Filter     add-filter RANGE | clear-filter --tab | sort RANGE --by "B:desc,C:asc"

Inspect    info | revisions [--limit N]
           inspect --tab T [--cells A1:H40] [--raw]
           export [--tab T] [--cells A1:H40] --format pdf|png|csv|xlsx --out FILE

Escape     batch-update --requests @file.json [--full]     (A1 strings and #hex colors allowed)
```

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success. Data is on stdout |
| 1 | API error. The HTTP status, Google's message and a `hint:` are on stderr |
| 2 | Usage error (argparse) |
| 3 | `--expect` refused the write. The cell diff is on stderr |
| 4 | `--verify` found a bad conversion (leading zeros, ID turned into a number, formula error) |

On any non-zero exit, stdout is empty, so a pipe into `json.load` won't half-parse.

## Value input

| Source | Flag |
|---|---|
| Inline JSON | `--values-json '[["a","b"],["c","d"]]'` |
| JSON file | `--values-json @data.json` |
| CSV file | `--csv data.csv` |
| CSV on stdin | `… \| gsheets.py write ID "T!A1" --values-stdin` |

In JSON, `null` leaves a cell untouched and `""` clears it. For text containing quotes, `→` or other awkward characters, build the JSON file in Python rather than quoting it in the shell.

## Examples

```bash
# a stakeholder tab from a CSV, in one call
gsheets table $ID --tab Review --create --csv results.csv --filter --banding \
  --col-format "D=0.0%" --widths 180,90,90,80

# safe edit of a co-edited sheet
gsheets find  $ID --tab Access --col A --value "Dana Levi"                        # → row 14
gsheets read  $ID "Access!F14" > /tmp/f14.json
gsheets write $ID "Access!F14" --values-json '[["Admin"]]' --expect @/tmp/f14.json

# log row at an exact position
gsheets read  $ID "'Access log'!A:A" | python3 -c 'import json,sys; print(len(json.load(sys.stdin))+1)'   # → 90
gsheets write $ID "'Access log'!A90" --values-json @row.json --value-input-option RAW

# look at the result
gsheets export $ID --tab Review --format png --out /tmp/review.png
```
