#!/usr/bin/env bash
# Decide whether a codex round's PROMPT citation still resolves to the bytes the
# round recorded, by comparing the cited file against `prompt_sha256` in its
# .provenance sidecar.
#
# This is the sibling of verify_artifact.sh and deliberately shares its shape,
# its three-verdict discipline and its exit codes. That one asks "did the ANSWER
# move"; this one asks "can anyone still read the QUESTION". For a PLAN round the
# repo sha is nearly meaningless and the prompt hash is the whole claim
# (codex_review.sh:224-229), so a round whose prompt is unreadable has recorded a
# verdict about a revision nobody has.
#
# THREE VERDICTS, and the third is the point:
#
#   VERIFIED     (0)  a citation resolved and its bytes hash to prompt_sha256
#   BROKEN       (1)  a citation resolved and its bytes DIFFER from prompt_sha256
#   CANNOT-TELL  (2)  nothing resolved, or there was nothing to check against
#
# ⚠️ A DANGLING PATH IS CANNOT-TELL, NEVER BROKEN. BROKEN is reserved for the case
# where bytes were actually read and actually disagreed. Collapsing "the prompt is
# gone" into BROKEN accuses a round nobody examined; collapsing it into VERIFIED
# certifies one. Measured 2026-09-19 over 498 sidecars: 190 are permanently
# CANNOT-TELL (187 predate the durable-copy mechanism entirely), and 3 are BROKEN
# — all three the same plan file, cited by three rounds at three different hashes,
# none of which the file carries today. A two-state check keyed on "does the path
# resolve" would have PASSED those three, which are the worst shape in the corpus.
#
# ⚠️ BROKEN IS NOT AN ACCUSATION, for the same reason verify_artifact.sh says so:
# a prompt file legitimately edited between rounds produces it, and that is in fact
# what the three measured instances are. It means "the citation no longer names the
# bytes the round read", which is all a hash comparison can support.

set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
usage: verify_prompt.sh <artifact.provenance>   verify one sidecar
       verify_prompt.sh <artifact.md>           same, via its sidecar
       verify_prompt.sh --dir <directory>       verify every sidecar in a directory
       verify_prompt.sh --self-test             prove this script's own verdicts fire

exit: 0 VERIFIED · 1 BROKEN · 2 CANNOT-TELL (worst verdict wins in --dir mode)
USAGE
  exit 64
}

