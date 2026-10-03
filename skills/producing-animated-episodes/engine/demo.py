"""A tiny fictional episode with synthetic assets (no API calls). `episode.py DIR demo` writes it; the smoke test
builds it end to end. Its config is templates/episode.example.json with fonts filled in."""
import json, os, subprocess
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLE = os.path.join(os.path.dirname(HERE), "templates", "episode.example.json")
FONT_CANDIDATES = ["~/Library/Fonts/Heebo-Bold.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
                   "/Library/Fonts/Arial Unicode.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def find_font():
    for f in FONT_CANDIDATES:
        p = os.path.expanduser(f)
        if os.path.exists(p):
            return p
    raise SystemExit("no Hebrew-capable font found: set 'fonts' in episode.json")


def _ff(*a):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *a], check=True)


def _panel(path, top, bottom, shapes):
    im = Image.new("RGB", (1152, 2048))
    d = ImageDraw.Draw(im)
    for y in range(2048):
        k = y / 2048
        d.line([(0, y), (1152, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(top, bottom)))
    for box, color in shapes:
        d.rounded_rectangle(box, 40, fill=color)
    im.save(path)


def _card(path, bg, shirt):
    im = Image.new("RGB", (1024, 1536), bg)
    d = ImageDraw.Draw(im)
    d.ellipse([382, 220, 642, 520], fill=(236, 200, 170))        # head
    d.rounded_rectangle([262, 560, 762, 1536], 120, fill=shirt)   # body
    im.save(path)


def write_demo(dest):
    root = os.path.join(os.path.abspath(dest), "demo-episode")
    for sub in ("panels/final", "characters/final", "audio/lines", "audio/music", "audio/sfx"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    cfg = json.load(open(EXAMPLE, encoding="utf-8"))
    f = find_font()
    cfg["fonts"] = {k: f for k in ("black", "hblack", "bold", "hand")}
    json.dump(cfg, open(os.path.join(root, "episode.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    _panel(os.path.join(root, "panels/final/p01.png"), (70, 50, 90), (230, 140, 80),
           [([150, 1300, 1000, 1500], (210, 180, 140)), ([380, 1150, 780, 1300], (240, 220, 200))])
    _panel(os.path.join(root, "panels/final/p02s.png"), (30, 120, 160), (20, 40, 60), [([300, 500, 850, 1200], (236, 200, 170))])
    _card(os.path.join(root, "characters/final/maya.png"), (224, 33, 138), (200, 30, 40))
    _card(os.path.join(root, "characters/final/ido.png"), (36, 80, 216), (40, 140, 70))
    for lid, sec, hz in (("01-1", 1.6, 330), ("02-1", 0.6, 440), ("02-2", 0.7, 260), ("03-1", 1.9, 300)):
        _ff("-f", "lavfi", "-i", f"sine=frequency={hz}:duration={sec}", "-ar", "44100", os.path.join(root, f"audio/lines/{lid}.mp3"))
    _ff("-f", "lavfi", "-i", "sine=frequency=220:duration=16", "-af", "volume=0.3", os.path.join(root, "audio/music/theme.mp3"))
    _ff("-f", "lavfi", "-i", "anoisesrc=d=0.6:c=pink", "-af", "afade=t=out:st=0.2:d=0.4", os.path.join(root, "audio/sfx/whoosh.mp3"))
    return root
