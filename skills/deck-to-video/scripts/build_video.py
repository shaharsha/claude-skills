#!/usr/bin/env python3
"""Build a self-playing slide video: each slide shows for its narration's length, then advances.

Usage:
  build_video.py SLIDES AUDIO_DIR OUT.mp4 [options]

  SLIDES     a .pdf (rasterized at --dpi via pdftoppm) OR a directory of images
             (sorted by name; one per slide)
  AUDIO_DIR  per-slide audio named slide01.mp3, slide02.mp3, ... (.mp3/.m4a/.wav)
             count MUST equal slide count

Options:
  --size WxH       output resolution (default 1920x1080; both must be even for yuv420p)
  --dpi N          PDF rasterization dpi (default 200 — text stays crisp at 1080p)
  --pad SECONDS    silence/hold after each narration before advancing (default 0.7)
  --no-bar         skip the per-slide progress bar + countdown overlay
  --no-counter     skip the "N / M" slide counter (drawn top-right)
  --bar-color HEX  progress fill color (default 2E6BFF)
  --crf N          x264 quality (default 20)

Why frames are baked with PIL instead of ffmpeg drawbox/drawtext (paid for in blood):
  - drawbox width expressions using `t` are evaluated ONCE in several ffmpeg builds,
    silently rendering a FULL bar from frame 0. The bug is invisible unless you
    extract frames at early/mid/late timestamps and look.
  - Homebrew ffmpeg bottles (2026+) are built WITHOUT libfreetype: no drawtext at all.
  Baking one frame per second with PIL sidesteps both, encodes cheaper (1 fps input,
  30 fps output on a static image), and is deterministic/testable.
"""
import argparse, json, math, os, re, shutil, subprocess, sys, tempfile

def natural_key(s):
    # numeric-aware sort so s10 comes after s2 (lexicographic order would break slide order)
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", os.path.basename(s))]

def find_ffmpeg():
    for cand in ("ffmpeg", "static_ffmpeg", os.path.expanduser("~/.local/bin/static_ffmpeg")):
        path = shutil.which(cand) if not cand.startswith("/") else (cand if os.path.exists(cand) else None)
        if path:
            return path
    sys.exit("no ffmpeg found — install one (e.g. `uv tool install static-ffmpeg`)")

def find_ffprobe():
    for cand in ("ffprobe", "static_ffprobe", os.path.expanduser("~/.local/bin/static_ffprobe")):
        path = shutil.which(cand) if not cand.startswith("/") else (cand if os.path.exists(cand) else None)
        if path:
            return path
    sys.exit("no ffprobe found")

