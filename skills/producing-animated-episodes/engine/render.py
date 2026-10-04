"""Render each shot to a segment: source image or clip, camera move, fx, overlays and subtitles, frame by frame."""
import hashlib, itertools, json, math, os, random, subprocess
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFilter, ImageOps
import frames as FR
import lipsync as LS
import textlayers as TL
from timeline import FX_TIMES, resolve_time

FFMPEG = "ffmpeg"
STILL = [(0, 1.0, .5, .5), (1, 1.0, .5, .5)]
CLIP_DEFAULT = [(0, 1.0, .5, .5), (1, 1.03, .5, .5)]   # a clip carries its own motion: barely push in


def ease(t):
    return t * t * (3 - 2 * t)


def cam_keys(spec):
    """Keyframes [(u, zoom, cx, cy)], from a list or the shorthands {"in": [z, cx, cy, z0, cx0, cy0]} / {"out": [z0, cx0, cy0]}."""
    if not spec:
        return None
    if isinstance(spec, dict):
        if "in" in spec:
            z, cx, cy, z0, cx0, cy0 = list(spec["in"]) + [1.10, .5, .5, 1.0, .5, .5][len(spec["in"]):]
            return [(0, z0, cx0, cy0), (1, z, cx, cy)]
        if "out" in spec:
            z0, cx0, cy0 = list(spec["out"]) + [1.15, .5, .5][len(spec["out"]):]
            return [(0, z0, cx0, cy0), (1, 1.0, .5, .5)]
        raise ValueError(f"bad cam {spec!r}")
    return [tuple(k) for k in spec]


def cam_at(keys, u):
    for (u0, *a), (u1, *b) in zip(keys, keys[1:]):
        if u <= u1:
            k = ease(0 if u1 == u0 else (u - u0) / (u1 - u0))
            return [x + (y - x) * k for x, y in zip(a, b)]
    return keys[-1][1:]


def with_alpha(im, a):
    if a >= .999:
        return im
    im = im.copy()
    im.putalpha(im.split()[3].point(lambda v: int(v * a)))
    return im


