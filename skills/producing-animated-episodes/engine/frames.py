"""Shot source images (panels, character cards, black, tablet composites, the group collage) and clip readers."""
import os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from textlayers import rounded

FFMPEG = "ffmpeg"
TABLET = {"w": 980, "h": 1500, "blur": 28, "dim": 0.45, "dim_color": [10, 12, 20], "radius": 60, "inset": 28,
          "screen_radius": 40, "lift": 40}
_cache, _warned = {}, False


def load_rgb(path):
    if path not in _cache:
        if not os.path.exists(path):
            raise FileNotFoundError(f"missing image {path}")
        _cache[path] = Image.open(path).convert("RGB")
    return _cache[path]


def cover(im, w, h):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def tablet(ep):
    return {**TABLET, **ep.data.get("tablet", {})}


def screen_size(ep):
    T = tablet(ep)
    return T["w"] - 2 * T["inset"], T["h"] - 2 * T["inset"]


def tablet_base(ep, bgpid):
    """Blurred, dimmed room + tablet bezel; returns (RGBA base, screen top-left, rounded screen mask)."""
    T, SW, SH = tablet(ep), ep.SRC_W, ep.SRC_H
    tw, th = T["w"], T["h"]
    bg = cover(load_rgb(ep.panel(bgpid)), SW, SH).filter(ImageFilter.GaussianBlur(T["blur"]))
    bg = Image.blend(bg, Image.new("RGB", bg.size, tuple(T["dim_color"])), T["dim"]).convert("RGBA")
    x0, y0 = (SW - tw) // 2, (SH - th) // 2 - T["lift"]
    shadow = rounded((tw + 40, th + 40), 70, (0, 0, 0, 160)).filter(ImageFilter.GaussianBlur(25))
    bg.alpha_composite(shadow, (x0 - 20, y0 + 10))
    bg.alpha_composite(rounded((tw, th), T["radius"], (18, 18, 22, 255)), (x0, y0))
    ImageDraw.Draw(bg).ellipse([SW // 2 - 7, y0 + 10, SW // 2 + 7, y0 + 24], fill=(45, 45, 52))
    mask = rounded(screen_size(ep), T["screen_radius"], (255, 255, 255, 255)).split()[3]
    return bg, (x0 + T["inset"], y0 + T["inset"]), mask


def tablet_compose(base, screen):
    bg, pos, mask = base
    out = bg.copy()
    out.paste(screen.convert("RGBA"), pos, mask)
    return out.convert("RGB")


def tablet_image(ep, av, bgpid):
    return tablet_compose(tablet_base(ep, bgpid), cover(load_rgb(ep.panel(av)), *screen_size(ep)))


def clip_frames(path, w, h, off=0, speed=1.0, fps=24):
    """RGB frames of a clip from `off` seconds (slowed by `speed`), scaled to cover w x h, at fps."""
    p = subprocess.Popen([FFMPEG, "-hide_banner", "-loglevel", "quiet", "-ss", f"{off:.3f}", "-i", path, "-vf",
                          f"setpts=PTS*{speed},scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h},fps={fps}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = w * h * 3
    try:
        while True:
            b = p.stdout.read(n)
            if len(b) < n:
                break
            yield Image.frombytes("RGB", (w, h), b)
    finally:  # the shot may end before the clip does: stop the decoder quietly
        p.stdout.close(); p.kill(); p.wait()


def cutout(card):
    """Remove a card's flat backdrop by flood-filling from the border (pure PIL + numpy)."""
    a = np.asarray(card.convert("RGB").filter(ImageFilter.GaussianBlur(3))).astype(np.int16)  # blur away render grain
    edge = np.concatenate([a[:8, :].reshape(-1, 3), a[:, :8].reshape(-1, 3), a[:, -8:].reshape(-1, 3)])
    bg = np.median(edge, axis=0)
    close = Image.fromarray(((np.abs(a - bg).sum(axis=2) < 95) * 255).astype(np.uint8)).copy()  # copy: floodfill needs a writable buffer
    w, h = close.size
    seeds = [(x, 0) for x in range(0, w, 24)] + [(0, y) for y in range(0, h, 24)] + [(w - 1, y) for y in range(0, h, 24)]
    for s in seeds:
        if close.getpixel(s) == 255:
            ImageDraw.floodfill(close, s, 128)
    bgmask = np.asarray(close) == 128
    alpha = Image.fromarray(((~bgmask) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    out = card.convert("RGBA"); out.putalpha(alpha)
    return out


def face_box(card):
    """(top, height) of the largest frontal face on a card, or None (also when OpenCV is missing)."""
    global _warned
    try:
        import cv2
    except ImportError:
        if not _warned:
            print("WARNING: OpenCV missing - group-shot faces are not size-equalized (pip install opencv-python-headless)")
            _warned = True
        return None
    g = cv2.cvtColor(np.asarray(card.convert("RGB")), cv2.COLOR_RGB2GRAY)
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    f = casc.detectMultiScale(g, 1.1, 5, minSize=(80, 80))
    if len(f) == 0:  # the strict pass misses some drawn faces: retry leniently
        f = casc.detectMultiScale(g, 1.05, 3, minSize=(80, 80))
    if len(f) == 0:
        return None
    x, y, w, h = max(f, key=lambda r: r[2] * r[3])
    return y, h


def collage_image(ep):
    """Group shot: cut-out cards in overlapping rows on a gradient, back row first; each card scaled so its face
    matches the row's median face size, and faces aligned on one line."""
    C = ep.data["collage"]
    SW, SH = ep.SRC_W, ep.SRC_H
    bg = Image.new("RGB", (SW, SH))
    d = ImageDraw.Draw(bg)
    top, bot = C.get("gradient_top", [255, 150, 70]), C.get("gradient_bottom", [185, 110, 180])
    for y in range(SH):
        k = y / SH
        d.line([(0, y), (SW, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(top, bot)))
    bg = bg.convert("RGBA")
    card_h = C.get("card_h", 1536)
    lo, hi = C.get("scale_clamp", [0.75, 1.25])
    margin = C.get("margin", 20)
    for row in C["rows"]:
        keys, h, y, dx = row["keys"], row["h"], row["y"], row.get("dx", 0)
        cards = {k: load_rgb(ep.path("characters", f"{k}.png")) for k in keys}
        faces = {k: face_box(c) for k, c in cards.items()}
        found = [fb for fb in faces.values() if fb]
        base = h / card_h
        med_h = float(np.median([fb[1] for fb in found])) * base if found else None
        med_c = float(np.median([fb[0] + fb[1] / 2 for fb in found])) * base if found else h * 0.3
        step = (SW - 2 * margin) / len(keys)
        for i, k in enumerate(keys):
            c, fb = cutout(cards[k]), faces[k]
            s = min(hi, max(lo, med_h / (fb[1] * base))) if (fb and med_h) else 1.0
            hh = int(h * s)
            c = c.resize((int(c.width * hh / c.height), hh), Image.LANCZOS)
            if k in C.get("mirror", []):  # a raised hand or prop would cover a neighbor's face
                c = ImageOps.mirror(c)
            x = int(margin + (i + .5) * step - c.width / 2 + dx)
            fc = (fb[0] + fb[1] / 2) * hh / card_h if fb else med_c
            bg.alpha_composite(c, (x, int(y + med_c - fc)))
    return bg.convert("RGB")


def shot_image(ep, spec):
    img = spec["img"]
    if img == "black":
        return Image.new("RGB", (ep.SRC_W, ep.SRC_H), (0, 0, 0))
    if img == "collage":
        return collage_image(ep)
    if img.startswith("card:"):
        return cover(load_rgb(ep.path("characters", img[5:] + ".png")), ep.SRC_W, ep.SRC_H)
    if img.startswith("tablet:"):
        _, av, bgp = img.split(":")
        return tablet_image(ep, av, bgp)
    return cover(load_rgb(ep.panel(img)), ep.SRC_W, ep.SRC_H)
