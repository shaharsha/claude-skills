#!/usr/bin/env python3
"""
lock-style.py — generate 1-2 abstract reference frames from a deck plan's `style_brief`,
to pin the deck's global visual style. The chosen reference is then passed to every
slide generation via --ref so the deck reads as one coherent artifact.

Usage:
  lock-style.py --plan deck-plan.json --output-dir ./refs/ [--n 2] [--size 2560x1440]

The script generates `n` candidate refs by calling openai-image.sh with the style brief
(no slide-level prompts). Claude is then expected to read both with the Read tool, pick
the strongest, and write its path back into deck-plan.json under `style_ref`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SKILLS_ROOT = Path.home() / ".claude" / "skills"
OPENAI_SCRIPT = SKILLS_ROOT / "image-generation" / "scripts" / "openai-image.sh"

REF_PROMPT_TEMPLATE = """A single abstract style reference frame for a 16:9 widescreen presentation deck.
This image will not contain any literal slide content; it is a STYLE BRIEF anchor that
defines the deck's overall aesthetic, palette, and visual motif.

Deck title: {title}
Aesthetic: {aesthetic}
Palette (use these hex colors and only these): {palette_str}
Recurring visual motif: {motif}

Style brief (this is the single most important constraint — apply rigorously):
{style_brief}

Composition: balanced, full-bleed, no white margins. No words, no letters, no numbers,
no text, no logos, no watermarks. Pure visual atmosphere — show the look and feel
that every slide in this deck will share."""


def build_ref_prompt(plan: dict) -> str:
    palette = plan.get("palette") or []
    palette_str = ", ".join(palette) if palette else "(no palette specified — pick a coherent one)"
    return REF_PROMPT_TEMPLATE.format(
        title=plan.get("title", "(untitled deck)"),
        aesthetic=plan.get("aesthetic", "(unspecified)"),
        palette_str=palette_str,
        motif=plan.get("motif", "(no recurring motif specified)"),
        style_brief=plan.get("style_brief", "(no style brief — fill in deck-plan.json)").strip(),
    )


def generate_one_ref(idx: int, prompt: str, output_path: Path, size: str, quality: str) -> tuple[int, Path, bool, str]:
    cmd = [
        str(OPENAI_SCRIPT),
        "--prompt", prompt,
        "--output", str(output_path),
        "--size", size,
        "--quality", quality,
        "--background", "opaque",
    ]
    print(f"[start] ref {idx} → {output_path.name}", file=sys.stderr)
    t0 = time.time()
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        err = (e.stderr or "").strip().splitlines()[-1] if e.stderr else f"exit {e.returncode}"
        print(f"[FAIL ] ref {idx}: {err}", file=sys.stderr)
        return idx, output_path, False, err
    dt = time.time() - t0
    if not output_path.exists():
        return idx, output_path, False, "output file missing"
    print(f"[done ] ref {idx} ({dt:.1f}s) → {output_path}", file=sys.stderr)
    return idx, output_path, True, ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate style reference frames for a deck.")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--n", type=int, default=2, help="Number of reference candidates (default 2)")
    ap.add_argument("--size", default="2560x1440")
    ap.add_argument("--quality", default="high", choices=["low", "medium", "high"])
    args = ap.parse_args()

    plan_path = Path(args.plan).resolve()
    if not plan_path.exists():
        print(f"ERROR: plan not found: {plan_path}", file=sys.stderr)
        return 2
    with plan_path.open() as f:
        plan = json.load(f)

    if not OPENAI_SCRIPT.exists():
        print(f"ERROR: openai-image.sh not found at {OPENAI_SCRIPT}", file=sys.stderr)
        return 2

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    prompt = build_ref_prompt(plan)
    print("=== Style brief prompt being sent for refs ===", file=sys.stderr)
    print(prompt, file=sys.stderr)
    print("=" * 50, file=sys.stderr)

    # Generate refs concurrently — small N, but no reason to serialize
    results: list[tuple[int, Path, bool, str]] = []
    with ThreadPoolExecutor(max_workers=min(args.n, 4)) as ex:
        futures = []
        for i in range(1, args.n + 1):
            ref_path = out_dir / f"style-ref-{i}.png"
            futures.append(ex.submit(generate_one_ref, i, prompt, ref_path, args.size, args.quality))
        for fut in as_completed(futures):
            results.append(fut.result())

    results.sort(key=lambda r: r[0])
    successes = [r for r in results if r[2]]
    failures = [r for r in results if not r[2]]

    print("", file=sys.stderr)
    print(f"=== Style refs: {len(successes)}/{len(results)} succeeded ===", file=sys.stderr)
    for r in failures:
        print(f"  FAILED ref {r[0]}: {r[3]}", file=sys.stderr)

    # Print successful ref paths to stdout for capture
    for r in successes:
        print(r[1])

    if not successes:
        print("", file=sys.stderr)
        print("No style refs generated. Slides will be unlocked (style may drift).", file=sys.stderr)
        return 1

    print("", file=sys.stderr)
    print("Next steps:", file=sys.stderr)
    print("  1. Read each generated PNG with the Read tool.", file=sys.stderr)
    print("  2. Pick the strongest one.", file=sys.stderr)
    print(f"  3. Set deck-plan.json's `style_ref` field to its path (relative to {plan_path.parent} or absolute).", file=sys.stderr)
    print("  4. Run generate-deck.py.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
