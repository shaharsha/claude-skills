# `gsheets.py` — CLI reference

A single Python file. No package, no install (beyond `pip install google-auth` for service-account auth — optional, see fallbacks below). All subcommands accept `<SPREADSHEET_ID>` as the first positional, and `--sa-key <path>` for auth.

```
gsheets.py <command> <SPREADSHEET_ID> [flags…]
```

For full per-subcommand flags, run:

```bash
./gsheets.py <command> --help
```

## Commands at a glance

```
Data            read           --range
                write          --range --values-json|--csv|--values-stdin [--value-input-option]
                append         --range --values-json|--csv [--insert-data-option]
                clear          --range

Tabs            list-tabs
                add-tab        --title [--rows --cols --index --color]
                delete-tab     --title
                rename-tab     --from --to
                duplicate-tab  --from --to [--index]

Structure       freeze         --tab [--rows N --cols N]
                resize-cols    --tab --cols A:C  (--width N | --auto)
                resize-rows    --tab --rows 1:3  (--height N | --auto)
                merge          --range [--merge-type MERGE_ALL|MERGE_COLUMNS|MERGE_ROWS]
                unmerge        --range
                insert-rows    --tab --rows 5:7
                delete-rows    --tab --rows 5:7
                insert-cols    --tab --cols B:D
                delete-cols    --tab --cols B:D

Styling         format         --range [--bg --fg --bold --italic --font-size --font
                                        --align --valign --wrap --number-format]
                format-header  --tab [--bg --fg --filter]
                borders        --range [--all | --top --bottom --left --right --inner]
                               [--style SOLID|DOTTED|DASHED|... --color #hex]
                banding        --range [--header-bg --first-bg --second-bg --footer-bg]
                conditional-format --range
                                   [--condition <TYPE> [--value V] [--bg --fg --bold]]
                                   | [--rule @rule.json]
                                   [--index 0]

Filter/sort     add-filter     --range
                clear-filter   --tab
                sort           --range --by "B:desc,C:asc"

Escape          batch-update   --requests @requests.json (or inline JSON)

Meta            info           (lists tabs + edit access + owner — safe dry-run)
```

## Auth flags

| Flag | When to use |
|---|---|
| `--sa-key /path/to/sa.json` | Service-account JSON. Recommended. |
| *(no flag)* | Falls back to `gcloud auth application-default print-access-token --scopes=...spreadsheets,...drive`. Needs a prior `gcloud auth application-default login` with those scopes. |

The script always passes explicit scopes to gcloud — the default cloud-platform-only token is silently insufficient for Sheets/Drive write.

## Common flag patterns

### Value input (`write`, `append`)

| Source | Flag |
|---|---|
| Inline JSON | `--values-json '[["a","b"],["c","d"]]'` |
| JSON file | `--values-json @data.json` |
| CSV file | `--csv data.csv` |
| CSV via stdin | `pipe \| ./gsheets.py write ... --values-stdin` |

### Range notation

`"<TabTitle>!A1:C10"` — most commands. Single cell (`A1`) or whole-column ranges (`A:Z`) also work.

For tabs with spaces in the title, quote them in the A1 string: `"'Q3 Review'!A1:Z"`. (Bash will swallow one layer of quotes, so this becomes `--range "'Q3 Review'!A1:Z"` in practice.)

### Color flags

Always hex: `--bg "#1a73e8"`. The leading `#` is optional. 3-char shorthand (`#f00`) works.

## Idempotency

| Re-running with same args | Safe? |
|---|---|
| `format`, `format-header`, `borders`, `freeze`, `resize-*` | Yes |
| `merge`, `add-filter` | Yes (last-write-wins) |
| `add-tab` with existing title | No (API: duplicate name) |
| `delete-tab` with deleted title | No (script: tab not found) |
| `banding` overlapping existing | No (API: overlapping ranges) |
| `conditional-format` | No — each call adds another rule. |

## Dependencies

- **Python ≥ 3.9**
- **stdlib only** for HTTP (uses `urllib.request`)
- For `--sa-key` auth: `pip install google-auth` (preferred) OR `pip install cryptography` (fallback, JWT minted manually)
- For no-`--sa-key` auth: `gcloud` CLI on PATH

## Examples by use case

### Push a CSV with header styling

```bash
gsheets.py write           $ID --range "Review!A1" --csv data.csv          --sa-key sa.json
gsheets.py format-header   $ID --tab Review --bg "#0b8043" --fg "#fff" --filter  --sa-key sa.json
gsheets.py resize-cols     $ID --tab Review --cols A:Z --auto             --sa-key sa.json
```

### Build a multi-tab dashboard

```bash
gsheets.py add-tab     $ID --title Summary --index 0 --color "#1a73e8" --sa-key sa.json
gsheets.py add-tab     $ID --title Raw     --index 1                   --sa-key sa.json
gsheets.py write       $ID --range "Raw!A1"     --csv raw.csv          --sa-key sa.json
gsheets.py write       $ID --range "Summary!A1" --values-json '[["KPI","Value"],["MRR","=SUM(Raw!C:C)"]]' --sa-key sa.json
gsheets.py format-header $ID --tab Summary --sa-key sa.json
gsheets.py format-header $ID --tab Raw     --filter --sa-key sa.json
```

### Highlight failing rows

```bash
gsheets.py conditional-format $ID \
  --range "Tests!E2:E" \
  --condition TEXT_EQ --value fail \
  --bg "#fce8e6" --fg "#b71c1c" --bold \
  --sa-key sa.json
```

### Escape hatch — gradient color scale

```bash
gsheets.py batch-update $ID --requests @./gradient.json --sa-key sa.json
```

(See `../reference/batch-update.md` for the rule JSON.)
