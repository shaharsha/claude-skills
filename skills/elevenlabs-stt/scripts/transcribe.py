#!/usr/bin/env python3
"""Transcribe a recording with ElevenLabs Scribe (default scribe_v3) into transcript.md, raw JSON and optional SRT.

  python3 transcribe.py INPUT --out DIR [options]
  python3 transcribe.py --url https://youtu.be/... --out DIR [options]
  python3 transcribe.py --from-json DIR/talk.scribe.json --out DIR      # re-render, no API call

INPUT is any audio or video file. Video, and any --start/--end range, is first cut to a
mono 16 kHz mp3 with ffmpeg, so a 1 GB mp4 uploads as a few MB. --url sends a hosted file
or a YouTube/TikTok link as source_url and uploads nothing.

Writes DIR/<name>.scribe.json (the raw response, always keep it: re-rendering is free and
re-transcribing is not), DIR/<name>.transcript.md ("[mm:ss] speaker_N: text" paragraphs),
DIR/<name>.srt with --srt, and DIR/<name>.edited.md with --edit. Then prints the length,
language, speaker count, how many words came out in Latin script (the check for English
terms inside Hebrew or Arabic speech), any long stretch with no words, and the cost at
list price.

The key comes from ELEVENLABS_API_KEY, else the first line of ~/.config/elevenlabs/api_key.
It is never printed. Stdlib only; ffmpeg is needed for video input or --start/--end.
"""
import argparse, json, os, pathlib, re, subprocess, sys, tempfile, time, urllib.error, urllib.request, uuid

API = "https://api.elevenlabs.io/v1/speech-to-text"
KEY_FILE = os.path.expanduser("~/.config/elevenlabs/api_key")
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".wmv", ".flv", ".webm", ".mpeg", ".mpg", ".3gp", ".m4v"}
# List prices per audio hour (elevenlabs.io/pricing/api, checked 2026-11-13). Plans include hours.
BASE_PER_HOUR = {"scribe_v3": 0.20, "scribe_v2": 0.20, "scribe_v2_medical": 0.20}
KEYTERMS_PER_HOUR, EDIT_PER_HOUR = 0.05, 0.07
RTL_LANGS = {"heb", "he", "ara", "ar", "fas", "fa", "urd", "ur", "yid", "yi"}


def api_key():
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key and os.path.exists(KEY_FILE):
        key = open(KEY_FILE).readline().strip()
    if not key:
        sys.exit(f"no ElevenLabs key: set ELEVENLABS_API_KEY or put the key alone in {KEY_FILE} (chmod 600)")
    return key


def mmss(s):
    s = int(s)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60:02d}:{s % 60:02d}"


def to_seconds(t):
    return sum(float(p) * 60 ** i for i, p in enumerate(reversed(t.split(":"))))


