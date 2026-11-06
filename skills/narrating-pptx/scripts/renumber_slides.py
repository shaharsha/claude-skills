#!/usr/bin/env python3
"""Shift narration to follow a slide inserted into, or deleted from, the middle of a deck.

  python3 renumber_slides.py scripts.json audio/ --insert 5 [--alignment alignment/] [--dry-run]
  python3 renumber_slides.py scripts.json audio/ --delete 5 [--alignment alignment/] [--dry-run]

--insert N: N is the NEW slide's own number (a slide added after slide 4 is --insert 5).
Slides N and later move up by one (audio/slide05.mp3 -> slide06.mp3, the scripts.json
key "05" -> "06", the matching _manifest.json entry and alignment file), leaving N free. Write the new slide's script under key N and generate only that clip,
with the voice and settings recorded in _manifest.json.
--delete N: slide N's clip, manifest entry and alignment move into audio/removed/
(never deleted), its script is dropped, and later slides move down by one.

Only the numbering changes, so nothing is regenerated and nothing is billed. Renames go
through temporary names, so no clip can overwrite another midway. --dry-run prints
the plan without touching anything.
"""
import argparse, json, os, re, sys, time

KEY = re.compile(r"^\d+$")


def plan(keys, op, n):
    """{old_key: new_key or None (removed)}. Each key keeps its own padding ("5" -> "6", "05" -> "06")."""
    moves = {}
    for k in sorted((k for k in keys if KEY.match(k)), key=int):
        i = int(k)
        if op == "insert" and i >= n:
            moves[k] = str(i + 1).zfill(len(k))
        elif op == "delete" and i == n:
            moves[k] = None
        elif op == "delete" and i > n:
            moves[k] = str(i - 1).zfill(len(k))
    return moves


def clip_names(manifest, moves, prefix):
    """{old_key: (old_file, new_file or None)} for the audio, from the manifest's file names.

    A clip the manifest doesn't list is assumed to be <prefix><key>.mp3. A listed file
    whose name doesn't end in its key can't be renamed safely, so that is an error.
    """
    out = {}
    for old, new in moves.items():
        f = (manifest.get(old) or {}).get("file") or f"{prefix}{old}.mp3"
        if not f.endswith(f"{old}.mp3"):
            sys.exit(f"can't renumber {f}: its name doesn't end in its key {old}")
        out[old] = (f, f[:-len(old) - 4] + new + ".mp3" if new else None)
    return out


def set_aside(folder, name):
    """A path in folder/removed/ that doesn't overwrite an earlier removal."""
    removed = os.path.join(folder, "removed")
    dst = os.path.join(removed, name)
    if os.path.exists(dst):
        stem, ext = os.path.splitext(name)
        dst = os.path.join(removed, f"{stem}.{time.strftime('%Y%m%d-%H%M%S')}{ext}")
    return dst


def rename_all(pairs, dry):
    """pairs: [(src, dst)]. Two phases through temporary names so no rename overwrites another."""
    pairs = [(s, d) for s, d in pairs if os.path.exists(s)]
    for s, d in pairs:
        print(f"  {s} -> {d}")
    if dry:
        return
    tmp = [(s, s + ".renumber-tmp", d) for s, d in pairs]
    for s, t, _ in tmp:
        os.rename(s, t)
    for _, t, d in tmp:
        os.makedirs(os.path.dirname(d) or ".", exist_ok=True)
        os.rename(t, d)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scripts"); ap.add_argument("audio_dir")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--insert", type=int, metavar="N",
                   help="the new slide's own number (added after slide 4 = 5); N and later move up by one")
    g.add_argument("--delete", type=int, metavar="N", help="remove slide N; later slides move down by one")
    ap.add_argument("--alignment", help="alignment/ directory to keep in step (<prefix>NN.json)")
    ap.add_argument("--prefix", default="slide",
                    help="name prefix of clips the manifest doesn't list, and of alignment files (default: slide)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    op, n = ("insert", a.insert) if a.insert is not None else ("delete", a.delete)

    scripts = json.load(open(a.scripts, encoding="utf-8"))
    mpath = os.path.join(a.audio_dir, "_manifest.json")
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}
    keys = set(scripts) | set(manifest)
    moves = plan(keys, op, n)
    if not moves:
        sys.exit(f"nothing to move: no slide numbered {n} or later")
    clash = {v for v in moves.values() if v} & (keys - set(moves))
    if clash:
        sys.exit(f"renumbering would collide with existing keys {sorted(clash)} - mixed key padding?")
    names = clip_names(manifest, moves, a.prefix)
    missing = [f for k, (f, _) in names.items()
               if (manifest.get(k) or {}).get("file") and not os.path.exists(os.path.join(a.audio_dir, f))]
    if missing:
        sys.exit(f"the manifest lists clips that aren't in {a.audio_dir}: {missing} - nothing was changed")

    files = []
    for old, (f_old, f_new) in names.items():
        src = os.path.join(a.audio_dir, f_old)
        files.append((src, os.path.join(a.audio_dir, f_new) if f_new else set_aside(a.audio_dir, f_old)))
    if a.alignment:
        for old, new in moves.items():
            src = os.path.join(a.alignment, f"{a.prefix}{old}.json")
            dst = (os.path.join(a.alignment, f"{a.prefix}{new}.json") if new
                   else set_aside(a.alignment, f"{a.prefix}{old}.json"))
            files.append((src, dst))
    print(f"{op} {n}: {len(moves)} slide(s) affected")
    rename_all(files, a.dry_run)

    def shifted(d):
        out = {k: v for k, v in d.items() if k not in moves}
        for old, new in moves.items():
            if old in d and new:
                out[new] = d[old]
        return dict(sorted(out.items(), key=lambda kv: (int(kv[0]) if KEY.match(kv[0]) else 1 << 30, kv[0])))

    new_scripts = shifted(scripts)
    new_manifest = shifted(manifest)
    for old, new in moves.items():
        if new and new in new_manifest and "file" in new_manifest[new]:
            new_manifest[new] = {**new_manifest[new], "file": names[old][1]}
    if a.dry_run:
        print(f"scripts.json keys after: {list(new_scripts)}")
        return
    gone = [k for k, v in moves.items() if v is None]
    if gone and gone[0] in manifest:  # keep the removed clip's settings next to it
        dst = set_aside(a.audio_dir, os.path.splitext(names[gone[0]][0])[0] + ".manifest.json")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        json.dump({gone[0]: manifest[gone[0]]}, open(dst, "w"), indent=1)
    json.dump(new_scripts, open(a.scripts, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if manifest:
        json.dump(new_manifest, open(mpath, "w"), indent=1)
    if op == "insert":
        hint = (f"write slide {n}'s script, then generate only that clip (--only) with the manifest's voice "
                f"and settings")
    else:
        hint = "rebuild the narrated deck from the full audio set"
    print(f"done: {a.scripts}, {mpath} and the files are renumbered; {hint}. For Google Slides, rebuild and "
          f"re-upload the videos for slide {n} and every later slide: Drive files are matched by slide number.")


if __name__ == "__main__":
    main()
