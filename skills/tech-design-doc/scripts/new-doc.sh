#!/usr/bin/env bash
# new-doc.sh — scaffold a new technical design doc from a template.
#
# Usage:
#   new-doc.sh --template <mini-adr|standard-rfc|heavyweight|partner> \
#              --slug <kebab-case-slug> \
#              --title "Doc title" \
#              [--author "Name"] [--approvers "Name1, Name2"] \
#              [--partner "Partner name"] [--date YYYY-MM-DD] \
#              [--out drafts/] [--out-file path/to/exact-name.md] \
#              [--number 0042] [--force]
#
# Writes to: <out>/design-<slug>-v1.md (or drafts/adr-<NNNN>-<slug>.md for mini-adr).
# Pass --out-file to write to an exact path instead.
# Refuses to overwrite an existing file (use --force to override).

set -euo pipefail

TEMPLATE=""
SLUG=""
TITLE=""
AUTHOR="${USER:-author}"
APPROVERS="(TBD)"
PARTNER="(partner)"
OUT="drafts"
OUT_FILE=""
NUMBER=""
DATE_OVERRIDE=""
FORCE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --template)  TEMPLATE="$2"; shift 2 ;;
    --slug)      SLUG="$2"; shift 2 ;;
    --title)     TITLE="$2"; shift 2 ;;
    --author)    AUTHOR="$2"; shift 2 ;;
    --approvers) APPROVERS="$2"; shift 2 ;;
    --partner)   PARTNER="$2"; shift 2 ;;
    --out)       OUT="$2"; shift 2 ;;
    --out-file)  OUT_FILE="$2"; shift 2 ;;
    --number)    NUMBER="$2"; shift 2 ;;
    --date)      DATE_OVERRIDE="$2"; shift 2 ;;
    --force)     FORCE=true; shift ;;
    -h|--help)
      sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$TEMPLATE" || -z "$SLUG" || -z "$TITLE" ]]; then
  echo "error: --template, --slug, --title are required" >&2
  echo "  templates: mini-adr | standard-rfc | heavyweight | partner" >&2
  exit 2
fi

case "$TEMPLATE" in
  mini-adr)      TMPL="mini-adr.md.tmpl" ;;
  standard-rfc)  TMPL="standard-rfc.md.tmpl" ;;
  heavyweight)   TMPL="heavyweight-doc.md.tmpl" ;;
  partner)       TMPL="partner-doc.md.tmpl" ;;
  *)
    echo "error: unknown template '$TEMPLATE'" >&2
    echo "  valid: mini-adr | standard-rfc | heavyweight | partner" >&2
    exit 2
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMPL_PATH="$SCRIPT_DIR/../templates/$TMPL"
if [[ ! -f "$TMPL_PATH" ]]; then
  echo "error: template not found at $TMPL_PATH" >&2
  exit 1
fi

if [[ -n "$OUT_FILE" ]]; then
  OUT_PATH="$OUT_FILE"
  FILENAME="$(basename "$OUT_FILE")"
  out_dir="$(dirname "$OUT_PATH")"
  [[ -n "$out_dir" && "$out_dir" != "." ]] && mkdir -p "$out_dir"
else
  mkdir -p "$OUT"
  if [[ "$TEMPLATE" == "mini-adr" ]]; then
    if [[ -z "$NUMBER" ]]; then
      # Auto-pick the next number based on existing adr-* files in OUT
      LAST=$(ls "$OUT" 2>/dev/null | grep -E '^adr-[0-9]{4}-' | sed -E 's/^adr-([0-9]{4}).*/\1/' | sort -n | tail -1 || true)
      if [[ -z "$LAST" ]]; then
        NUMBER="0001"
      else
        NUMBER=$(printf "%04d" $((10#$LAST + 1)))
      fi
    fi
    FILENAME="adr-$NUMBER-$SLUG.md"
  else
    FILENAME="design-$SLUG-v1.md"
  fi
  OUT_PATH="$OUT/$FILENAME"
fi

if [[ -f "$OUT_PATH" && "$FORCE" != true ]]; then
  echo "error: $OUT_PATH already exists. Use --force to overwrite, or bump --slug / version." >&2
  exit 1
fi

if [[ -n "$DATE_OVERRIDE" ]]; then
  DATE="$DATE_OVERRIDE"
else
  DATE=$(date +%Y-%m-%d)
fi

# Substitute placeholders
sed \
  -e "s|{{TITLE}}|$TITLE|g" \
  -e "s|{{AUTHOR}}|$AUTHOR|g" \
  -e "s|{{APPROVERS}}|$APPROVERS|g" \
  -e "s|{{DATE}}|$DATE|g" \
  -e "s|{{NUMBER}}|$NUMBER|g" \
  -e "s|{{FILENAME}}|$FILENAME|g" \
  -e "s|{{PARTNER_NAME}}|$PARTNER|g" \
  "$TMPL_PATH" > "$OUT_PATH"

echo "✓ Scaffolded: $OUT_PATH"
echo
echo "Next steps:"
echo "  1. Edit the file: open '$OUT_PATH'"
echo "  2. Fill Summary + Goals/Non-Goals first (BLUF)"
echo "  3. Write ≥3 Alternatives BEFORE detailing the proposal"
echo "  4. Audit: ~/.claude/skills/tech-design-doc/scripts/audit-doc.py '$OUT_PATH'"
