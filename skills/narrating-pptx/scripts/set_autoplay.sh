#!/bin/bash
# Set every media shape in a pptx to autoplay on slide entry — by letting REAL
# PowerPoint author the timing XML (the only reliable way; hand-written <p:timing>
# XML triggers the repair dialog). macOS + Microsoft PowerPoint required.
# Usage: ./set_autoplay.sh /absolute/path/deck.pptx EXPECTED_SLIDE_COUNT
# File must be under ~/Downloads, ~/Documents or ~/Desktop (PowerPoint sandbox),
# unless PowerPoint has Full Disk Access.
set -euo pipefail
FILE="$1"; SLIDES="$2"; BASE="$(basename "$FILE")"
RESULT=$(osascript <<EOS
tell application "Microsoft PowerPoint"
  activate
  open POSIX file "$FILE"
  -- target the presentation BY NAME (never "presentation 1" — a stale window steals it)
  set thePres to missing value
  repeat 60 times
    delay 1
    try
      set thePres to presentation "$BASE"
      if (count of slides of thePres) is $SLIDES then exit repeat
    end try
  end repeat
  if thePres is missing value then error "presentation $BASE never opened"
  if (count of slides of thePres) is not $SLIDES then error "slide count mismatch: expected $SLIDES got " & (count of slides of thePres)
  set fixedCount to 0
  repeat with i from 1 to (count of slides of thePres)
    repeat with j from 1 to (count of shapes of (slide i of thePres))
      try -- only media shapes accept play settings; others error into the try
        set ps to play settings of animation settings of (shape j of (slide i of thePres))
        set play on entry of ps to true
        set hide while not playing of ps to true
        set fixedCount to fixedCount + 1
      end try
    end repeat
  end repeat
  save thePres
  delay 2
  close thePres
  return "autoplay set on " & fixedCount & " media shapes"
end tell
EOS
)
echo "$RESULT"
# Fail loudly if nothing was set — silence here means click-to-play shipped by accident
case "$RESULT" in *"on 0 media"*) echo "ERROR: no media shapes found" >&2; exit 1;; esac
