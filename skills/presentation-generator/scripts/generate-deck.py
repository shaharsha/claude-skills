#!/usr/bin/env python3
"""
generate-deck.py — read a deck-plan.json and generate every slide as a 16:9 PNG,
fanning out to N concurrent image-generation jobs (default 4).

Each slide's `image_prompt` is sent to either openai-image.sh or gemini-image.sh
(per the slide's `model` field). The plan's `style_ref` is passed as `--ref` to every
call so style stays locked across the deck.

Usage:
  generate-deck.py --plan deck-plan.json --output-dir ./slides/ [--concurrency 4]
                   [--size 2560x1440] [--quality high] [--dry-run]

Exit codes:
  0  all slides generated successfully
  1  one or more slides failed (others may have succeeded; a per-slide report is printed)
  2  bad arguments / missing plan / missing scripts
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Paths to the image-generation skill's scripts. Keep these absolute so the orchestrator
# works regardless of cwd.
SKILLS_ROOT = Path.home() / ".claude" / "skills"
OPENAI_SCRIPT = SKILLS_ROOT / "image-generation" / "scripts" / "openai-image.sh"
GEMINI_SCRIPT = SKILLS_ROOT / "image-generation" / "scripts" / "gemini-image.sh"


@dataclass
class SlideJob:
    slide_id: str
    role: str
    idea: str
    prompt: str
    output_path: Path
    model: str
    style_ref: Optional[Path]


@dataclass
class SlideResult:
    slide_id: str
    output_path: Path
    success: bool
    duration_s: float
    error: Optional[str] = None


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:48] or "slide"


def build_full_prompt(slide: dict, plan: dict) -> str:
    """Inject the deck-wide style brief into the per-slide image prompt.

    The deck plan has top-level `style_brief` (a paragraph) plus per-slide
    `image_prompt`. We concatenate so every slide bakes the global look in.
    """
    style_brief = plan.get("style_brief", "").strip()
    slide_prompt = slide["image_prompt"].strip()
    if style_brief:
        return f"{slide_prompt}\n\nVisual style (apply to entire image): {style_brief}"
    return slide_prompt


def build_command(job: SlideJob, size: str, quality: str) -> list[str]:
    if job.model == "gemini":
        if not GEMINI_SCRIPT.exists():
            raise FileNotFoundError(f"gemini-image.sh not found at {GEMINI_SCRIPT}")
        cmd = [
            str(GEMINI_SCRIPT),
            "--prompt", job.prompt,
            "--output", str(job.output_path),
            "--aspect", "16:9",
            "--size", "4K",
            "--model", "pro",
        ]
        if job.style_ref:
            cmd += ["--ref", str(job.style_ref)]
        return cmd

    # default: openai gpt-image-2
    if not OPENAI_SCRIPT.exists():
        raise FileNotFoundError(f"openai-image.sh not found at {OPENAI_SCRIPT}")
    cmd = [
        str(OPENAI_SCRIPT),
        "--prompt", job.prompt,
        "--output", str(job.output_path),
        "--size", size,
        "--quality", quality,
        "--background", "opaque",
    ]
    if job.style_ref:
        cmd += ["--ref", str(job.style_ref)]
    return cmd


# Patterns that indicate a transient failure worth one auto-retry.
# Curl exit codes: 6 (DNS), 7 (connect refused), 28 (timeout), 35 (SSL handshake),
# 52 (empty reply), 56 (recv failure / connection reset). HTTP 429/502/503/504 also transient.
_TRANSIENT_PATTERNS = (
    "curl: (6)",
    "curl: (7)",
    "curl: (28)",
    "curl: (35)",
    "curl: (52)",
    "curl: (56)",
    "Connection reset",
    "Recv failure",
    "Could not resolve host",
    "Operation timed out",
    "Connection refused",
    "Empty reply from server",
    "429 Too Many Requests",
    "502 Bad Gateway",
    "503 Service Unavailable",
    "504 Gateway Timeout",
    "Service Unavailable",
    "Gateway Timeout",
    "rate_limit",
    "server_error",
)


def _is_transient(err: str) -> bool:
    if not err:
        return False
    return any(pat in err for pat in _TRANSIENT_PATTERNS)


def _exec_once(cmd: list[str], slide_id: str, t0: float, output_path: Path) -> SlideResult:
    """Single attempt at running the image-gen subprocess. Returns SlideResult."""
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        dt = time.time() - t0
        err = (e.stderr or "").strip().splitlines()[-1] if e.stderr else f"exit {e.returncode}"
        return SlideResult(slide_id, output_path, False, dt, error=err)

    dt = time.time() - t0
    if not output_path.exists():
        return SlideResult(slide_id, output_path, False, dt, error="output file missing")
    return SlideResult(slide_id, output_path, True, dt)


def run_slide(job: SlideJob, size: str, quality: str, dry_run: bool) -> SlideResult:
    t0 = time.time()
    try:
        cmd = build_command(job, size=size, quality=quality)
    except FileNotFoundError as e:
        return SlideResult(job.slide_id, job.output_path, False, 0.0, error=str(e))

    if dry_run:
        print(f"[DRY] slide {job.slide_id}: {' '.join(cmd[:3])} ...", file=sys.stderr)
        return SlideResult(job.slide_id, job.output_path, True, 0.0)

    job.output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[start] slide {job.slide_id} ({job.role}) → {job.output_path.name}", file=sys.stderr)

    result = _exec_once(cmd, job.slide_id, t0, job.output_path)

    # Single auto-retry if the failure looks transient (network blip, rate limit, 5xx).
    # Avoids losing a whole batch when the image API has a momentary hiccup.
    # Permanent failures (bad prompt, content policy, auth) skip the retry.
    if not result.success and _is_transient(result.error or ""):
        print(f"[retry] slide {job.slide_id}: transient error - retrying once after 3s ({result.error})", file=sys.stderr)
        time.sleep(3)
        t1 = time.time()
        result = _exec_once(cmd, job.slide_id, t1, job.output_path)

    if not result.success:
        print(f"[FAIL ] slide {job.slide_id} ({result.duration_s:.1f}s): {result.error}", file=sys.stderr)
        return result

    print(f"[done ] slide {job.slide_id} ({result.duration_s:.1f}s) → {job.output_path}", file=sys.stderr)
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate every slide in a deck plan in parallel.")
    ap.add_argument("--plan", required=True, help="Path to deck-plan.json")
    ap.add_argument("--output-dir", required=True, help="Directory for slide PNGs")
    ap.add_argument("--concurrency", type=int, default=4, help="Max parallel image jobs (default 4)")
    ap.add_argument("--size", default="2560x1440", help="Image size for openai (default 2560x1440 = 16:9)")
    ap.add_argument("--quality", default="high", choices=["low", "medium", "high"])
    ap.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    ap.add_argument("--only", help="Comma-separated slide IDs to render (e.g., '03,07')")
    args = ap.parse_args()

    plan_path = Path(args.plan).resolve()
    if not plan_path.exists():
        print(f"ERROR: deck plan not found: {plan_path}", file=sys.stderr)
        return 2

    with plan_path.open() as f:
        plan = json.load(f)

    slides = plan.get("slides", [])
    if not slides:
        print("ERROR: deck plan has no slides", file=sys.stderr)
        return 2

    style_ref_field = plan.get("style_ref")
    style_ref: Optional[Path] = None
    if style_ref_field:
        style_ref = (plan_path.parent / style_ref_field).resolve() if not Path(style_ref_field).is_absolute() else Path(style_ref_field)
        if not style_ref.exists():
            print(f"WARN: style_ref declared but file missing: {style_ref}. Proceeding without --ref.", file=sys.stderr)
            style_ref = None

    only = set(s.strip() for s in args.only.split(",")) if args.only else None

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    jobs: list[SlideJob] = []
    for slide in slides:
        sid = str(slide["id"])
        if only and sid not in only:
            continue
        slug = slugify(slide.get("role", "slide") + "-" + slide.get("idea", "")[:30])
        out = output_dir / f"slide-{sid}-{slug}.png"
        full_prompt = build_full_prompt(slide, plan)
        jobs.append(SlideJob(
            slide_id=sid,
            role=slide.get("role", "slide"),
            idea=slide.get("idea", ""),
            prompt=full_prompt,
            output_path=out,
            model=slide.get("model", "openai"),
            style_ref=style_ref,
        ))

    if not jobs:
        print("ERROR: no slides matched filter", file=sys.stderr)
        return 2

    print(f"Generating {len(jobs)} slide(s) with concurrency {args.concurrency}...", file=sys.stderr)
    if style_ref:
        print(f"Style lock: --ref {style_ref}", file=sys.stderr)
    else:
        print("Style lock: NONE (no style_ref in plan; slides may drift)", file=sys.stderr)

    t_start = time.time()
    results: list[SlideResult] = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = {ex.submit(run_slide, j, args.size, args.quality, args.dry_run): j for j in jobs}
        for fut in as_completed(futures):
            results.append(fut.result())

    total_dt = time.time() - t_start
    results.sort(key=lambda r: r.slide_id)

    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]

    print("", file=sys.stderr)
    print(f"=== Generation complete in {total_dt:.1f}s ===", file=sys.stderr)
    print(f"  Success: {len(successes)} / {len(results)}", file=sys.stderr)
    if failures:
        print(f"  FAILED:  {len(failures)}", file=sys.stderr)
        for r in failures:
            print(f"    slide {r.slide_id}: {r.error}", file=sys.stderr)
        # Surface a copy-pasteable retry command. Auto-retry already covered transient
        # errors once; remaining failures need either a prompt fix or a manual rerun.
        failed_ids = ",".join(r.slide_id for r in failures)
        print("", file=sys.stderr)
        print(f"  To retry just the failed slides:", file=sys.stderr)
        print(f"    --only {failed_ids}", file=sys.stderr)

    # Print successful slide paths to stdout (one per line) for capture by caller
    for r in successes:
        print(r.output_path)

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
