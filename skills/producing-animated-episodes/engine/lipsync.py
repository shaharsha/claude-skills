"""Lip-sync for an episode: one speaker per part, a face point per part, Sync 3 on fal, frame-exact joins.
The renderer uses <lipsync>/final/<shot>.mp4 (already offset, sped and frame-exact) instead of the raw clip, but only
while its record (<shot>.json next to it) matches the shot as it is now."""
import json, os, re, shutil, subprocess, sys, time
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


def _read(path):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return None


def _ident(f):
    return [os.path.getmtime(f), os.path.getsize(f)] if os.path.exists(f) else None


def inputs(ep, shot):
    """What a shot's parts are cut from: the clip, its offset and speed, the frame count, the line timing and takes."""
    clip = ep.path("clips", f"{shot.get('clip', shot['id'])}.mp4")
    skip = sorted(lid for sid, lid in ep.data.get("lipsync", {}).get("skip", []) if sid == shot["id"])
    rec = {"clip": [clip, _ident(clip)], "off": shot.get("clip_off", 0), "speed": shot.get("clip_speed", 1.0),
           "frames": shot["nframes"], "placed": {l: [round(a, 4), round(b, 4)] for l, (a, b) in shot["placed"].items()},
           "audio": {l: _ident(ep.line_audio(l)) for l in shot["placed"]}, "skip": skip}
    return json.loads(json.dumps(rec))


def manifest(ep, shot):
    """The record written next to a joined shot: its inputs plus the face points its parts were synced with."""
    faces = ep.data.get("lipsync", {}).get("faces", {})
    return json.loads(json.dumps({"inputs": inputs(ep, shot),
                                  "faces": {k: v for k, v in faces.items() if k.split("|")[0] == shot["id"]}}))


def current_final(ep, shot):
    """(synced file or None, stale): the synced file only while it was made from the shot as it is now."""
    f = ep.path("lipsync", "final", f"{shot['id']}.mp4")
    if not os.path.exists(f):
        return None, False
    return (f, False) if _read(f[:-4] + ".json") == manifest(ep, shot) else (None, True)


def _part_outs(ep, sid):
    d = ep.path("lipsync", "out")
    return [os.path.join(d, n) for n in sorted(os.listdir(d)) if re.fullmatch(rf"{re.escape(sid)}_\d+\.mp4", n)] \
        if os.path.isdir(d) else []


def _retire(ep, files):
    old = ep.path("lipsync", "out", "_old", time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(old, exist_ok=True)
    for f in files:
        shutil.move(f, os.path.join(old, os.path.basename(f)))
    return old


def retire_stale(ep, shot):
    """Move a shot's synced parts aside when its clip, offset, speed, lines or takes changed, so `run` re-syncs them."""
    sid = shot["id"]
    final = ep.path("lipsync", "final", f"{sid}.mp4")
    rec = _read(final[:-4] + ".json")
    known = rec.get("inputs") if isinstance(rec, dict) else _read(ep.path("lipsync", "parts", f"{sid}_inputs.json"))
    if (rec is None and known is None) or known == inputs(ep, shot):
        return False
    files = _part_outs(ep, sid) + [f for f in (final, final[:-4] + ".json") if os.path.exists(f)]
    if files:
        old = _retire(ep, files)
        print(f"  {sid}: its clip, offset, speed or lines changed: the old synced parts moved to {old}, `run` re-syncs them")
    return True


def checked(ep, shots, only=None):
    """Lip-sync shots whose cut parts match the shot as it is now (the others are named, with the fix)."""
    by, ok = {s["id"]: s for s in shots}, []
    for sid in ep.data.get("lipsync", {}).get("shots", []):
        if only and sid not in only:
            continue
        if _read(ep.path("lipsync", "parts", f"{sid}_inputs.json")) == inputs(ep, by[sid]):
            ok.append(sid)
        else:
            print(f"  {sid}: not prepared for its current clip, offset, speed or lines: "
                  f"run `lipsync prep {sid}` first (skipped)")
    return ok


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
    by, items = {s["id"]: s for s in shots}, []
    for sp in shot_specs(ep, shots):
        if only and sp["id"] not in only:
            continue
        if not os.path.exists(sp["clip"]):
            print(f"  {sp['id']}: no clip {sp['clip']}, skipped")
            continue
        retire_stale(ep, by[sp["id"]])
        LP.normalize(sp["clip"], sp["video"], sp["frames"], sp["off"], sp["speed"], sp["fps"], sp["size"])
        plan = json.load(open(LP.split(sp, parts_dir)))
        json.dump(inputs(ep, by[sp["id"]]), open(os.path.join(parts_dir, f"{sp['id']}_inputs.json"), "w"), indent=1)
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
    ok = checked(ep, shots, only)
    synced_with = {sid: (_read(ep.path("lipsync", "final", f"{sid}.json")) or {}).get("faces", {}) for sid in ok}
    jobs, missing, moved = [], [], []
    for p in plan_parts(ep, shots):
        key = f"{p['shot']}|{p['k']}"
        if p["skip"] or p["shot"] not in ok:
            continue
        if key not in faces:
            missing.append(f"{key} ({p['who']})")
            continue
        done = ep.path("lipsync", "out", f"{p['shot']}_{p['k']}.mp4")
        if os.path.exists(done) and synced_with[p["shot"]].get(key, faces[key]) != faces[key]:
            moved.append(done)  # synced on another face point
        x, y = faces[key]
        jobs.append({"video": ep.path("lipsync", "parts", f"{p['shot']}_{p['k']}.mp4"),
                     "audio": ep.path("lipsync", "parts", f"{p['shot']}_{p['k']}.wav"),
                     "out": ep.path("lipsync", "out", f"{p['shot']}_{p['k']}.mp4"), "face": f"{x},{y}@{p['mid']}",
                     "seconds": (p["f1"] - p["f0"]) / ep.fps})
    if missing:
        print("  no face point (kept unsynced):", ", ".join(missing))
    if moved:
        print(f"  face point changed, re-syncing: {', '.join(os.path.basename(f) for f in moved)} "
              f"(old parts in {_retire(ep, moved)})")
    secs = sum(j["seconds"] for j in jobs if not os.path.exists(j["out"]))
    print(f"  {len(jobs)} part(s) to sync, {secs:.1f} s of video not yet synced: about ${secs * 0.133:.2f} (Sync 3 on fal, ~$0.133/s)")
    if jobs:
        os.makedirs(ep.path("lipsync", "out"), exist_ok=True)
        f = ep.path("lipsync", "out", "_jobs.json")
        json.dump(jobs, open(f, "w"), indent=1)
        subprocess.run([sys.executable, G.tool("generating-video-clips", "scripts", "lipsync_fal.py"), "--jobs", f,
                        "--concurrency", str(workers)])
    return join_all(ep, shots, only, ok)


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
    json.dump(manifest(ep, {s["id"]: s for s in shots}[sid]), open(out[:-4] + ".json", "w"), indent=1)


def join_all(ep, shots, only=None, ok=None):
    done = []
    for sid in (checked(ep, shots, only) if ok is None else ok):
        k_parts = [p for p in plan_parts(ep, shots) if p["shot"] == sid]
        if any(os.path.exists(ep.path("lipsync", "out", f"{sid}_{p['k']}.mp4")) for p in k_parts):
            join_one(ep, shots, sid, ep.path("lipsync", "final", f"{sid}.mp4"))
            print("  joined", sid)
            done.append(sid)
    return done
