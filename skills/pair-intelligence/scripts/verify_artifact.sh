#!/usr/bin/env bash
# Decide whether a codex round's .md still holds the bytes recorded when it was
# generated, by comparing it against `artifact_sha256` in its .provenance sidecar.
#
# THREE VERDICTS, and the third is the point:
#
#   UNCHANGED    (0)  a valid recorded digest, and it matches
#   CHANGED      (1)  a valid recorded digest, and it differs
#   CANNOT-TELL  (2)  there is nothing to check against
#
# CANNOT-TELL must never collapse into either neighbour. As 0 it would certify an
# artifact nobody examined; as 1 it would accuse one nobody examined. Every round
# generated before `artifact_sha256` existed is in this class, permanently -- that
# is a fact about the evidence, not a defect in the file.
#
# ⚠️ CHANGED IS NOT AN ACCUSATION. It means "differs from what was recorded at
# generation", nothing more. This tool compares bytes, and bytes cannot distinguish
# tampering from a legitimate regeneration -- re-rendering a .md from its .json with
# render_review.py, for instance, changes it honestly. Claiming to tell those apart
# would assert a discrimination the method cannot make.

set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
usage: verify_artifact.sh <artifact.md>       verify one artifact
       verify_artifact.sh --dir <directory>   verify every .md in a directory
       verify_artifact.sh --self-test         prove this script's own verdicts fire

exit: 0 UNCHANGED · 1 CHANGED · 2 CANNOT-TELL (worst verdict wins in --dir mode)
USAGE
  exit 64
}

# Read the recorded digest out of a sidecar, or explain why we cannot.
# Echoes "<status>\t<detail>", where status is OK | NOSIDECAR | NOKEY | DUP | SENTINEL | MALFORMED.
#
# The grammar is strict on purpose. Sidecar values are printf'd unescaped by
# codex_review.sh and `--label` is not sanitised, so a hostile or merely careless
# label can inject an extra line. Refusing anything that is not exactly one
# 64-character lowercase digest is what stops a malformed sidecar producing a
# CONFIDENT verdict -- the failure mode being avoided is a wrong answer, not a crash.
_recorded_digest() {
  local prov="$1" line value bytes stripped
  local -a vals=()
  [[ -f "$prov" && -r "$prov" ]] || { printf 'NOSIDECAR\t%s\n' "$prov"; return 0; }

  # Reject NUL bytes BEFORE parsing. `read` stops at a NUL, so a line of the form
  # `artifact_sha256=<valid digest>\0<junk>` is delivered as just the digest and
  # sails through the shape check -- a malformed sidecar producing a CONFIDENT
  # UNCHANGED, which is the one outcome this tool must never produce. The shape
  # check cannot catch it because the bytes that make it malformed are the bytes
  # `read` discarded, so the test has to happen at the byte level, before parsing.
  # Each helper's STATUS is checked, not just its output. Both failing produces two
  # empty strings, and `"" != ""` is FALSE -- so an unchecked comparison passes the
  # gate precisely when the check could not run, and a NUL-suffixed digest then
  # reads as UNCHANGED. Measured with both `wc` calls returning 127: the gate
  # passed. A check that cannot run must say so, never wave the input through.
  bytes="$(wc -c < "$prov" 2>/dev/null)" || { printf 'UNCHECKABLE\t\n'; return 0; }
  stripped="$(LC_ALL=C tr -d '\000' < "$prov" 2>/dev/null | wc -c)" || { printf 'UNCHECKABLE\t\n'; return 0; }
  if [[ -z "$bytes" || -z "$stripped" ]]; then
    printf 'UNCHECKABLE\t\n'; return 0
  fi
  if [[ "$bytes" != "$stripped" ]]; then
    printf 'MALFORMED\t\n'; return 0
  fi

  # KNOWN AND ACCEPTED: the sidecar is opened twice — once above for the NUL check,
  # once below to parse — so a rewrite landing between them is not detected. Not
  # fixed, and the reason is that closing it buys nothing: anyone able to rewrite the
  # sidecar mid-check can simply write a matching digest instead, which no amount of
  # atomicity here would catch. The race grants an attacker nothing they do not
  # already have, and sidecars are written once at generation and never revised.
  #
  # Read once and collect, rather than `grep -c` + `sed`. `grep -c` exits 1 for a
  # legitimate zero count and >1 for a real error, so a `|| true` that makes the
  # normal case work also swallows the error case -- and the two mean opposite
  # things. Counting here leaves no status to misread. `|| [[ -n $line ]]` catches
  # a final line with no newline; `%$'\r'` tolerates a CRLF sidecar.
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ "$line" == artifact_sha256=* ]] && vals+=("${line#artifact_sha256=}")
  done < "$prov"

  case "${#vals[@]}" in
    0) printf 'NOKEY\t\n'; return 0 ;;
    1) : ;;
    *) printf 'DUP\t%s\n' "${#vals[@]}"; return 0 ;;
  esac
  value="${vals[0]}"
  if [[ "$value" == "unavailable" ]]; then
    printf 'SENTINEL\t\n'
  elif [[ "$value" =~ ^[0-9a-f]{64}$ ]]; then
    printf 'OK\t%s\n' "$value"
  else
    # The value is deliberately NOT echoed back: it has already failed validation,
    # and a malformed value can itself contain a tab, which would corrupt the
    # TAB-joined result this function returns.
    printf 'MALFORMED\t\n'
  fi
}