def prepare_audio(path, start, end):
    """Upload audio files as they are; cut video (or a range) to a small mono mp3 first."""
    p = pathlib.Path(path)
    if not p.exists():
        sys.exit(f"no such file: {p}")
    if p.suffix.lower() not in VIDEO_EXT and not (start or end):
        return p
    out = pathlib.Path(tempfile.mkdtemp()) / (p.stem + ".mp3")
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y"]
    if start:
        cmd += ["-ss", str(to_seconds(start))]
    if end:
        cmd += ["-to", str(to_seconds(end))]
    cmd += ["-i", str(p), "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(out)]
    subprocess.run(cmd, check=True, stdin=subprocess.DEVNULL)
    return out


def read_terms(args):
    terms = []
    for chunk in args.keyterms or []:
        terms += [t.strip() for t in chunk.split(",")]
    if args.keyterms_file:
        for line in open(args.keyterms_file, encoding="utf-8"):
            line = line.split("#", 1)[0].strip()
            if line:
                terms.append(line)
    terms = list(dict.fromkeys(t for t in terms if t))
    bad = [t for t in terms if len(t) > 50 or len(t.split()) > 5 or re.search(r"[<>{}\[\]\\]", t)]
    if bad:
        sys.exit(f"keyterms must be <=50 chars, <=5 words, no <>{{}}[]\\ : {bad[:5]}")
    if len(terms) > 1000:
        sys.exit(f"{len(terms)} keyterms; the batch limit is 1,000")
    return terms


def build_fields(a, terms):
    f = [("model_id", a.model), ("timestamps_granularity", "word"),
         ("diarize", "false" if a.no_diarize else "true"),
         ("tag_audio_events", "true" if a.events else "false")]
    if a.language:
        f.append(("language_code", a.language))
    for code in a.also or []:
        f.append(("secondary_language_codes", code))
    if a.speakers:
        f.append(("num_speakers", str(a.speakers)))
    if a.numbers:
        f.append(("numbers_format", a.numbers))
    if a.clean:
        f.append(("no_verbatim", "true"))
    if a.seed is not None:
        f.append(("seed", str(a.seed)))
    if a.edit:
        f.append(("transcript_edit", a.edit))
    f += [("keyterms", t) for t in terms]
    if a.srt:
        f.append(("additional_formats", json.dumps([{
            "format": "srt", "max_characters_per_line": a.srt_chars,
            "max_segment_duration_s": a.srt_secs, "include_speakers": False}])))
    if a.url:
        f.append(("source_url", a.url))
    return f


def multipart(fields, audio):
    b = uuid.uuid4().hex
    body = b"".join(f'--{b}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{v}\r\n'.encode()
                    for n, v in fields)
    if audio:
        body += (f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{audio.name}"\r\n'
                 "Content-Type: application/octet-stream\r\n\r\n").encode() + audio.read_bytes() + b"\r\n"
    return body + f"--{b}--\r\n".encode(), b


def call(fields, audio, key, retries=3):
    body, boundary = multipart(fields, audio)
    for attempt in range(retries + 1):
        req = urllib.request.Request(API, data=body, method="POST", headers={
            "xi-api-key": key, "Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            with urllib.request.urlopen(req, timeout=3600) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:600]
            # 429 = concurrency; 5xx said "you have not been charged" when seen on 2026-11-13.
            if (e.code == 429 or e.code >= 500) and attempt < retries:
                wait = 5 * 2 ** attempt
                print(f"HTTP {e.code}, retrying in {wait}s: {msg[:160]}", file=sys.stderr)
                time.sleep(wait)
                continue
            sys.exit(f"HTTP {e.code}: {msg}")


def _srt_time(x):
    h, m, r = x.strip().split(":")
    s, ms = r.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def _srt_fmt(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def _wrap(text, width, max_lines=2):
    lines, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}" if cur else w
    if cur:
        lines.append(cur)
    return lines if len(lines) <= max_lines and all(len(x) <= width for x in lines) else None


def tidy_srt(srt, width=42, max_secs=6.0, min_secs=1.0, max_gap=0.6, words=None):
    """Fix the sub-second fragment cues the API emits (a lone word for 0.2 s).

    First, a cue shorter than min_secs joins the previous or next cue when the pause between
    them is under max_gap, the joined text still wraps into 2 lines of `width`, and the joined
    cue lasts at most max_secs. A fragment that can't join whole is then re-split with its
    neighbour at a word boundary (preferring a sentence end), using the word timestamps from
    the response, so both cues fit the limits. Returns (srt, merged, resplit).
    """
    cues = []
    for block in re.split(r"\n\s*\n", srt.strip()):
        ls = block.strip().split("\n")
        if len(ls) >= 3 and "-->" in ls[1]:
            a, b = ls[1].split("-->")
            cues.append({"start": _srt_time(a), "end": _srt_time(b), "text": " ".join(ls[2:])})
    merged, changed = 0, True
    while changed:
        changed = False
        for i, c in enumerate(cues):
            if c["end"] - c["start"] >= min_secs:
                continue
            for j in (i - 1, i + 1):
                if not 0 <= j < len(cues):
                    continue
                first, second = (cues[j], c) if j < i else (c, cues[j])
                lines = _wrap(f"{first['text']} {second['text']}", width)
                if lines and second["start"] - first["end"] <= max_gap and second["end"] - first["start"] <= max_secs:
                    first.update(end=second["end"], text=" ".join(lines))
                    first["lines"] = lines
                    cues.remove(second)
                    merged += 1
                    changed = True
                    break
            if changed:
                break
    resplit = 0
    timed = [w for w in (words or []) if w.get("type") == "word" and w.get("start") is not None]
    changed = bool(timed)
    while changed:
        changed = False
        for i, c in enumerate(cues):
            if c["end"] - c["start"] >= min_secs:
                continue
            best = None
            for j in (i - 1, i + 1):
                if not 0 <= j < len(cues):
                    continue
                a, b = (j, i) if j < i else (i, j)
                first, second = cues[a], cues[b]
                if second["start"] - first["end"] > max_gap:
                    continue
                ws = [w for w in timed if w["start"] >= first["start"] - 0.05 and w["end"] <= second["end"] + 0.05]
                for k in range(1, len(ws)):
                    left, right = ws[:k], ws[k:]
                    lt, rt = " ".join(w["text"] for w in left), " ".join(w["text"] for w in right)
                    l_end, r_start = left[-1]["end"], right[0]["start"]
                    ll, rl = _wrap(lt, width), _wrap(rt, width)
                    if not (ll and rl and min_secs <= l_end - first["start"] <= max_secs
                            and min_secs <= second["end"] - r_start <= max_secs):
                        continue
                    score = (2 if lt.endswith((".", "?", "!")) else 1 if lt.endswith(",") else 0) \
                        - abs(len(lt) - len(rt)) / 100
                    if best is None or score > best[0]:
                        best = (score, a, b, {"start": first["start"], "end": l_end, "text": lt, "lines": ll},
                                {"start": r_start, "end": second["end"], "text": rt, "lines": rl})
            if best:
                _, a, b, new_a, new_b = best
                cues[a], cues[b] = new_a, new_b
                resplit += 1
                changed = True
                break
    out = []
    for n, c in enumerate(cues, 1):
        lines = c.get("lines") or _wrap(c["text"], width) or [c["text"]]
        out.append(f"{n}\n{_srt_fmt(c['start'])} --> {_srt_fmt(c['end'])}\n" + "\n".join(lines))
    return "\n\n".join(out) + "\n", merged, resplit


def paragraphs(data, max_chars=400, gap=2.0):
    """Group words into paragraphs: a new one at a speaker change, a pause, or a long finished sentence."""
    out, cur = [], None
    for w in data.get("words", []):
        if w.get("type") == "spacing":
            if cur:
                cur["text"] += w["text"]
            continue
        spk = w.get("speaker_id") or ""
        pause = w["start"] - cur["end"] if cur else 0
        long_done = cur and len(cur["text"]) > max_chars and cur["text"].rstrip().endswith((".", "?", "!"))
        if cur is None or spk != cur["spk"] or pause > gap or long_done:
            if cur:
                out.append(cur)
            cur = {"spk": spk, "start": w["start"], "end": w["end"], "text": w["text"]}
        else:
            cur["text"] += w["text"]
            cur["end"] = w["end"]
    if cur:
        out.append(cur)
    return out


def gaps(data, min_seconds=45):
    """Stretches with no words: real silence, or speech the model dropped."""
    words = [w for w in data.get("words", []) if w.get("type") == "word"]
    found, prev = [], 0.0
    for w in words:
        if w["start"] - prev >= min_seconds:
            found.append((prev, w["start"]))
        prev = max(prev, min(w["end"], w["start"] + 5))  # a word can be stretched across a silence
    end = data.get("audio_duration_secs") or prev
    if end - prev >= min_seconds:
        found.append((prev, end))
    return found


def render(data, title, meta):
    paras = paragraphs(data)
    speakers = sorted({p["spk"] for p in paras if p["spk"]})
    lines = [f"# {title}", "", f"Machine transcript ({meta}). Not corrected by hand."]
    if len(speakers) > 1:
        lines.append("Speaker labels are voice clusters, not names.")
    lines += ["", "---", ""]
    for p in paras:
        who = f" {p['spk']}:" if len(speakers) > 1 else ""
        lines += [f"[{mmss(p['start'])}]{who} {' '.join(p['text'].split())}", ""]
    return "\n".join(lines), len(paras), speakers


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?", help="audio or video file")
    ap.add_argument("--url", help="hosted media or YouTube/TikTok link, sent as source_url")
    ap.add_argument("--from-json", help="re-render an earlier .scribe.json without calling the API")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--name", help="output file stem (default: the input's stem)")
    ap.add_argument("--title", help="heading for transcript.md")
    ap.add_argument("--model", default="scribe_v3", help="scribe_v3 (default), scribe_v2, scribe_v2_medical")
    ap.add_argument("--language", help="main language, ISO 639-1/3 (he, en, ...); default auto-detect")
    ap.add_argument("--also", nargs="+", metavar="CODE",
                    help="other languages in the audio (secondary_language_codes, scribe_v3 only; needs --language)")
    ap.add_argument("--keyterms", action="append", metavar="'A,B,C'",
                    help="comma-separated terms to bias toward (names, products, jargon); +$0.05/h")
    ap.add_argument("--keyterms-file", help="one term per line, # comments")
    ap.add_argument("--no-diarize", action="store_true", help="skip speaker labels")
    ap.add_argument("--speakers", type=int, help="upper bound on speakers (num_speakers, max 32)")
    ap.add_argument("--numbers", choices=["digits", "words"], help="numbers_format (scribe_v3 only)")
    ap.add_argument("--clean", action="store_true", help="no_verbatim: drop fillers, false starts, sounds")
    ap.add_argument("--events", action="store_true", help="tag audio events like (laughter)")
    ap.add_argument("--edit", help="transcript_edit instruction, applied after transcription; +$0.07/h")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--srt", action="store_true", help="also write an .srt (needs diarization, forced on)")
    ap.add_argument("--srt-chars", type=int, default=42, help="max characters per subtitle line")
    ap.add_argument("--srt-secs", type=float, default=6.0, help="max seconds per subtitle cue")
    ap.add_argument("--start", help="MM:SS or H:MM:SS, transcribe from here")
    ap.add_argument("--end", help="MM:SS or H:MM:SS, transcribe to here")
    a = ap.parse_args()

    if sum(bool(x) for x in (a.input, a.url, a.from_json)) != 1:
        ap.error("give exactly one of INPUT, --url or --from-json")
    if a.also and not a.language:
        ap.error("--also needs --language (secondary languages alone returned HTTP 500 on 2026-11-13)")
    if (a.also or a.numbers) and a.model != "scribe_v3":
        ap.error("--also and --numbers work only with scribe_v3 (scribe_v2 returns HTTP 400)")
    if a.srt and a.no_diarize:
        ap.error("--srt needs diarization: the API refuses additional formats without it")
    if a.url and (a.start or a.end):
        ap.error("--start/--end cut a local file; download the media first")

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    name = a.name or pathlib.Path(a.input or a.from_json or "transcript").stem.replace(".scribe", "")
    terms, elapsed = [], 0.0
    if a.from_json:
        data = json.loads(pathlib.Path(a.from_json).read_text(encoding="utf-8"))
        meta = data.get("_request", {}).get("model_id", "ElevenLabs Scribe")
    else:
        terms = read_terms(a)
        fields = build_fields(a, terms)
        audio = None if a.url else prepare_audio(a.input, a.start, a.end)
        t0 = time.time()
        data = call(fields, audio, api_key())
        elapsed = time.time() - t0
        data["_request"] = {k: v for k, v in fields if k != "keyterms"} | ({"keyterms": terms} if terms else {})
        (out / f"{name}.scribe.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        meta = f"ElevenLabs {a.model}" + (f", {len(terms)} keyterms" if terms else "")

    md, n_paras, speakers = render(data, a.title or name, meta)
    (out / f"{name}.transcript.md").write_text(md, encoding="utf-8")
    written = [f"{name}.scribe.json", f"{name}.transcript.md"] if not a.from_json else [f"{name}.transcript.md"]
    for fmt in data.get("additional_formats") or []:
        if fmt and fmt.get("requested_format") == "srt":
            (out / f"{name}.api.srt").write_text(fmt["content"], encoding="utf-8")
            srt, merged, resplit = tidy_srt(fmt["content"], a.srt_chars, a.srt_secs, words=data.get("words"))
            (out / f"{name}.srt").write_text(srt, encoding="utf-8")
            written.append(f"{name}.srt ({merged} fragment cues merged, {resplit} re-split at a word boundary; "
                           f"the API's own is {name}.api.srt)")
    edit = data.get("edited_transcript")
    if edit:
        if edit.get("kind") == "transcript":
            (out / f"{name}.edited.md").write_text(edit["edited_text"], encoding="utf-8")
            written.append(f"{name}.edited.md")
        else:
            print(f"WARN: transcript_edit failed: {edit.get('message')}")

    words = [w for w in data.get("words", []) if w.get("type") == "word"]
    secs = data.get("audio_duration_secs") or (words[-1]["end"] if words else 0)
    lang = data.get("language_code")
    print(f"wrote {', '.join(written)} in {out}")
    print(f"{mmss(secs)} of audio, language {lang} ({(data.get('language_probability') or 0):.2f}), "
          f"{len(words)} words, {n_paras} paragraphs, {len(speakers) or 1} speaker(s)"
          + (f", {elapsed:.0f}s to transcribe" if elapsed else ""))
    if lang in RTL_LANGS or (a.language or "") in RTL_LANGS:
        latin = sum(1 for w in words if re.search(r"[A-Za-z]", w["text"]))
        print(f"Latin-script words: {latin} of {len(words)}. If English terms came out in Hebrew/Arabic "
              f"letters, add them with --keyterms (or try --clean) and re-run.")
    for s, e in gaps(data):
        print(f"WARN: no words from {mmss(s)} to {mmss(e)}: silence, or dropped speech. If people talk "
              f"there, re-run with --start {mmss(s)} --end {mmss(e)} and splice the text in.")
    if not a.from_json:
        hours = secs / 3600
        billed = max(secs, 20) / 3600 if len(terms) > 100 else hours
        cost = BASE_PER_HOUR.get(a.model, 0.20) * hours + (KEYTERMS_PER_HOUR * billed if terms else 0) \
            + (EDIT_PER_HOUR * max(hours, 10 / 3600) if a.edit else 0)
        print(f"cost at list price: about ${cost:.3f}")


if __name__ == "__main__":
    main()
