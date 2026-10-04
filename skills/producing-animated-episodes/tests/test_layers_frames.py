import os, subprocess
import numpy as np
import pytest
from PIL import Image, ImageDraw
import frames, textlayers as TL
from conftest import hebrew_font


def alpha(im):
    return np.asarray(im.split()[3]).astype(np.int16)


def find(sub, img):
    """(x, y, mean abs diff) of the best placement of sub inside img, compared on alpha."""
    a, s = alpha(img), alpha(sub)
    best = (0, 0, 1e9)
    for y in range(0, a.shape[0] - s.shape[0] + 1):
        for x in range(0, a.shape[1] - s.shape[1] + 1):
            d = np.abs(a[y:y + s.shape[0], x:x + s.shape[1]] - s).mean()
            if d < best[2]:
                best = (x, y, d)
    return best


class Ep:  # minimal stand-in for configure()
    def __init__(self, d, l): self.text_dir, self.text_lang = d, l


def test_raqm_available():
    TL.require_raqm()


def test_rtl_number_first_renders_on_the_right_in_order():
    # bidi: in a right-to-left line the first logical word ("12,345") is rightmost, and its digits keep their order
    TL.configure(Ep("rtl", "he"))
    f = TL.font(hebrew_font(), 48)
    full = TL.text_layer(["12,345 הודעות"], f, pad=0)
    num = TL.text_layer(["12,345"], f, pad=0)
    rev = TL.text_layer(["543,21"], f, pad=0)
    x, y, d = find(num, full)
    assert x > full.width / 2 and d < 12, (x, full.width, d)
    assert find(rev, full)[2] > d + 10          # the reversed digit string matches far worse


def test_ltr_project_keeps_punctuation_order():
    f = TL.font(hebrew_font(), 48)
    TL.configure(Ep("ltr", "en"))
    got = TL.text_layer(["Hello!"], f, pad=0)
    ref = Image.new("RGBA", got.size, (0, 0, 0, 0))
    ImageDraw.Draw(ref).text((got.width // 2, int(f.size * 1.15) // 2), "Hello!", font=f, fill=(255, 255, 255), anchor="mm")
    assert np.array_equal(np.asarray(got), np.asarray(ref))
    TL.configure(Ep("rtl", "he"))
    assert not np.array_equal(np.asarray(TL.text_layer(["Hello!"], f, pad=0)), np.asarray(got))


def test_strip_tags():
    assert TL.strip_tags("[excited] שלום!  [pause] מה") == "שלום! מה"


def test_style_cap_wraps_and_positions(tiny):
    TL.configure(tiny)
    im, pos, anim = TL.render_style(tiny, tiny.styles["cap"], "שורה ארוכה מאוד " * 10)
    one, _, _ = TL.render_style(tiny, tiny.styles["cap"], "קצר")
    assert im.width <= 900 + 68 and im.height > one.height
    assert pos == ((1080 - im.width) // 2, 150) and anim == "fade"


def test_stack_style_positions(tiny):
    TL.configure(tiny)
    f = hebrew_font()
    st = {"kind": "stack", "canvas": [1080, 520], "pos": [0, 90], "anim": "pop",
          "items": [{"font": "black", "size": 100, "y": 20, "pad": 0}, {"font": "bold", "size": 40, "gap": 20, "pad": 0}]}
    im, pos, anim = TL.render_style(tiny, st, ["כותרת", "פרק 1"])
    h1 = TL.text_layer(["כותרת"], TL.font(f, 100), pad=0).height
    a = alpha(im)
    assert im.size == (1080, 520) and pos == (0, 90) and anim == "pop"
    assert a[:20].max() == 0 and a[20 + h1:20 + h1 + 20].max() == 0 and a[20 + h1 + 20:].max() > 0


def test_band_and_subtitle(tiny):
    TL.configure(tiny)
    b = TL.band(tiny, {}, "מאיה", "12,345 הודעות", "#F28C28")
    assert b.size == (1080 + 200, 330)
    im, (x, y) = TL.subtitle_layer(tiny, "02-1", "maya")
    assert im.width <= 1080 and x == (1080 - im.width) // 2 and y < 1560


def test_poll_layer_fills(tiny):
    TL.configure(tiny)
    st = {"kind": "poll", "title": "מי?", "subtitle": "בחרו", "options": [["מאיה", 3], ["עידו", 1]], "total": 4}
    a, b = TL.poll_layer(tiny, st, 0.0), TL.poll_layer(tiny, st, 1.0)
    assert a.size == (900, 640) and not np.array_equal(np.asarray(a), np.asarray(b))


def card(path, bg=(242, 140, 40)):
    im = Image.new("RGB", (300, 400), bg)
    ImageDraw.Draw(im).ellipse([100, 80, 200, 380], fill=(30, 30, 30))
    im.save(path)


def test_cutout_removes_flat_background(tmp_path):
    card(tmp_path / "c.png")
    out = frames.cutout(Image.open(tmp_path / "c.png"))
    assert out.getpixel((5, 5))[3] == 0 and out.getpixel((150, 300))[3] == 255


def test_collage_without_faces_renders(tiny):
    os.makedirs(tiny.path("characters"), exist_ok=True)
    for k in ("maya", "ido"):
        card(tiny.path("characters", f"{k}.png"))
    tiny.data["collage"] = {"rows": [{"keys": ["maya", "ido"], "h": 760, "y": 560}]}
    im = frames.collage_image(tiny)
    assert im.size == (1152, 2048) and im.getpixel((0, 0)) == (255, 150, 70)


def test_tablet_image_geometry(tiny):
    os.makedirs(tiny.path("panels_final"), exist_ok=True)
    Image.new("RGB", (1152, 2048), (255, 0, 0)).save(tiny.path("panels_final", "p01.png"))
    Image.new("RGB", (1152, 2048), (0, 0, 255)).save(tiny.path("panels_final", "p02.png"))
    im = frames.tablet_image(tiny, "p01", "p02")
    r, g, b = im.getpixel((576, 1000))
    r2, g2, b2 = im.getpixel((5, 5))
    assert im.size == (1152, 2048) and r > 200 and b < 50 and b2 > r2


def test_clip_frames_scale_and_count(tmp_path):
    p = tmp_path / "c.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=144x256:rate=24",
                    "-frames:v", "48", "-pix_fmt", "yuv420p", str(p)], check=True)
    fr = list(frames.clip_frames(str(p), 72, 128, 0, 1.0, 24))
    assert len(fr) == 48 and fr[0].size == (72, 128)
    assert len(list(frames.clip_frames(str(p), 72, 128, 1.0, 1.0, 24))) == 24


def test_tag_only_line_has_no_subtitle(tiny):
    TL.configure(tiny)
    tiny.lines["01-1"]["text"] = "[gasps]"
    assert TL.subtitle_layer(tiny, "01-1", "maya") is None


def test_rgba_character_colors_do_not_crash(tiny):
    TL.configure(tiny)
    TL.band(tiny, {}, "מאיה", "שופטת", "#E0218A80")
    tiny.speakers["maya"]["color"] = "#F28C2880"
    im, pos = TL.subtitle_layer(tiny, "02-1", "maya")
    assert im.width > 0


def test_speaker_without_display_name_has_no_name_pill(tiny):
    TL.configure(tiny)
    with_name, _ = TL.subtitle_layer(tiny, "02-1", "maya")
    tiny.speakers["narrator"] = {"display": None, "voice": "VN"}
    without, _ = TL.subtitle_layer(tiny, "02-1", "narrator")
    assert without.height < with_name.height - 30              # the text alone, no pill above it