# Read ONE key out of a sidecar, or explain why we cannot.
# Echoes "<status>\t<value>", status is OK | NOSIDECAR | NOKEY | DUP | MALFORMED | UNCHECKABLE.
#
# `want_digest=1` additionally requires the value to be exactly 64 lowercase hex.
# Refusing anything else is what stops a malformed sidecar producing a CONFIDENT
# verdict. Note codex_review.sh does NOT shape-check prompt_sha256 before writing
# it (contrast ARTIFACT_SHA, which is checked at :383): `PROMPT_SHA` falls back to
# the literal `unknown` at :231, and a hasher exiting 0 with junk is recorded
# verbatim. Both are shapes the PRODUCER can emit and neither appears in the
# corpus today, so the consumer has to refuse them on its own account.
_sidecar_value() {
  local prov="$1" key="$2" want_digest="${3:-0}" line value bytes stripped
  local -a vals=()
  [[ -f "$prov" && -r "$prov" ]] || { printf 'NOSIDECAR\t%s\n' "$prov"; return 0; }

  # Reject NUL bytes BEFORE parsing, and for the same reason verify_artifact.sh
  # does: `read` stops at a NUL, so `prompt_sha256=<valid digest>\0<junk>` is
  # delivered as just the digest and sails through the shape check. Each helper's
  # STATUS is checked — both failing leaves two empty strings, and `"" != ""` is
  # FALSE, so an unchecked comparison passes the gate precisely when it could not
  # run.
  bytes="$(wc -c < "$prov" 2>/dev/null)" || { printf 'UNCHECKABLE\t\n'; return 0; }
  stripped="$(LC_ALL=C tr -d '\000' < "$prov" 2>/dev/null | wc -c)" || { printf 'UNCHECKABLE\t\n'; return 0; }
  if [[ -z "$bytes" || -z "$stripped" ]]; then printf 'UNCHECKABLE\t\n'; return 0; fi
  if [[ "$bytes" != "$stripped" ]]; then printf 'MALFORMED\t\n'; return 0; fi

  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ "$line" == "$key="* ]] && vals+=("${line#"$key="}")
  done < "$prov"

  case "${#vals[@]}" in
    0) printf 'NOKEY\t\n'; return 0 ;;
    1) : ;;
    # DUPLICATES ARE REFUSED, NOT RESOLVED. `--label` is unsanitised and every
    # sidecar value is printf'd raw, so a label or a path carrying a newline can
    # inject a second `prompt=`. Taking the first would let the injected line
    # decide which bytes the gate believes it read.
    *) printf 'DUP\t%s\n' "${#vals[@]}"; return 0 ;;
  esac
  value="${vals[0]}"
  if (( want_digest )); then
    # The producer's own two sentinels, plus anything else off-shape, all collapse
    # to one refusal so a reader never has to interpret a novel value.
    if [[ "$value" == "unknown" || "$value" == "unavailable" ]]; then
      printf 'MALFORMED\t\n'
    elif [[ "$value" =~ ^[0-9a-f]{64}$ ]]; then
      printf 'OK\t%s\n' "$value"
    else
      # NOT echoed back: it already failed validation and may itself contain a TAB,
      # which would corrupt this function's TAB-joined result.
      printf 'MALFORMED\t\n'
    fi
  else
    [[ -n "$value" ]] && printf 'OK\t%s\n' "$value" || printf 'MALFORMED\t\n'
  fi
}

VERDICT=""   # set by verify_one
DETAIL=""
RESOLVED_VIA=""

