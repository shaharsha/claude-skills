"""Text that shapes correctly in any direction (Pillow + RAQM), the overlay styles of episode.json,
speaker subtitles, and the chat-poll card."""
import re
from PIL import Image, ImageDraw, ImageFont, features

DIRECTION, LANGUAGE = "ltr", "en"
_fonts = {}


def configure(ep):
    """Call once per process (render workers too) before drawing any text."""
    global DIRECTION, LANGUAGE
    DIRECTION, LANGUAGE = ep.text_dir, ep.text_lang


def require_raqm():
    if not features.check("raqm"):
        raise SystemExit("Pillow was built without RAQM, so Hebrew/Arabic would render reversed and unshaped. "
                         "Install libraqm (macOS: brew install libraqm) and reinstall Pillow "
                         "(pip install --force-reinstall --no-binary pillow pillow), or use a wheel that bundles it.")


def font(path, size):
    k = (path, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
    return _fonts[k]


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in range(0, len(h), 2))


def lum(c):
    return .299 * c[0] + .587 * c[1] + .114 * c[2]


def strip_tags(t):
    return re.sub(r"\s+", " ", re.sub(r"\[[^\]]*\]", "", t)).strip()


def tlen(f, s):
    return f.getlength(s, direction=DIRECTION, language=LANGUAGE)


def wrap(s, f, maxw):
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if tlen(f, t) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def text_layer(lines, f, fill=(255, 255, 255), stroke=0, sfill=(0, 0, 0), spacing=1.15, pad=30):
    """RGBA image with centered lines."""
    lh = int(f.size * spacing)
    w = int(max(tlen(f, l) for l in lines)) + 2 * pad + 2 * stroke
    h = lh * len(lines) + 2 * pad
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        d.text((w // 2, pad + i * lh + lh // 2), l, font=f, fill=fill, anchor="mm", direction=DIRECTION, language=LANGUAGE,
               stroke_width=stroke, stroke_fill=sfill)
    return im


def rounded(size, r, fill):
    m = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], r, fill=fill)
    return m


def pill(lines, f, fg, bg, pad=(34, 18), r=26):
    t = text_layer(lines, f, fill=fg, pad=0)
    im = rounded((t.width + 2 * pad[0], t.height + 2 * pad[1]), r, bg)
    im.alpha_composite(t, (pad[0], pad[1]))
    return im