VERDICT=""   # set by verify_one
DETAIL=""

# Classify ONE .md. Never returns non-zero for a "bad" verdict -- the caller reads
# $VERDICT -- so that `set -e` cannot turn a CHANGED finding into an abort.
verify_one() {
  local md="$1" prov actual parsed status recorded
  prov="${md%.md}.provenance"

  if [[ ! -f "$md" || ! -r "$md" ]]; then
    VERDICT="CANNOT-TELL"; DETAIL="artifact missing or unreadable"; return 0
  fi

  parsed="$(_recorded_digest "$prov")"
  status="${parsed%%$'\t'*}"
  recorded="${parsed#*$'\t'}"

  case "$status" in
    NOSIDECAR) VERDICT="CANNOT-TELL"; DETAIL="no .provenance sidecar (round predates artifact_sha256, or is not a round artifact)"; return 0 ;;
    NOKEY)     VERDICT="CANNOT-TELL"; DETAIL="sidecar has no artifact_sha256 key (generated before this check existed)"; return 0 ;;
    DUP)       VERDICT="CANNOT-TELL"; DETAIL="sidecar has $recorded artifact_sha256 keys; exactly one is required"; return 0 ;;
    SENTINEL)  VERDICT="CANNOT-TELL"; DETAIL="sidecar records artifact_sha256=unavailable — the hash could not be computed at generation"; return 0 ;;
    MALFORMED) VERDICT="CANNOT-TELL"; DETAIL="sidecar artifact_sha256 is not 64 lowercase hex characters"; return 0 ;;
    UNCHECKABLE) VERDICT="CANNOT-TELL"; DETAIL="the sidecar could not be checked for NUL bytes (wc/tr unavailable or failed); nothing was compared"; return 0 ;;
  esac

  # BOTH conditions, and neither alone is enough. A hasher that exits non-zero while
  # emitting the recorded digest would otherwise be read as UNCHANGED -- certifying an
  # artifact on the word of a command that reported failure. One emitting malformed
  # output with status 0 would be read as CHANGED, accusing an untouched file. Both
  # are confident wrong answers, which is the only class of bug that matters here;
  # the honest verdict when no valid digest was obtained is CANNOT-TELL.
  actual="$(shasum -a 256 "$md" 2>/dev/null | awk '{print $1}')" || {
    VERDICT="CANNOT-TELL"; DETAIL="the hasher failed on this artifact; nothing was compared"; return 0
  }
  if [[ ! "$actual" =~ ^[0-9a-f]{64}$ ]]; then
    VERDICT="CANNOT-TELL"; DETAIL="the hasher returned something that is not a digest; nothing was compared"; return 0
  fi
  if [[ "$actual" == "$recorded" ]]; then
    VERDICT="UNCHANGED"; DETAIL="$recorded"
  else
    VERDICT="CHANGED";   DETAIL="recorded $recorded · now $actual"
  fi
  return 0
}

_worst() {  # 1 (CHANGED) beats 2 (CANNOT-TELL) beats 0
  local a="$1" b="$2"
  [[ "$a" == 1 || "$b" == 1 ]] && { echo 1; return; }
  [[ "$a" == 2 || "$b" == 2 ]] && { echo 2; return; }
  echo 0
}

_code_for() { case "$1" in UNCHANGED) echo 0 ;; CHANGED) echo 1 ;; *) echo 2 ;; esac; }