# Classify ONE sidecar. Never returns non-zero for a "bad" verdict -- the caller
# reads $VERDICT -- so `set -e` cannot turn a BROKEN finding into an abort.
verify_one() {
  local prov="$1" parsed status cited recorded sib actual dir base
  [[ "$prov" == *.md ]] && prov="${prov%.md}.provenance"
  RESOLVED_VIA=""

  parsed="$(_sidecar_value "$prov" prompt_sha256 1)"
  status="${parsed%%$'\t'*}"
  recorded="${parsed#*$'\t'}"
  case "$status" in
    NOSIDECAR)   VERDICT="CANNOT-TELL"; DETAIL="no .provenance sidecar"; return 0 ;;
    NOKEY)       VERDICT="CANNOT-TELL"; DETAIL="sidecar has no prompt_sha256 key"; return 0 ;;
    DUP)         VERDICT="CANNOT-TELL"; DETAIL="sidecar has $recorded prompt_sha256 keys; exactly one is required"; return 0 ;;
    MALFORMED)   VERDICT="CANNOT-TELL"; DETAIL="prompt_sha256 is not 64 lowercase hex characters (or is the 'unknown'/'unavailable' sentinel)"; return 0 ;;
    UNCHECKABLE) VERDICT="CANNOT-TELL"; DETAIL="the sidecar could not be checked for NUL bytes; nothing was compared"; return 0 ;;
  esac

  parsed="$(_sidecar_value "$prov" prompt 0)"
  status="${parsed%%$'\t'*}"
  cited="${parsed#*$'\t'}"
  case "$status" in
    NOKEY)     VERDICT="CANNOT-TELL"; DETAIL="sidecar records a prompt_sha256 but no prompt= to check it against"; return 0 ;;
    DUP)       VERDICT="CANNOT-TELL"; DETAIL="sidecar has $cited prompt= keys; exactly one is required"; return 0 ;;
    MALFORMED) VERDICT="CANNOT-TELL"; DETAIL="prompt= is empty"; return 0 ;;
    NOSIDECAR|UNCHECKABLE) VERDICT="CANNOT-TELL"; DETAIL="the sidecar became unreadable between reads"; return 0 ;;
  esac

  # ── THE DURABLE-SIBLING FALLBACK, and it is the load-bearing line ────────────
  # `prompt=` is written as an ABSOLUTE path to a file codex_review.sh has just
  # copied NEXT TO the artifact (:252-255). Absolute + always-a-sibling is a
  # citation that breaks on precisely the act preserving evidence requires:
  # moving the set out of a worktree that is about to be removed. Measured
  # 2026-09-19: of 55 sidecars whose absolute prompt= no longer resolves while
  # claiming prompt_durable=yes, 52 have the bytes sitting beside them, and all
  # 52 hash to the recorded prompt_sha256. The retention worked; only the path
  # spelling failed. So resolve the SIBLING FIRST -- a copy the sidecar's own
  # directory holds is better evidence than an absolute path into somebody's
  # home directory, which may today be a DIFFERENT file of the same name.
  dir="$(dirname "$prov")"
  base="${cited##*/}"
  # `prompt_relative=` is the producer's explicit durable citation (added with the
  # §4A.7 ruling). Prefer it, but fall back to the BASENAME of `prompt=` so the
  # 52 already-written sidecars recover too -- a fix that only helps rounds not yet
  # run would leave the entire measured population in CANNOT-TELL.
  local rel_parsed rel_status rel
  rel_parsed="$(_sidecar_value "$prov" prompt_relative 0)"
  rel_status="${rel_parsed%%$'\t'*}"
  rel="${rel_parsed#*$'\t'}"
  # A relative citation must be a BARE NAME. `..`, a slash or an absolute path
  # would let a sidecar point the checker outside the directory that vouches for
  # it, which is the whole property this citation form is chosen for.
  if [[ "$rel_status" == OK && "$rel" != */* && "$rel" != ".." && -f "$dir/$rel" && -r "$dir/$rel" ]]; then
    sib="$dir/$rel"; RESOLVED_VIA="prompt_relative $rel"
  elif [[ -f "$dir/$base" && -r "$dir/$base" ]]; then
    sib="$dir/$base"; RESOLVED_VIA="durable sibling $base"
  elif [[ -f "$cited" && -r "$cited" ]]; then
    sib="$cited"; RESOLVED_VIA="recorded path"
  else
    VERDICT="CANNOT-TELL"
    DETAIL="prompt not found beside the sidecar ($base) nor at the recorded path ($cited)"
    return 0
  fi

  # BOTH conditions, for verify_artifact.sh's reason: a hasher that exits non-zero
  # while emitting the recorded digest would otherwise read as VERIFIED, and one
  # emitting junk with status 0 would read as BROKEN. Both are confident wrong
  # answers; the honest verdict when no valid digest was obtained is CANNOT-TELL.
  actual="$(shasum -a 256 "$sib" 2>/dev/null | awk '{print $1}')" || {
    VERDICT="CANNOT-TELL"; DETAIL="the hasher failed on the prompt; nothing was compared"; return 0
  }
  if [[ ! "$actual" =~ ^[0-9a-f]{64}$ ]]; then
    VERDICT="CANNOT-TELL"; DETAIL="the hasher returned something that is not a digest; nothing was compared"; return 0
  fi
  if [[ "$actual" == "$recorded" ]]; then
    VERDICT="VERIFIED"; DETAIL="$recorded (via $RESOLVED_VIA)"
  else
    VERDICT="BROKEN";   DETAIL="recorded $recorded · now $actual (via $RESOLVED_VIA)"
  fi
  return 0
}

_worst() { local a="$1" b="$2"
  [[ "$a" == 1 || "$b" == 1 ]] && { echo 1; return; }
  [[ "$a" == 2 || "$b" == 2 ]] && { echo 2; return; }
  echo 0; }
_code_for() { case "$1" in VERIFIED) echo 0 ;; BROKEN) echo 1 ;; *) echo 2 ;; esac; }

verify_dir() {
  local dir="$1" worst=0 n_ok=0 n_broken=0 n_cant=0 total=0 prov list
  local -a cant=()
  [[ -d "$dir" ]] || { echo "no such directory: $dir" >&2; exit 66; }

  # Enumerate into a file so the status of `find` and `sort` is OBSERVABLE; through
  # a process substitution a failed enumeration is indistinguishable from an empty
  # directory. EXIT, not RETURN: this function always ends in `exit`. The path is a
  # GLOBAL with a reserved name and the trap is single-quoted, so a later refactor
  # to `return` cannot make the trap `rm -f` whatever `list` is in scope.
  _VERIFY_PROMPT_LIST="$(mktemp)"
  trap 'rm -f "$_VERIFY_PROMPT_LIST" "$_VERIFY_PROMPT_LIST.s"' EXIT
  list="$_VERIFY_PROMPT_LIST"
  find "$dir" -maxdepth 1 \( -type f -o -type l \) -name '*.provenance' -print0 > "$list" || {
    echo "could not enumerate $dir; nothing was checked" >&2; exit 2; }
  sort -z < "$list" > "$list.s" || {
    echo "could not order the sidecar list; nothing was checked" >&2; exit 2; }
  mv "$list.s" "$list"

  # EVERY sidecar is classified, with no membership predicate and no exclusion
  # bucket -- verify_artifact.sh's lesson, where three attempts to define "which
  # files are rounds" were each defeated by a case one step up. A sidecar we
  # cannot check is REPORTED as CANNOT-TELL, never dropped, so nothing leaves the
  # denominator silently.
  while IFS= read -r -d '' prov; do
    total=$((total + 1))
    verify_one "$prov"
    case "$VERDICT" in
      VERIFIED) n_ok=$((n_ok + 1)) ;;
      BROKEN)   n_broken=$((n_broken + 1)); printf 'BROKEN       %s\n              %s\n' "${prov##*/}" "$DETAIL" ;;
      *)        n_cant=$((n_cant + 1)); cant+=("${prov##*/} — $DETAIL") ;;
    esac
    worst="$(_worst "$worst" "$(_code_for "$VERDICT")")"
  done < "$list"

  # An empty population is CANNOT-TELL, never success: "I verified everything" and
  # "there was nothing to verify" must not share an exit status.
  (( total == 0 )) && worst=2

  local conclusive=$((n_ok + n_broken))
  printf '\n%s of %s checked · VERIFIED %s · BROKEN %s · CANNOT-TELL %s\n' \
    "$conclusive" "$total" "$n_ok" "$n_broken" "$n_cant"
  if (( n_cant > 0 )); then
    printf '\nCANNOT-TELL:\n'
    printf '  %s\n' "${cant[@]}"
  fi
  exit "$worst"
}