def band(ep, st, name, stat, color):
    """A character card's slanted name band (ports edit.make_overlay 'band')."""
    W, c = ep.W, rgb(color)[:3]
    b = Image.new("RGBA", (W + 200, 330), (0, 0, 0, 0))
    d = ImageDraw.Draw(b)
    d.polygon([(0, 60), (W + 200, 0), (W + 200, 270), (0, 330)], fill=(15, 15, 25, 235))
    d.polygon([(0, 60), (W + 200, 0), (W + 200, 22), (0, 82)], fill=c + (255,))
    n = text_layer([name], font(ep.font(st.get("name_font", "black")), st.get("name_size", 130)), fill=(255, 255, 255),
                   stroke=8, sfill=c, pad=0)
    sf = font(ep.font(st.get("stat_font", "bold")), st.get("stat_size", 54))
    s = text_layer(wrap(stat, sf, 950), sf, fill=rgb(st.get("stat_fill", "#FFEB78")), pad=0)
    b.alpha_composite(n, ((b.width - n.width) // 2, 60))
    b.alpha_composite(s, ((b.width - s.width) // 2, 60 + n.height + 6))
    return b


def render_style(ep, st, text, color=None):
    """(RGBA layer, (x, y) top-left on the output frame, anim) for one overlay."""
    W, H = ep.W, ep.H
    kind = st.get("kind", "text")
    if kind == "band":
        return band(ep, st, text[0], text[1], color), (-100, st.get("y_top", H - 520)), st.get("anim", "slide")
    if kind == "stack":
        cw, chh = st["canvas"]
        im, y = Image.new("RGBA", (cw, chh), (0, 0, 0, 0)), None
        for item, t in zip(st["items"], text):
            layer = text_layer([t], font(ep.font(item["font"]), item["size"]), fill=rgb(item.get("fill", "#FFFFFF")),
                               stroke=item.get("stroke", 0), sfill=rgb(item.get("stroke_fill", "#000000")),
                               pad=item.get("pad", 0))
            y = item["y"] if y is None else y + item.get("gap", 0)
            im.alpha_composite(layer, ((cw - layer.width) // 2, y))
            y += layer.height
        return im, tuple(st["pos"]), st.get("anim", "pop")
    lines = text if isinstance(text, list) else [text]
    f = font(ep.font(st["font"]), st["size"])
    if "wrap" in st:
        lines = [l for t in lines for l in wrap(t, f, st["wrap"])]
    if "pill" in st:
        im = pill(lines, f, rgb(st.get("fill", "#FFFFFF")), rgb(st["pill"]), tuple(st.get("pill_pad", (34, 18))),
                  st.get("radius", 26))
    else:
        im = text_layer(lines, f, fill=rgb(st.get("fill", "#FFFFFF")), stroke=st.get("stroke", 0),
                        sfill=rgb(st.get("stroke_fill", "#000000")), spacing=st.get("spacing", 1.15), pad=st.get("pad", 30))
    if st.get("rotate"):
        im = im.rotate(st["rotate"], expand=True, resample=Image.BICUBIC)
    if "center" in st:
        cx, cy = int(st["center"][0] * W), int(st["center"][1] * H)
        pos = (cx - im.width // 2, cy - im.height // 2)
    else:
        x = (W - im.width) // 2 if st.get("x", "center") == "center" else st["x"]
        y = st["y_center"] - im.height // 2 if "y_center" in st else st.get("y_top", 0)
        pos = (x, y)
    return im, pos, st.get("anim", "fade")


def poll_layer(ep, st, progress):
    """Chat-app poll card (right-to-left layout); progress 0..1 fills the votes."""
    cw, ch = st.get("w", 900), st.get("h", 640)
    im = rounded((cw, ch), 34, (255, 255, 255, 245))
    d = ImageDraw.Draw(im)
    fT = font(ep.font(st.get("title_font", "hblack")), 52)
    fO = font(ep.font(st.get("option_font", "bold")), 44)
    fS = font(ep.font(st.get("option_font", "bold")), 30)
    kw = dict(anchor="rm", direction=DIRECTION, language=LANGUAGE)
    d.text((cw - 50, 70), st["title"], font=fT, fill=(17, 27, 33), **kw)
    d.text((cw - 50, 125), st["subtitle"], font=fS, fill=(120, 130, 135), **kw)
    total = st["total"]
    for i, (name, n) in enumerate(st["options"]):
        y = 200 + i * 105
        k = n * min(1, progress * 1.15)
        d.ellipse([cw - 82, y - 20, cw - 42, y + 20], outline=(37, 211, 102), width=4)
        if i == 0 and progress > .5:
            d.ellipse([cw - 74, y - 12, cw - 50, y + 12], fill=(37, 211, 102))
        d.text((cw - 105, y), name, font=fO, fill=(17, 27, 33), **kw)
        d.text((60, y), str(int(round(k))), font=fO, fill=(80, 90, 95), anchor="lm")
        d.rounded_rectangle([60, y + 38, cw - 50, y + 50], 6, fill=(225, 230, 232))
        bw = (cw - 110) * (k / total)
        if bw > 2:
            d.rounded_rectangle([cw - 50 - bw, y + 38, cw - 50, y + 50], 6, fill=(37, 211, 102))
    return im


def subtitle_layer(ep, lid, who):
    """Speaker name pill (in the speaker's color) above the line's text, centered near the bottom."""
    S = ep.data.get("subtitle", {})
    text = strip_tags(ep.lines[lid]["text"])
    if not text:  # a line that is only audio tags ("[gasps]") has nothing to show
        return None
    f = font(ep.font(S.get("font", "bold")), S.get("size", 58))
    body = text_layer(wrap(text, f, S.get("wrap", 940)), f, fill=(255, 255, 255), stroke=S.get("stroke", 7), sfill=(0, 0, 0),
                      pad=S.get("pad", 6))
    sp = ep.speakers.get(who, {"display": who, "color": "#FFFFFF"})
    col = rgb(sp.get("color", "#FFFFFF"))[:3]
    fg = (0, 0, 0) if lum(col) > 150 else (255, 255, 255)
    name = pill([sp.get("display", who)], font(ep.font(S.get("name_font", "hblack")), S.get("name_size", 38)), fg, col + (255,),
                tuple(S.get("name_pad", (24, 8))), S.get("name_radius", 20))
    w = max(body.width, name.width)
    im = Image.new("RGBA", (w, name.height + body.height + 4), (0, 0, 0, 0))
    im.alpha_composite(name, ((w - name.width) // 2, 0))
    im.alpha_composite(body, ((w - body.width) // 2, name.height + 4))
    return im, ((ep.W - w) // 2, S.get("bottom", 1560) - name.height)