verify_dir() {
  local dir="$1" worst=0 n_ok=0 n_changed=0 n_cant=0 total=0 md list
  local -a cant=()
  [[ -d "$dir" ]] || { echo "no such directory: $dir" >&2; exit 66; }

  # Enumerate into a file rather than a process substitution, so the status of
  # `find` and `sort` is OBSERVABLE. Through `done < <(find … | sort -z)` a failed
  # enumeration is indistinguishable from an empty directory, and the run would
  # report success having listed nothing.
  # EXIT, not RETURN: this function always ends in `exit`, and a RETURN trap does
  # not fire on `exit` -- so the enumeration file would leak on every single run.
  # `$list.s` is named too, because a failing `sort` leaves it behind.
  #
  # The path is a GLOBAL with a reserved name, and the trap is single-quoted so it
  # reads that global when it fires -- NOT a `local`. Measured on bash 3.2.57 a
  # local IS still visible to the trap when `exit` is called from inside the
  # function, so the local form works TODAY. It stops working the moment anyone
  # changes this function to `return` instead: the frame is gone by then, and the
  # trap would resolve whatever `list` happens to exist in the environment and
  # `rm -f` THAT. A one-word rename removes a latent `rm` on an attacker- or
  # accident-supplied path, and costs nothing.
  _VERIFY_ARTIFACT_LIST="$(mktemp)"
  trap 'rm -f "$_VERIFY_ARTIFACT_LIST" "$_VERIFY_ARTIFACT_LIST.s"' EXIT
  list="$_VERIFY_ARTIFACT_LIST"
  # `\( -type f -o -type l \)`, never a bare `-type f`: a SYMLINKED .md is still a
  # .md, and dropping it silently is the exact defect the missing membership
  # predicate was removed to prevent -- rebuilt one layer down, in `find`. A broken
  # or unreadable link reaches verify_one and lands in CANNOT-TELL, which is true.
  find "$dir" -maxdepth 1 \( -type f -o -type l \) -name '*.md' -print0 > "$list" || {
    echo "could not enumerate $dir; nothing was checked" >&2; exit 2; }
  sort -z < "$list" > "$list.s" || {
    echo "could not order the artifact list; nothing was checked" >&2; exit 2; }
  mv "$list.s" "$list"

  # EVERY .md is classified. There is no membership predicate and no exclusion
  # bucket, deliberately: three successive attempts to define "which .md files are
  # rounds" were each defeated by a case one step up (a shape match admitted
  # *.prompt.md; an evidence match dropped a real round whose .json had been
  # cleaned up). A file we cannot verify is REPORTED as CANNOT-TELL rather than
  # dropped, so no real round can leave the denominator. Saying "I cannot verify
  # PR-BODY-x.md" is true and costs one line.
  while IFS= read -r -d '' md; do
    total=$((total + 1))
    verify_one "$md"
    case "$VERDICT" in
      UNCHANGED) n_ok=$((n_ok + 1)) ;;
      CHANGED)   n_changed=$((n_changed + 1)); printf 'CHANGED      %s\n              %s\n' "${md##*/}" "$DETAIL" ;;
      *)         n_cant=$((n_cant + 1)); cant+=("${md##*/} — $DETAIL") ;;
    esac
    worst="$(_worst "$worst" "$(_code_for "$VERDICT")")"
  done < "$list"

  # An empty population is CANNOT-TELL, never success. `worst` starts at 0, so
  # without this an empty or wrongly-pointed directory exits 0 — the documented
  # UNCHANGED code — having checked nothing at all. "I verified everything" and
  # "there was nothing to verify" must not share an exit status.
  (( total == 0 )) && worst=2

  # The coverage fraction is stated, always, and never as a bare CLEAN. A checker
  # that examined half its population and said "clean" is the exact defect this
  # tool was built after.
  local conclusive=$((n_ok + n_changed))
  printf '\n%s of %s verified · UNCHANGED %s · CHANGED %s · CANNOT-TELL %s\n' \
    "$conclusive" "$total" "$n_ok" "$n_changed" "$n_cant"
  if (( n_cant > 0 )); then
    printf '\nCANNOT-TELL:\n'
    printf '  %s\n' "${cant[@]}"
  fi
  exit "$worst"
}

# ------------------------------------------------------------------ self-test --
# Every control below must be watched failing before it is believed, so each one
# names what it would catch. THE CLEAN CONTROL RUNS FIRST AND THE RUN STOPS IF IT
# IS NOT GREEN: every other control expects a NON-UNCHANGED verdict, so a verifier
# broken against correct input satisfies all of them "successfully" and the defect
# is masked by the controls meant to find it.
_st_fail=0
_expect() {  # _expect <label> <wanted-verdict> <md>
  local label="$1" want="$2" md="$3"
  verify_one "$md"
  if [[ "$VERDICT" == "$want" ]]; then
    printf '  ok    %-34s -> %s\n' "$label" "$VERDICT"
  else
    printf '  FAIL  %-34s -> %s (wanted %s: %s)\n' "$label" "$VERDICT" "$want" "$DETAIL"
    _st_fail=$((_st_fail + 1))
  fi
}