def glow(ep, col, side):
    W, H, c = ep.W, ep.H, TL.rgb(col)
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    for r in range(18, 0, -1):
        a, rad = int(10 * (19 - r)), r * 70
        cy = 0 if side == "top" else H
        d.ellipse([W // 2 - rad, cy - rad, W // 2 + rad, cy + rad], fill=c + (a,))
    return g.filter(ImageFilter.GaussianBlur(60))


def speed_lines(ep, center):
    W, H = ep.W, ep.H
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    cx, cy = center[0] * W, center[1] * H
    rnd = random.Random(3)
    for _ in range(120):
        ang = rnd.uniform(0, 2 * math.pi)
        r0 = rnd.uniform(380, 520); r1 = 1500
        w = rnd.uniform(2, 9)
        d.line([(cx + r0 * math.cos(ang), cy + r0 * math.sin(ang)), (cx + r1 * math.cos(ang), cy + r1 * math.sin(ang))],
               fill=(255, 255, 255, 170), width=int(w))
    return g


def render_shot(args):
    ep, shot, build_dir, lipsync = args
    TL.configure(ep)
    W, H, SW, SH, FPS = ep.W, ep.H, ep.SRC_W, ep.SRC_H, ep.fps
    out = os.path.join(build_dir, "seg", f"{shot['id']}.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    src = FR.shot_image(ep, shot)
    keys = cam_keys(shot.get("cam")) or STILL
    clip = ep.path("clips", f"{shot.get('clip', shot['id'])}.mp4")
    off, speed = shot.get("clip_off", 0), shot.get("clip_speed", 1.0)
    synced = LS.current_final(ep, shot)[0] if lipsync else None
    if synced:  # lip-synced version: already offset, sped and frame-exact
        clip, off, speed = synced, 0, 1.0
    frames, tbase = None, None
    if os.path.exists(clip) and not shot.get("static"):
        if shot["img"].startswith("tablet:"):
            tbase = FR.tablet_base(ep, shot["img"].split(":")[2])
            frames = FR.clip_frames(clip, *FR.screen_size(ep), off, speed, FPS)
        else:
            frames = FR.clip_frames(clip, SW, SH, off, speed, FPS)
        first = next(frames, None)
        if first is None:
            print(f"WARNING: {shot['id']}: {os.path.basename(clip)} gives no frames from {off:g}s "
                  "(clip_off past its end?): using the still", flush=True)
            frames, tbase = None, None
        else:
            frames = itertools.chain([first], frames)
            keys = cam_keys(shot.get("clip_cam")) or CLIP_DEFAULT
    placed = shot["placed"]
    ovs = []  # (layer or poll style, pos, t0, t1, anim)
    for ov in shot.get("overlays", []):
        st = ep.styles[ov["style"]]
        t0 = resolve_time(ov.get("t0", 0), placed)
        t1 = resolve_time(ov["t1"], placed) if ov.get("t1") is not None else shot["dur"]
        if st.get("kind") == "poll":
            ovs.append((st, None, t0, t1, "poll"))
            continue
        im, pos, anim = TL.render_style(ep, st, ov.get("text"), ov.get("color"))
        ovs.append((im, pos, t0, t1, anim))
    for lid, (st_, en) in ({} if shot.get("nosub") else placed).items():
        sub = TL.subtitle_layer(ep, lid, shot.get("who", {}).get(lid, ep.lines[lid]["who"]))
        if sub:
            ovs.append((*sub, st_, en + ep.timing["sub_tail"], "sub"))
    fx = [[f[0], *(resolve_time(v, placed) if i in FX_TIMES.get(f[0], ()) else v for i, v in enumerate(f[1:], 1))]
          for f in shot.get("fx", [])]  # line references (S02-1, E02-1+0.3) become seconds
    speedfx = None
    for f in fx:
        if f[0] == "speed":
            speedfx = speed_lines(ep, f[3])
    glow_layers = {}
    rnd = random.Random(7)
    tmp = out + ".part.mp4"
    ff = subprocess.Popen([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                           "-pix_fmt", "yuv420p", "-r", str(FPS), tmp], stdin=subprocess.PIPE)
    for i in range(shot["nframes"]):
        t = i / FPS
        u = i / max(1, shot["nframes"] - 1)
        if frames is not None:
            nxt = next(frames, None)  # past the clip's end, hold its last frame
            if nxt is not None:
                src = FR.tablet_compose(tbase, nxt) if tbase else nxt
        z, cx, cy = cam_at(keys, u)
        for f in fx:
            if f[0] == "shake":
                t0, t1, amp = f[1], f[2], f[3]
                if t0 <= t <= t1:
                    k = 1 - (t - t0) / (t1 - t0)
                    cx += rnd.uniform(-1, 1) * amp * k / SW
                    cy += rnd.uniform(-1, 1) * amp * k / SH
        cw, ch = SW / z, SH / z
        x0 = min(max(cx * SW - cw / 2, 0), SW - cw)
        y0 = min(max(cy * SH - ch / 2, 0), SH - ch)
        frame = src.transform((W, H), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.BICUBIC)
        for f in fx:
            if f[0] == "desat":
                t0 = f[1]
                if t >= t0:
                    frame = Image.blend(frame, ImageOps.grayscale(frame).convert("RGB"), min(1, (t - t0) / .5))
            elif f[0] == "glow":
                t0, t1, col, side = f[1], f[2], f[3], f[4]
                if t0 <= t <= t1:
                    if side not in glow_layers:
                        glow_layers[side] = glow(ep, col, side)
                    k = math.sin(math.pi * (t - t0) / (t1 - t0))
                    frame = Image.alpha_composite(frame.convert("RGBA"), with_alpha(glow_layers[side], .85 * k)).convert("RGB")
            elif f[0] == "speed":
                t0 = f[1]
                if t >= t0 and speedfx is not None:
                    k = min(1, (t - t0) / .15) * (0.75 + .25 * math.sin(t * 40))
                    frame = Image.alpha_composite(frame.convert("RGBA"), with_alpha(speedfx, k)).convert("RGB")
        frame = frame.convert("RGBA")
        for im, pos, t0, t1, anim in ovs:
            if not (t0 <= t <= t1):
                continue
            a, dy, layer = 1.0, 0, im
            age, left = t - t0, t1 - t
            if anim == "poll":
                layer = TL.poll_layer(ep, im, min(1, age / im.get("fill_seconds", 3.2)))
                pos = ((W - layer.width) // 2, im.get("y_top", 140))
                a = min(1, age / .2)
            elif anim == "pop":
                s = min(1, age / .18)
                sc = .6 + .4 * s + .08 * math.sin(min(1, age / .3) * math.pi)
                layer = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BICUBIC)
                pos = (pos[0] + (im.width - layer.width) // 2, pos[1] + (im.height - layer.height) // 2)
                a = s
            elif anim == "slide":
                k = ease(min(1, age / .12))
                pos = (int(pos[0] + (1 - k) * 600), pos[1])
            elif anim == "write":
                k = min(1, age / 1.6)
                cut = int(im.width * (1 - k))
                layer = im.copy()
                hide = [0, 0, cut, im.height] if ep.text_dir == "rtl" else [im.width - cut, 0, im.width, im.height]
                ImageDraw.Draw(layer).rectangle(hide, fill=(0, 0, 0, 0))   # handwriting appears in reading order
            elif anim in ("fade", "sub"):
                a = min(1, age / (.08 if anim == "sub" else .25))
            if anim != "poll" and left < .12 and t1 < shot["dur"] - .01:
                a *= max(0, left / .12)
            frame.alpha_composite(with_alpha(layer, a), (int(pos[0]), int(pos[1] + dy)))
        frame = frame.convert("RGB")
        for f in fx:
            if f[0] == "flash" and f[1] <= t < f[1] + .25:
                frame = Image.blend(frame, Image.new("RGB", frame.size, (255, 255, 255)), 1 - (t - f[1]) / .25)
            if f[0] == "fadeout" and t > shot["dur"] - f[1]:
                frame = Image.blend(frame, Image.new("RGB", frame.size, (0, 0, 0)), (t - (shot["dur"] - f[1])) / f[1])
        try:
            ff.stdin.write(frame.tobytes())
        except BrokenPipeError:  # ffmpeg died (bad output path, disk full): report it below, not as a pipe error
            break
    try:
        ff.stdin.close()
    except BrokenPipeError:
        pass
    if ff.wait() != 0:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise RuntimeError(f"ffmpeg failed while rendering {shot['id']}")
    os.replace(tmp, out)  # only complete segments ever get the final name
    return shot["id"]


def shot_inputs(ep, shot):
    """Files a shot's frames are made from (a missing file counts too: it may appear later)."""
    img, files = shot["img"], []
    if img.startswith("card:"):
        files.append(ep.path("characters", img[5:] + ".png"))
    elif img.startswith("tablet:"):
        files += [ep.panel(p) for p in img.split(":")[1:]]
    elif img == "collage":
        files += [ep.path("characters", f"{k}.png") for r in ep.data.get("collage", {}).get("rows", []) for k in r["keys"]]
    elif img != "black":
        files.append(ep.panel(img))
    files += [ep.path("clips", f"{shot.get('clip', shot['id'])}.mp4"), ep.path("lipsync", "final", f"{shot['id']}.mp4")]
    return files


def shot_key(ep, shot, lipsync=True):
    """Everything a segment depends on: its spec (not its position), the look settings, its line texts and its input files."""
    spec = {k: v for k, v in shot.items() if k != "start"}
    look = {k: ep.data.get(k) for k in ("styles", "subtitle", "fonts", "text", "video", "tablet", "collage")}
    texts = [ep.lines.get(x.partition("@")[0], {}).get("text") for x in shot.get("lines", [])]
    who = {l: shot.get("who", {}).get(l, ep.lines.get(l, {}).get("who")) for l in shot.get("placed", {})}
    files = [(f, os.path.getmtime(f), os.path.getsize(f)) if os.path.exists(f) else (f, None) for f in shot_inputs(ep, shot)]
    synced = bool(lipsync and LS.current_final(ep, shot)[0])
    blob = json.dumps([spec, look, ep.speakers, texts, who, ep.timing["sub_tail"], files, synced], sort_keys=True,
                      default=str, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def render_all(ep, shots, build_dir, only=None, force=False, lipsync=True, workers=6):
    """Render every segment whose inputs changed since it was made (all with force, or exactly `only`)."""
    seg = os.path.join(build_dir, "seg")
    os.makedirs(seg, exist_ok=True)
    keys = {s["id"]: shot_key(ep, s, lipsync) for s in shots}
    for s in shots:
        if lipsync and LS.current_final(ep, s)[1]:
            print(f"WARNING: {s['id']} lip-sync is stale (its clip, offset, speed, lines or face points changed): using the "
                  f"raw clip until you run `lipsync prep {s['id']}` and `lipsync run {s['id']}`", flush=True)

    def fresh(s):
        out, keyf = os.path.join(seg, f"{s['id']}.mp4"), os.path.join(seg, f"{s['id']}.key")
        return os.path.exists(out) and os.path.exists(keyf) and open(keyf).read() == keys[s["id"]]

    todo = [s for s in shots if (only and s["id"] in only) or (not only and (force or not fresh(s)))]
    done = []
    with Pool(workers) as p:
        for sid in p.imap_unordered(render_shot, [(ep, s, build_dir, lipsync) for s in todo]):
            with open(os.path.join(seg, f"{sid}.key"), "w") as fh:
                fh.write(keys[sid])
            print("rendered", sid, flush=True)
            done.append(sid)
    return done


def concat(shots, build_dir):
    lst = os.path.join(build_dir, "concat.txt")
    with open(lst, "w") as fh:
        fh.write("".join(f"file 'seg/{s['id']}.mp4'\n" for s in shots))
    video = os.path.join(build_dir, "video.mp4")
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", video], check=True)
    return video