def audio_duration(ffprobe, path):
    out = subprocess.check_output([ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", path])
    return float(json.loads(out)["format"]["duration"])

def load_font(size):
    from PIL import ImageFont
    for p in ("/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return None  # countdown text skipped; bar still drawn

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slides"); ap.add_argument("audio_dir"); ap.add_argument("out")
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--pad", type=float, default=0.7)
    ap.add_argument("--no-bar", action="store_true")
    ap.add_argument("--no-counter", action="store_true")
    ap.add_argument("--bar-color", default="2E6BFF")
    ap.add_argument("--crf", type=int, default=20)
    args = ap.parse_args()

    from PIL import Image, ImageDraw
    W, H = (int(v) for v in args.size.lower().split("x"))
    if W % 2 or H % 2:
        sys.exit(f"--size {W}x{H}: both dimensions must be even (yuv420p requirement)")
    ff, ffprobe = find_ffmpeg(), find_ffprobe()
    work = tempfile.mkdtemp(prefix="deck2video_")

    # --- collect slide images ---
    if args.slides.lower().endswith(".pdf"):
        if not shutil.which("pdftoppm"):
            sys.exit("pdftoppm (poppler) required to rasterize a PDF — `brew install poppler`")
        subprocess.run(["pdftoppm", "-jpeg", "-r", str(args.dpi), "-jpegopt", "quality=92",
                        args.slides, os.path.join(work, "slide")], check=True)
        images = sorted((os.path.join(work, f) for f in os.listdir(work) if f.endswith(".jpg")),
                        key=natural_key)
    else:
        exts = (".jpg", ".jpeg", ".png")
        images = sorted((os.path.join(args.slides, f) for f in os.listdir(args.slides)
                         if f.lower().endswith(exts)), key=natural_key)
    if not images:
        sys.exit("no slide images found")
    out_parent = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_parent, exist_ok=True)

    # --- collect audio, enforce 1:1 ---
    audio = []
    for i in range(1, len(images) + 1):
        for ext in (".mp3", ".m4a", ".wav"):
            p = os.path.join(args.audio_dir, f"slide{i:02d}{ext}")
            if os.path.exists(p):
                audio.append(p); break
        else:
            sys.exit(f"missing audio for slide {i} (expected {args.audio_dir}/slide{i:02d}.mp3) — "
                     f"found {len(images)} slides; audio count must match")

    # --- geometry for the progress overlay (bottom-right) ---
    BW, BH = int(W * 0.125), max(4, int(H * 0.0074))       # ~240x8 at 1080p
    BX, BY = W - BW - int(W * 0.021), H - BH - int(H * 0.013)
    fill_rgb = tuple(int(args.bar_color[j:j+2], 16) for j in (0, 2, 4))
    font = load_font(max(12, int(H * 0.0213)))

    segs, total = [], 0.0
    for i, (img_path, aud_path) in enumerate(zip(images, audio), start=1):
        dur = audio_duration(ffprobe, aud_path)
        seg_dur = round(dur + args.pad, 3)
        total += seg_dur
        base = Image.open(img_path).convert("RGB").resize((W, H), Image.LANCZOS)
        if font and not args.no_counter:
            # "N / M" top-right — mid-gray reads on light and dark slides alike
            cd = ImageDraw.Draw(base)
            label = f"{i} / {len(images)}"
            tw = cd.textbbox((0, 0), label, font=font)[2]
            cd.text((W - int(W * 0.021) - tw, int(H * 0.022)), label, font=font,
                    fill=(138, 147, 166))
        seqdir = os.path.join(work, f"seq{i:02d}"); os.makedirs(seqdir)
        for sec in range(math.ceil(seg_dur)):
            fr = base.copy()
            if not args.no_bar:
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                d = ImageDraw.Draw(ov)
                d.rectangle([BX, BY, BX + BW, BY + BH], fill=(138, 147, 166, 90))
                fillw = int(BW * min((sec + 0.5) / dur, 1.0))
                if fillw > 0:
                    d.rectangle([BX, BY, BX + fillw, BY + BH], fill=fill_rgb + (242,))
                if font:
                    label = f"{max(0, math.ceil(dur - sec))}s"
                    tw = d.textbbox((0, 0), label, font=font)[2]
                    d.text((BX - 14 - tw, BY - int(H * 0.0111)), label, font=font,
                           fill=(138, 147, 166, 255))
                fr.paste(ov, (0, 0), ov)
            fr.save(os.path.join(seqdir, f"f{sec:03d}.jpg"), quality=90)
        seg = os.path.join(work, f"seg{i:02d}.mp4")
        r = subprocess.run([ff, "-y", "-loglevel", "error",
            "-framerate", "1", "-i", os.path.join(seqdir, "f%03d.jpg"),
            "-i", aud_path, "-af", f"apad=pad_dur={args.pad}",
            "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
            "-tune", "stillimage", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
            "-t", str(seg_dur), seg], capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"slide {i} encode failed:\n{r.stderr[-800:]}")
        segs.append(seg)
        print(f"slide {i:02d}: {seg_dur:.1f}s", flush=True)

    concat = os.path.join(work, "concat.txt")
    with open(concat, "w") as f:
        f.writelines(f"file '{s}'\n" for s in segs)
    r = subprocess.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", concat, "-c", "copy", "-movflags", "+faststart", args.out],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"concat failed:\n{r.stderr[-800:]}")

    got = audio_duration(ffprobe, args.out)
    ok = abs(got - total) < 2.0
    print(f"\n{args.out}: {got/60:.1f} min ({len(segs)} slides) — "
          f"{'duration matches segment sum' if ok else f'WARNING: expected {total/60:.1f} min'}")
    shutil.rmtree(work, ignore_errors=True)
    if not ok:
        sys.exit(1)

if __name__ == "__main__":
    main()
