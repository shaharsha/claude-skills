"""Lip-sync for an episode: one speaker per part, a face point per part, Sync 3 on fal, frame-exact joins.
The renderer uses <lipsync>/final/<shot>.mp4 (already offset, sped and frame-exact) instead of the raw clip."""
import json, os, subprocess, sys
from PIL import Image, ImageDraw
import generate as G


def _parts_mod():
    return G._module("generating-video-clips", "lipsync_parts.py")


def shot_specs(ep, shots):
    L = ep.data.get("lipsync", {})
    skip = {tuple(x) for x in L.get("skip", [])}
    by = {s["id"]: s for s in shots}
    out = []
    for sid in L.get("shots", []):
        s = by[sid]
        lines = [{"id": lid, "audio": ep.line_audio(lid), "start": st, "end": en,
                  "speaker": s.get("who", {}).get(lid, ep.lines[lid]["who"]), "skip": (sid, lid) in skip}
                 for lid, (st, en) in s["placed"].items()]
        out.append({"id": sid, "video": ep.path("lipsync", "parts", f"{sid}_full.mp4"), "fps": ep.fps,
                    "frames": s["nframes"], "size": "x".join(map(str, ep.video["clip_size"])), "lines": lines,
                    "clip": ep.path("clips", f"{s.get('clip', sid)}.mp4"), "off": s.get("clip_off", 0),
                    "speed": s.get("clip_speed", 1.0)})
    return out


def plan_parts(ep, shots):
    cuts = _parts_mod().cuts
    return [{"shot": sp["id"], "k": k, "line": l["id"], "who": l["speaker"], "f0": f0, "f1": f1, "mid": (f1 - f0) // 2,
             "skip": l["skip"]}
            for sp in shot_specs(ep, shots) for k, (l, f0, f1) in enumerate(cuts(sp["lines"], sp["frames"], sp["fps"]))]


def _sheet(items, out):
    """Overview of part middle frames with labels (pick exact points on the full-size _mid.png files)."""
    W, H = 270, 480
    im = Image.new("RGB", (4 * (W + 6), ((len(items) + 3) // 4) * (H + 34)), "white")
    d = ImageDraw.Draw(im)
    for i, (png, label) in enumerate(items):
        x, y = (i % 4) * (W + 6), (i // 4) * (H + 34)
        im.paste(Image.open(png).convert("RGB").resize((W, H)), (x, y))
        d.text((x + 4, y + H + 6), label, fill="black")
    im.save(out)


def prep(ep, shots, only=None):
    LP = _parts_mod()
    parts_dir = ep.path("lipsync", "parts")
    os.makedirs(parts_dir, exist_ok=True)
    items = []
    for sp in shot_specs(ep, shots):
        if only and sp["id"] not in only:
            continue
        if not os.path.exists(sp["clip"]):
            print(f"  {sp['id']}: no clip {sp['clip']}, skipped")
            continue
        LP.normalize(sp["clip"], sp["video"], sp["frames"], sp["off"], sp["speed"], sp["fps"], sp["size"])
        plan = json.load(open(LP.split(sp, parts_dir)))
        for p in plan["parts"]:
            if p["skip"]:
                continue
            png = os.path.join(parts_dir, f"{sp['id']}_{p['k']}_mid.png")
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", p["video"], "-vf",
                            f"select=eq(n\\,{p['mid']})", "-frames:v", "1", png], check=True)
            items.append((png, f"{sp['id']}|{p['k']} {p['speaker']} (frame {p['mid']})"))
    os.makedirs(ep.path("build", "review"), exist_ok=True)
    for n in range(0, len(items), 8):
        _sheet(items[n:n + 8], ep.path("build", "review", f"lipsync_sheet_{n // 8}.jpg"))
    print(f"  {len(items)} parts need a face point: read parts/<shot>_<k>_mid.png, add lipsync.faces['<shot>|<k>'] = [x, y]")


def run(ep, shots, only=None, workers=6):
    faces = ep.data.get("lipsync", {}).get("faces", {})
    jobs, missing = [], []
    for p in plan_parts(ep, shots):
        key = f"{p['shot']}|{p['k']}"
        if p["skip"] or (only and p["shot"] not in only):
            continue
        if key not in faces:
            missing.append(f"{key} ({p['who']})")
            continue
        x, y = faces[key]
        jobs.append({"video": ep.path("lipsync", "parts", f"{p['shot']}_{p['k']}.mp4"),
                     "audio": ep.path("lipsync", "parts", f"{p['shot']}_{p['k']}.wav"),
                     "out": ep.path("lipsync", "out", f"{p['shot']}_{p['k']}.mp4"), "face": f"{x},{y}@{p['mid']}"})
    if missing:
        print("  no face point (kept unsynced):", ", ".join(missing))
    if jobs:
        os.makedirs(ep.path("lipsync", "out"), exist_ok=True)
        f = ep.path("lipsync", "out", "_jobs.json")
        json.dump(jobs, open(f, "w"), indent=1)
        subprocess.run([sys.executable, G.tool("generating-video-clips", "scripts", "lipsync_fal.py"), "--jobs", f,
                        "--concurrency", str(workers)])
    return join_all(ep, shots, only)


def join_one(ep, shots, sid, out):
    parts_dir = ep.path("lipsync", "parts")
    os.makedirs(parts_dir, exist_ok=True)
    plan = {"id": sid, "fps": ep.fps, "size": "x".join(map(str, ep.video["clip_size"])), "parts": [
        {"k": p["k"], "line": p["line"], "speaker": p["who"], "f0": p["f0"], "f1": p["f1"], "mid": p["mid"], "skip": p["skip"],
         "video": os.path.join(parts_dir, f"{sid}_{p['k']}.mp4"), "audio": os.path.join(parts_dir, f"{sid}_{p['k']}.wav")}
        for p in plan_parts(ep, shots) if p["shot"] == sid]}
    path = os.path.join(parts_dir, f"{sid}_plan.json")
    json.dump(plan, open(path, "w"), indent=1)
    _parts_mod().join(path, ep.path("lipsync", "out"), out)


def join_all(ep, shots, only=None):
    done = []
    for sp in shot_specs(ep, shots):
        sid = sp["id"]
        if only and sid not in only:
            continue
        k_parts = [p for p in plan_parts(ep, shots) if p["shot"] == sid]
        if any(os.path.exists(ep.path("lipsync", "out", f"{sid}_{p['k']}.mp4")) for p in k_parts):
            join_one(ep, shots, sid, ep.path("lipsync", "final", f"{sid}.mp4"))
            print("  joined", sid)
            done.append(sid)
    return done
