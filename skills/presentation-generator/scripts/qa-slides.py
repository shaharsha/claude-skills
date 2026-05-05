#!/usr/bin/env python3
"""
qa-slides.py — mechanical QA pass over generated slides.

This catches the cheap-to-detect failures (missing files, wrong dimensions, suspiciously
small file size, all-black or all-white frames) so Claude can focus its multimodal QA on
the harder visual judgments.

Usage:
  qa-slides.py --plan deck-plan.json --slides-dir ./slides/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageStat
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow", file=sys.stderr)
    sys.exit(2)


# Tolerance for 16:9 aspect (allow tiny rounding error from generators)
TARGET_ASPECT = 16 / 9
ASPECT_TOLERANCE = 0.02
MIN_FILE_BYTES = 50 * 1024  # 50KB — anything smaller is almost certainly a generation failure


def find_slide_png(slides_dir: Path, slide_id: str) -> Path | None:
    matches = sorted(slides_dir.glob(f"slide-{slide_id}-*.png"))
    if not matches:
        matches = sorted(slides_dir.glob(f"slide-{slide_id}*.png"))
    return matches[0] if matches else None


def check_slide(slide_id: str, png: Path) -> list[str]:
    issues: list[str] = []

    if not png.exists():
        return ["FILE MISSING"]

    size_bytes = png.stat().st_size
    if size_bytes < MIN_FILE_BYTES:
        issues.append(f"file size {size_bytes}B < {MIN_FILE_BYTES}B (likely failed generation)")

    try:
        with Image.open(png) as im:
            w, h = im.size
            aspect = w / h if h else 0
            if abs(aspect - TARGET_ASPECT) > ASPECT_TOLERANCE:
                issues.append(f"aspect {w}×{h} ({aspect:.3f}) is not 16:9 ({TARGET_ASPECT:.3f})")

            # Sample mean luminance — flag pure-black or pure-white frames as broken
            gray = im.convert("L")
            stat = ImageStat.Stat(gray)
            mean = stat.mean[0]
            if mean < 5:
                issues.append(f"mean luminance {mean:.1f} (near-black — likely broken)")
            elif mean > 250:
                issues.append(f"mean luminance {mean:.1f} (near-white — likely broken)")

            # Variance: flat-color slides have very low std-dev
            stddev = stat.stddev[0]
            if stddev < 5:
                issues.append(f"std-dev {stddev:.1f} (visually flat — possibly broken)")
    except Exception as e:
        issues.append(f"PIL could not open: {e}")

    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description="Mechanical QA over generated slide PNGs.")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--slides-dir", required=True)
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable")
    args = ap.parse_args()

    plan_path = Path(args.plan).resolve()
    slides_dir = Path(args.slides_dir).resolve()

    with plan_path.open() as f:
        plan = json.load(f)

    slides = plan.get("slides", [])
    if not slides:
        print("ERROR: no slides in plan", file=sys.stderr)
        return 2

    report = []
    fail_count = 0
    for s in slides:
        sid = str(s["id"])
        png = find_slide_png(slides_dir, sid)
        path_str = str(png) if png else None
        if png is None:
            issues = ["FILE MISSING"]
        else:
            issues = check_slide(sid, png)
        if issues:
            fail_count += 1
        report.append({
            "id": sid,
            "role": s.get("role", ""),
            "idea": s.get("idea", ""),
            "path": path_str,
            "issues": issues,
            "ok": not issues,
        })

    if args.json:
        print(json.dumps({"slides": report, "fail_count": fail_count}, indent=2))
    else:
        print(f"=== QA report: {len(report) - fail_count}/{len(report)} slides clean ===")
        for r in report:
            sid = r["id"]
            if r["ok"]:
                print(f"  ✓ slide {sid} ({r['role']})")
            else:
                print(f"  ✗ slide {sid} ({r['role']}): {'; '.join(r['issues'])}")
        if fail_count:
            print("")
            print(f"{fail_count} slide(s) flagged. Re-read each PNG with the Read tool")
            print("for visual review, then regenerate the failures with refined prompts.")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