self_test() {
  local d; d="$(mktemp -d)"; trap 'rm -rf "$d"' RETURN
  local md="$d/20260101-000000-fixture.md" prov="$d/20260101-000000-fixture.provenance"
  printf 'the artifact body\n' > "$md"
  local real; real="$(shasum -a 256 "$md" | awk '{print $1}')"

  printf 'CLEAN CONTROL FIRST — if this is not ok, every result below is meaningless\n'
  printf 'sha=abc\nartifact_sha256=%s\n' "$real" > "$prov"
  _expect 'untouched pair' UNCHANGED "$md"
  if (( _st_fail > 0 )); then
    printf '\nSTOPPING: the clean control failed. The verifier is broken against CORRECT\n'
    printf 'input, so every mutation control below would "pass" for the wrong reason.\n'
    return 1
  fi

  printf '\nmutation control — must be detected\n'
  printf 'the artifact body, edited\n' > "$md"
  _expect 'one byte changed' CHANGED "$md"
  printf 'the artifact body\n' > "$md"   # restore

  printf '\nCANNOT-TELL controls — one per cause, each must NOT masquerade as a verdict\n'
  rm -f "$prov";                                              _expect 'no sidecar'        CANNOT-TELL "$md"
  printf 'sha=abc\n' > "$prov";                               _expect 'sidecar, no key'   CANNOT-TELL "$md"
  printf 'artifact_sha256=unavailable\n' > "$prov";           _expect 'sentinel'          CANNOT-TELL "$md"
  printf 'artifact_sha256=NOTAHASH\n' > "$prov";              _expect 'malformed'         CANNOT-TELL "$md"
  printf 'artifact_sha256=%s\nartifact_sha256=%s\n' "$real" "$real" > "$prov"
  _expect 'duplicate keys' CANNOT-TELL "$md"
  printf 'artifact_sha256=%s\n' "$real" > "$prov"
  _expect 'artifact missing' CANNOT-TELL "$d/nonexistent.md"

  # An uppercase digest is refused deliberately: shasum emits lowercase, so an
  # uppercase value did not come from the generator and its provenance is unknown.
  printf 'artifact_sha256=%s\n' "$(printf '%s' "$real" | tr 'a-f' 'A-F')" > "$prov"
  _expect 'uppercase hex refused' CANNOT-TELL "$md"

  # A CRLF sidecar must still parse — otherwise the digest silently carries a \r,
  # fails the hex match, and a perfectly good artifact reports CANNOT-TELL.
  printf 'artifact_sha256=%s\r\n' "$real" > "$prov"
  _expect 'CRLF sidecar' UNCHANGED "$md"

  # A NUL truncates `read`, so the junk after it vanishes and the digest looks
  # valid. This control is the reason the byte-level check exists; without it the
  # sidecar is malformed and the verdict is a confident UNCHANGED.
  { printf 'artifact_sha256=%s' "$real"; printf '\000junk\n'; } > "$prov"
  _expect 'NUL-suffixed digest refused' CANNOT-TELL "$md"

  printf '\nHASHER controls — a failing hasher must not produce a CONFIDENT verdict\n'
  printf 'artifact_sha256=%s\n' "$real" > "$prov"
  # A function shadows the command for verify_one, which runs in this same shell.
  # The dangerous case is the FIRST one: output that matches, from a command that
  # reported failure. Read as UNCHANGED it certifies an artifact on the word of a
  # hasher that said it failed.
  shasum() { printf '%s  -\n' "$real"; return 7; }
  _expect 'fails BUT emits the right digest' CANNOT-TELL "$md"
  shasum() { printf 'not-a-digest  -\n'; return 0; }
  _expect 'succeeds with malformed output' CANNOT-TELL "$md"
  unset -f shasum
  _expect 'real hasher restored' UNCHANGED "$md"

  # The NUL precheck's own helpers. If they fail, BOTH variables come back empty
  # and `"" != ""` is false — so the gate passes exactly when it could not run.
  printf 'artifact_sha256=%s\n' "$real" > "$prov"
  wc() { return 127; }
  _expect 'wc unavailable -> not a pass' CANNOT-TELL "$md"
  unset -f wc
  _expect 'wc restored' UNCHANGED "$md"

  printf '\nDIRECTORY-MODE control — nothing may leave the denominator silently\n'
  local dd="$d/dirmode"; mkdir -p "$dd"
  cp "$md" "$dd/real.md"; cp "$prov" "$dd/real.provenance"
  ln -s "$dd/real.md" "$dd/linked.md"          # a symlinked .md is still a .md
  printf 'not a round\n' > "$dd/PR-BODY-x.md"  # and so is a non-round file
  # Runs the REAL verify_dir in a subshell (it ends in `exit`, which would otherwise
  # end the self-test) and reads M off its own coverage line — so this exercises the
  # shipped enumeration rather than a second copy of it.
  local out
  out="$( ( verify_dir "$dd" ) 2>/dev/null | sed -n 's/^[0-9]* of \([0-9]*\) verified.*/\1/p' )" || true
  if [[ "$out" == "3" ]]; then
    printf '  ok    %-34s -> 3 of 3 classified\n' 'symlink + non-round counted'
  else
    printf '  FAIL  %-34s -> %s classified, wanted 3\n' 'symlink + non-round counted' "$out"
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