# ------------------------------------------------------------------ self-test --
# THE CLEAN CONTROL RUNS FIRST AND THE RUN STOPS IF IT IS NOT GREEN: every other
# control expects a NON-VERIFIED verdict, so a checker broken against correct input
# satisfies all of them "successfully" and the defect is masked by the controls
# meant to find it.
_st_fail=0
_expect() {  # _expect <label> <wanted-verdict> <sidecar>
  local label="$1" want="$2" prov="$3"
  verify_one "$prov"
  if [[ "$VERDICT" == "$want" ]]; then
    printf '  ok    %-40s -> %s\n' "$label" "$VERDICT"
  else
    printf '  FAIL  %-40s -> %s (wanted %s: %s)\n' "$label" "$VERDICT" "$want" "$DETAIL"
    _st_fail=$((_st_fail + 1))
  fi
}

self_test() {
  local d; d="$(mktemp -d)"; trap 'rm -rf "$d"' RETURN
  local away="$d/away"; mkdir -p "$away"
  local prov="$d/20260101-000000-fix.provenance"
  local sib="$d/20260101-000000-fix.prompt.md"
  local far="$away/20260101-000000-fix.prompt.md"
  printf 'the prompt body\n' > "$sib"
  local real; real="$(shasum -a 256 "$sib" | awk '{print $1}')"

  printf 'CLEAN CONTROL FIRST — if this is not ok, every result below is meaningless\n'
  printf 'sha=abc\nprompt=%s\nprompt_sha256=%s\nprompt_durable=yes\n' "$sib" "$real" > "$prov"
  _expect 'untouched pair, path resolves' VERIFIED "$prov"
  if (( _st_fail > 0 )); then
    printf '\nSTOPPING: the clean control failed. The checker is broken against CORRECT\n'
    printf 'input, so every control below would "pass" for the wrong reason.\n'
    return 1
  fi

  # ── ONE VIOLATING CASE PER ADMITTED STATE ───────────────────────────────────
  # The repo's rule: a guard classifying by a set of states needs a case landing
  # in EACH member, not one case in total.

  printf '\nSTATE 1/3 — VERIFIED, reached by BOTH routes (the sibling fallback is the fix)\n'
  # The 52-sidecar case: the recorded absolute path is gone, the copy is beside
  # the sidecar. This must VERIFY, or the fix does not work.
  printf 'sha=abc\nprompt=%s\nprompt_relative=%s\nprompt_sha256=%s\nprompt_durable=yes\n' "$far" "${sib##*/}" "$real" > "$prov"
  _expect 'prompt_relative resolves (new producer)' VERIFIED "$prov"
  # ⚠️ DRAIN CHECK. Preferring prompt_relative NARROWS the basename route, so this
  # control exists to prove that route is still REACHABLE -- every sidecar written
  # before today has no prompt_relative at all, and they are the majority of the
  # population. A control that can no longer fire is not a passing control.
  printf 'sha=abc\nprompt=%s\nprompt_sha256=%s\nprompt_durable=yes\n' "$far" "$real" > "$prov"
  _expect 'no prompt_relative, sibling present' VERIFIED "$prov"
  # And the plain case where only the recorded path exists (no sibling).
  local d2="$d/nosib"; mkdir -p "$d2"
  local prov2="$d2/20260101-000000-other.provenance"
  cp "$sib" "$far"
  printf 'sha=abc\nprompt=%s\nprompt_sha256=%s\n' "$far" "$real" > "$prov2"
  _expect 'no sibling, recorded path resolves' VERIFIED "$prov2"

  printf '\nSTATE 2/3 — BROKEN: resolves, and the bytes disagree\n'
  # The measured tor428 shape: the cited file still exists and holds OTHER bytes.
  printf 'the prompt body, revised\n' > "$sib"
  printf 'sha=abc\nprompt=%s\nprompt_sha256=%s\nprompt_durable=yes\n' "$sib" "$real" > "$prov"
  _expect 'cited file holds different bytes' BROKEN "$prov"
  printf 'the prompt body\n' > "$sib"   # restore

  printf '\nSTATE 3/3 — CANNOT-TELL, one control per distinct cause\n'
  printf 'sha=abc\nprompt=%s/gone.prompt.md\nprompt_sha256=%s\nprompt_durable=yes\n' "$away" "$real" > "$prov"
  _expect 'nothing resolves anywhere'            CANNOT-TELL "$prov"
  # A traversal or absolute prompt_relative must not be FOLLOWED. The prompt= here
  # names a basename with no sibling, so nothing can rescue it -- if the traversal
  # were honoured this would come back VERIFIED.
  printf 'sha=abc\nprompt=%s/gone.prompt.md\nprompt_relative=../%s\nprompt_sha256=%s\n' "$away" "${sib##*/}" "$real" > "$prov"
  _expect 'prompt_relative traversal refused'    CANNOT-TELL "$prov"
  printf 'sha=abc\nprompt=%s/gone.prompt.md\nprompt_relative=%s\nprompt_sha256=%s\n' "$away" "$sib" "$real" > "$prov"
  _expect 'prompt_relative absolute refused'     CANNOT-TELL "$prov"
  printf 'sha=abc\nprompt=%s\n' "$sib" > "$prov"
  _expect 'no prompt_sha256 key'                 CANNOT-TELL "$prov"
  printf 'sha=abc\nprompt_sha256=%s\n' "$real" > "$prov"
  _expect 'hash but no prompt= to check'         CANNOT-TELL "$prov"
  printf 'sha=abc\nprompt=%s\nprompt_sha256=unknown\n' "$sib" > "$prov"
  _expect "producer sentinel 'unknown'"          CANNOT-TELL "$prov"
  printf 'sha=abc\nprompt=%s\nprompt_sha256=unavailable\n' "$sib" > "$prov"
  _expect "producer sentinel 'unavailable'"      CANNOT-TELL "$prov"
  printf 'sha=abc\nprompt=%s\nprompt_sha256=NOTAHASH\n' "$sib" > "$prov"
  _expect 'malformed digest'                     CANNOT-TELL "$prov"
  printf 'sha=abc\nprompt=%s\nprompt_sha256=%s\n' "$sib" "$(printf '%s' "$real" | tr 'a-f' 'A-F')" > "$prov"
  _expect 'uppercase digest refused'             CANNOT-TELL "$prov"
  printf 'sha=abc\nprompt=%s\nprompt_sha256=%s\nprompt_sha256=%s\n' "$sib" "$real" "$real" > "$prov"
  _expect 'duplicate prompt_sha256 keys'         CANNOT-TELL "$prov"
  printf 'sha=abc\nprompt=%s\nprompt=%s\nprompt_sha256=%s\n' "$sib" "$far" "$real" > "$prov"
  _expect 'duplicate prompt= keys (label injection)' CANNOT-TELL "$prov"
  rm -f "$prov"
  _expect 'no sidecar at all'                    CANNOT-TELL "$prov"
  { printf 'sha=abc\nprompt=%s\nprompt_sha256=%s' "$sib" "$real"; printf '\000junk\n'; } > "$prov"
  _expect 'NUL-suffixed sidecar refused'         CANNOT-TELL "$prov"

  printf '\nCRLF — a Windows-written sidecar must still VERIFY, not degrade\n'
  printf 'sha=abc\r\nprompt=%s\r\nprompt_sha256=%s\r\n' "$sib" "$real" > "$prov"
  _expect 'CRLF sidecar'                         VERIFIED "$prov"

  printf '\nHASHER controls — a failing hasher must not produce a CONFIDENT verdict\n'
  printf 'sha=abc\nprompt=%s\nprompt_sha256=%s\n' "$sib" "$real" > "$prov"
  shasum() { printf '%s  -\n' "$real"; return 7; }
  _expect 'fails BUT emits the right digest'     CANNOT-TELL "$prov"
  shasum() { printf 'not-a-digest  -\n'; return 0; }
  _expect 'succeeds with malformed output'       CANNOT-TELL "$prov"
  unset -f shasum
  _expect 'real hasher restored'                 VERIFIED "$prov"
  wc() { return 127; }
  _expect 'wc unavailable -> not a pass'         CANNOT-TELL "$prov"
  unset -f wc
  _expect 'wc restored'                          VERIFIED "$prov"

  # ── THE NON-MEMBER DIRECTION ────────────────────────────────────────────────
  # Proof that no sidecar shape the PRODUCER can emit escapes all three states.
  # Enumerated from codex_review.sh:396-399, which is the only writer: the printf
  # is a fixed 11-key template, so the value of every key is the only thing that
  # can vary. Each varying value is driven into verify_one below.
  printf '\nNON-MEMBER SWEEP — every value the producer can emit must land in a state\n'
  local st n_unclassified=0
  _sweep() { # _sweep <label> <sidecar-body>
    printf '%b' "$2" > "$prov"
    verify_one "$prov"
    case "$VERDICT" in
      VERIFIED|BROKEN|CANNOT-TELL) printf '  ok    %-40s -> %s\n' "$1" "$VERDICT" ;;
      *) printf '  FAIL  %-40s -> UNCLASSIFIED (%s)\n' "$1" "$VERDICT"; n_unclassified=$((n_unclassified + 1)) ;;
    esac
  }
  _sweep 'prompt=copy, durable=yes'   "prompt=$sib\nprompt_sha256=$real\nprompt_durable=yes\n"
  _sweep 'prompt_relative present'    "prompt=$far\nprompt_relative=${sib##*/}\nprompt_sha256=$real\nprompt_durable=yes\n"
  _sweep 'prompt_relative EMPTY (dur=no)' "prompt=$far\nprompt_relative=\nprompt_sha256=$real\nprompt_durable=no\n"
  _sweep 'prompt_relative traversal'  "prompt=$far\nprompt_relative=../escape.md\nprompt_sha256=$real\nprompt_durable=yes\n"
  _sweep 'prompt_relative absolute'   "prompt=$far\nprompt_relative=/etc/hosts\nprompt_sha256=$real\nprompt_durable=yes\n"
  _sweep 'duplicate prompt_relative'  "prompt=$far\nprompt_relative=a.md\nprompt_relative=b.md\nprompt_sha256=$real\n"
  _sweep 'prompt=origin, durable=no'  "prompt=$far\nprompt_sha256=$real\nprompt_durable=no\n"
  _sweep 'prompt_sha256=unknown'      "prompt=$sib\nprompt_sha256=unknown\nprompt_durable=yes\n"
  _sweep 'prompt_sha256 junk, dur=no' "prompt=$sib\nprompt_sha256=zz\nprompt_durable=no\n"
  _sweep 'pre-2026-08-07 key set'     "sha=abc\nbranch=b\ntree=clean\nprompt=$sib\nprompt_sha256=$real\nlabel=l\nsession=s\nstamp=t\n"
  _sweep 'full 11-key modern set'     "sha=abc\nbranch=b\ntree=clean\nprompt=$sib\nprompt_sha256=$real\nprompt_origin=$far\nprompt_durable=yes\nlabel=l\nsession=s\nstamp=t\nartifact_sha256=$real\n"
  _sweep 'injected extra prompt line' "prompt=$sib\nprompt=$far\nprompt_sha256=$real\n"
  _sweep 'empty prompt value'         "prompt=\nprompt_sha256=$real\n"
  _sweep 'tree=DIRTY round'           "sha=abc\ntree=DIRTY — uncommitted\nprompt=$sib\nprompt_sha256=$real\n"
  if (( n_unclassified > 0 )); then _st_fail=$((_st_fail + n_unclassified)); fi

  printf '\nDIRECTORY-MODE control — nothing may leave the denominator silently\n'
  local dd="$d/dirmode"; mkdir -p "$dd"
  cp "$sib" "$dd/real.prompt.md"
  printf 'prompt=%s/real.prompt.md\nprompt_sha256=%s\n' "$dd" "$real" > "$dd/real.provenance"
  printf 'prompt=/nowhere/x.md\nprompt_sha256=%s\n' "$real" > "$dd/gone.provenance"
  ln -s "$dd/real.provenance" "$dd/linked.provenance"
  local out
  out="$( ( verify_dir "$dd" ) 2>/dev/null | sed -n 's/^[0-9]* of \([0-9]*\) checked.*/\1/p' )" || true
  if [[ "$out" == "3" ]]; then
    printf '  ok    %-40s -> 3 of 3 classified\n' 'symlink + dangling counted'
  else
    printf '  FAIL  %-40s -> %s classified, wanted 3\n' 'symlink + dangling counted' "$out"
    _st_fail=$((_st_fail + 1))
  fi

  printf '\n'
  if (( _st_fail == 0 )); then printf 'self-test: all controls behaved as specified\n'; return 0
  else printf 'self-test: %s control(s) FAILED\n' "$_st_fail"; return 1; fi
}

# ------------------------------------------------------------------------ main --
[[ $# -ge 1 ]] || usage
case "$1" in
  --self-test) self_test ;;
  --dir)       [[ $# -ge 2 ]] || usage; verify_dir "$2" ;;
  -h|--help)   usage ;;
  -*)          usage ;;
  *)
    verify_one "$1"
    printf '%-12s %s\n            %s\n' "$VERDICT" "${1##*/}" "$DETAIL"
    exit "$(_code_for "$VERDICT")"
    ;;
esac
