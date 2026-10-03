"""Asset generation driven by episode.json: pure request builders (also dumped by `episode.py prompts`) and runners
that call the sibling skills' scripts. Paid calls happen only in run_* functions."""
import importlib.util, json, os, re, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def tool(skill, *rel):
    p = os.path.join(SKILLS, skill, *rel)
    if not os.path.exists(p):
        raise SystemExit(f"missing {p}: install the {skill} skill next to producing-animated-episodes")
    return p


def _module(skill, script):
    p = tool(skill, "scripts", script)
    sys.path.insert(0, os.path.dirname(p))
    spec = importlib.util.spec_from_file_location(script[:-3], p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def pron(ep, text):
    for a, b in ep.data.get("pronounce", []):
        text = text.replace(a, b)
    return text


# ---------------------------------------------------------------- characters
def char_face_args(ep, key):
    c, P = ep.characters[key], ep.prompts
    refs = c.get("refs", [])
    if refs:
        intro = P["char_face_refs_many"] if len(refs) > 1 else P["char_face_refs_one"]
        prompt = P["char_face"].format(refs=intro, likeness=c["likeness"], style=P["char_style"], no_text=P["char_no_text"])
    else:
        prompt = P["char_face_text"].format(likeness=c["likeness"], style=P["char_style"], no_text=P["char_no_text"])
    args = ["--size", "1024x1536", "--n", "2", "--draft", "--output", f"{ep.paths['cards']}/{key}-face.png", "--prompt", prompt]
    for f in refs:
        args += ["--ref", f"{ep.paths['faces']}/{f}.png"]
    return args


def char_card_args(ep, key, face_file, n=1):
    c, P = ep.characters[key], ep.prompts
    keep = P["char_card_keep_adjusted"].format(adjust=c["face_adjust"]) if c.get("face_adjust") else P["char_card_keep"]
    prompt = P["char_card"].format(body=c["body"], pose=c["pose"], outfit=c["outfit"], bg=c.get("background", c.get("color")),
                                   keep=keep, no_text=P["char_no_text"])
    return ["--size", "1024x1536", "--n", str(n), "--draft", "--output", f"{ep.paths['cards']}/{key}-card.png",
            "--ref", f"{ep.paths['cards']}/{face_file}", "--prompt", prompt]


def char_final_args(ep, key):
    c = ep.characters[key]
    prompt = ep.prompts["char_final"].format(bg=c.get("background", c.get("color")))
    return ["--size", "1024x1536", "--output", f"{ep.paths['characters']}/{key}.png",
            "--ref", f"{ep.paths['cards']}/{key}-card.png", "--prompt", prompt]


# ---------------------------------------------------------------- panels
def panel_prompt(ep, pid):
    p, P = ep.data["panels"][pid], ep.prompts
    chars, scene, exc = p.get("chars", []), p["scene"], p.get("text_exception")
    parts = []
    if chars:
        names = [ep.characters[c]["panel_name"] for c in chars]
        parts.append("\n".join(P["panel_ref"].format(i=i + 1, name=n) for i, n in enumerate(names)))
        for i, n in enumerate(names):  # tie each name's first mention to its card
            scene = re.sub(rf"\b{re.escape(n)}\b", P["panel_bind"].format(i=i + 1, name=n), scene, count=1)
        parts.append(P["panel_task"].format(n=len(chars), noun=P["person_one"] if len(chars) == 1 else P["person_many"]))
    t = P["panel_no_text_base"] + (P["panel_no_text_except"].format(exception=exc) if exc else "")
    parts += [scene, P["panel_style"], P["panel_no_text"].format(t=t), P["panel_footer"]]
    return "\n".join(parts)


def panel_draft_args(ep, pid, hq):
    quality = ["--quality", "high"] if hq else ["--draft"]  # Sunburst high for 2+ characters; Flare drops all but Image 1
    args = ["--size", ep.data.get("panel_size", "1152x2048"), *quality, "--output", f"{ep.paths['panels_draft']}/{pid}.png",
            "--prompt", panel_prompt(ep, pid)]
    for c in ep.data["panels"][pid].get("chars", []):
        args += ["--ref", f"{ep.paths['characters']}/{c}.png"]
    return args


def panel_final_args(ep, pid):
    exc, P = ep.data["panels"][pid].get("text_exception"), ep.prompts
    prompt = P["panel_final"] + (P["panel_final_keep"].format(exception=exc) if exc else P["panel_final_notext"])
    return ["--size", ep.data.get("panel_size", "1152x2048"), "--output", f"{ep.paths['panels_final']}/{pid}.png",
            "--ref", f"{ep.paths['panels_draft']}/{pid}.png", "--prompt", prompt]


# ---------------------------------------------------------------- voices, sound, clips
def line_jobs(ep, only=None):
    groups, jobs = ep.data.get("groups", {}), []
    for l in ep.data.get("lines", []):
        if only and l["id"] not in only:
            continue
        text = pron(ep, l["text"])
        if l["id"] in groups:  # a crowd line: one take per voice, mixed later
            jobs += [[f"{l['id']}__{k}", ep.characters[k]["voice"], text] for k in groups[l["id"]]]
        else:
            jobs.append([l["id"], ep.characters[l["who"]]["voice"], text])
    return jobs


def sound_requests(ep, only=None):
    gm = _module("elevenlabs-tts", "generate_music_and_sfx.py")
    out = {}
    for kind, key in (("music", "music"), ("sfx", "sfx")):
        for name, spec in ep.data.get(key, {}).items():
            if not only or name in only:
                out[name] = list(gm.request_for(name, {"type": kind, **spec}))
    return out


def animate_jobs(ep, only=None):
    A = ep.data.get("animate", {})
    return {sid: [j["panel"], A.get("base", "") + j["motion"]] for sid, j in A.get("shots", {}).items()
            if not only or sid in only}


def prompts_dump(ep):
    P = ep.data.get("panels", {})
    return {"char_face": {k: char_face_args(ep, k) for k in ep.characters},
            "char_card": {k: char_card_args(ep, k, f"{k}-face.png") for k in ep.characters},
            "char_final": {k: char_final_args(ep, k) for k in ep.characters},
            "panel_draft": {p: panel_draft_args(ep, p, False) for p in P},
            "panel_drafthq": {p: panel_draft_args(ep, p, True) for p in P},
            "panel_final": {p: panel_final_args(ep, p) for p in P},
            "lines": line_jobs(ep), "sound": sound_requests(ep), "animate": animate_jobs(ep)}


# ---------------------------------------------------------------- runners (paid)
def _need(var):
    if not os.environ.get(var):
        raise SystemExit(f"set {var} first")


def run_images(ep, arglists, workers=5):
    _need("OPENAI_IMAGE_API_KEY")
    script, total = tool("image-generation", "scripts", "openai-image.sh"), 0.0

    def one(args):
        os.makedirs(os.path.join(ep.root, os.path.dirname(args[args.index("--output") + 1])), exist_ok=True)
        r = subprocess.run(["bash", script, *args], cwd=ep.root, capture_output=True, text=True)
        cost = sum(map(float, re.findall(r"cost≈\$([0-9.]+)", r.stderr)))
        return args[args.index("--output") + 1], r.returncode, (r.stderr.strip().splitlines() or [""])[-1], cost

    with ThreadPoolExecutor(workers) as ex:
        for out, rc, last, cost in ex.map(one, arglists):
            total += cost
            print(f"  {out:40} rc={rc} ${cost:.3f}  {last}", flush=True)
    print(f"  total ≈ ${total:.3f}")
    return total


def _ff(*a):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *a], check=True)


def tts_cmd(V, gen, js, voice, work):
    cmd = [sys.executable, gen, js, voice, work, "--model", V["model"], "--stability", str(V["stability"]),
           "--concurrency", "1", "--prefix", ""]
    if V.get("similarity") is not None:
        cmd += ["--similarity", str(V["similarity"])]
    if V.get("language_code"):
        cmd += ["--language-code", V["language_code"]]
    return cmd


def check_line_paths(ep):
    """Tempo, trim and level write processed copies: raw and processed lines must live in different folders."""
    V = ep.data.get("voice", {})
    processed = V.get("tempo", 1.0) != 1.0 or any(l.get("trim") or l.get("level") for l in ep.data.get("lines", []))
    if processed and os.path.abspath(ep.path("lines_raw")) == os.path.abspath(ep.path("lines")):
        raise SystemExit("paths.lines_raw and paths.lines are the same folder, so tempo/trim/level would be skipped or "
                         "applied twice: give them different folders (defaults: audio/lines_raw and audio/lines)")


def run_lines(ep, only=None, workers=4):
    """TTS every line (crowd lines per voice, then mixed), then tempo, then optional trim and level per line."""
    _need("ELEVENLABS_API_KEY")
    check_line_paths(ep)
    V = {"model": "eleven_v4", "stability": 0.5, "tempo": 1.0, **ep.data.get("voice", {})}
    raw, final = ep.path("lines_raw"), ep.path("lines")
    gen, groups = tool("elevenlabs-tts", "scripts", "generate_tts.py"), ep.data.get("groups", {})

    def tts(job):
        clip, voice, text = job
        work = os.path.join(raw, "_work", clip)
        os.makedirs(work, exist_ok=True)
        js = os.path.join(work, "line.json")
        json.dump({clip: text}, open(js, "w", encoding="utf-8"), ensure_ascii=False)
        r = subprocess.run(tts_cmd(V, gen, js, voice, work), capture_output=True, text=True)
        src = os.path.join(work, f"{clip}.mp3")
        if r.returncode or not os.path.exists(src):
            return clip, (r.stdout + r.stderr).strip().splitlines()[-1:] or ["failed"]
        dst = os.path.join(raw, "parts") if "__" in clip else raw
        os.makedirs(dst, exist_ok=True)
        shutil.copy(src, os.path.join(dst, f"{clip}.mp3"))
        return clip, None

    jobs = line_jobs(ep, only)
    with ThreadPoolExecutor(workers) as ex:
        for clip, err in ex.map(tts, jobs):
            print(f"  {clip}: {'OK' if not err else 'FAIL ' + ' '.join(err)}", flush=True)
    ids = [l["id"] for l in ep.data["lines"] if not only or l["id"] in only]
    for lid in ids:
        if lid in groups:  # crowd: stagger the voices 0-160 ms apart
            parts = [os.path.join(raw, "parts", f"{lid}__{k}.mp3") for k in groups[lid]]
            ins = [x for p in parts for x in ("-i", p)]
            fc = "".join(f"[{i}]adelay={i * 37 % 160}|{i * 37 % 160},volume=0.9[a{i}];" for i in range(len(parts)))
            fc += "".join(f"[a{i}]" for i in range(len(parts))) + f"amix=inputs={len(parts)}:normalize=0,loudnorm=I=-16:TP=-1.5[o]"
            _ff(*ins, "-filter_complex", fc, "-map", "[o]", "-ar", "44100", "-ac", "1", "-b:a", "128k", os.path.join(raw, f"{lid}.mp3"))
    os.makedirs(final, exist_ok=True)
    for lid in ids:
        src, dst = os.path.join(raw, f"{lid}.mp3"), os.path.join(final, f"{lid}.mp3")
        if os.path.abspath(src) != os.path.abspath(dst):
            if V["tempo"] != 1.0:
                _ff("-i", src, "-af", f"atempo={V['tempo']}", "-ar", "44100", "-b:a", "160k", dst)
            else:
                shutil.copy(src, dst)
    flagged = {k: [l["id"] for l in ep.data["lines"] if l.get(k) and l["id"] in ids] for k in ("trim", "level")}
    if flagged["trim"]:
        keep = os.path.join(final, "_pre_trim"); os.makedirs(keep, exist_ok=True)
        for lid in flagged["trim"]:
            shutil.copy(os.path.join(final, f"{lid}.mp3"), os.path.join(keep, f"{lid}.mp3"))
        js = os.path.join(keep, "lines.json")
        json.dump({l["id"]: pron(ep, l["text"]) for l in ep.data["lines"] if l["id"] in flagged["trim"]},
                  open(js, "w", encoding="utf-8"), ensure_ascii=False)
        subprocess.run([sys.executable, tool("elevenlabs-tts", "scripts", "trim_to_words.py"), js, keep, final, "--prefix", ""])
    if flagged["level"]:
        keep = os.path.join(final, "_pre_level"); os.makedirs(keep, exist_ok=True)
        for lid in flagged["level"]:
            shutil.copy(os.path.join(final, f"{lid}.mp3"), os.path.join(keep, f"{lid}.mp3"))
        subprocess.run([sys.executable, tool("elevenlabs-tts", "scripts", "level_clips.py"), keep, final,
                        "--target", str(V.get("level_target", -18)), "--only", *flagged["level"]])


def run_sound(ep, only=None):
    _need("ELEVENLABS_API_KEY")
    gen = tool("elevenlabs-tts", "scripts", "generate_music_and_sfx.py")
    for kind, dest in (("music", "music"), ("sfx", "sfx")):
        spec = {n: {"type": kind, **v} for n, v in ep.data.get(kind, {}).items() if not only or n in only}
        if not spec:
            continue
        os.makedirs(ep.path(dest), exist_ok=True)
        f = ep.path(dest, "_spec.json")
        json.dump(spec, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        subprocess.run([sys.executable, gen, f, ep.path(dest)])


def run_animate(ep, only=None, takes=1):
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_IMAGE_API_KEY")):
        raise SystemExit("set GEMINI_API_KEY first")
    jobs, missing = {}, []
    for sid, (pid, prompt) in animate_jobs(ep, only).items():
        img = ep.path("panels_final", f"{pid}.png")
        if os.path.exists(img):
            jobs[sid] = {"image": img, "prompt": prompt}
        else:
            missing.append(pid)
    if missing:
        raise SystemExit(f"promote these panels first (panels final): {sorted(set(missing))}")
    os.makedirs(ep.path("clips"), exist_ok=True)
    f = ep.path("clips", "_jobs.json")
    json.dump({"base": "", "jobs": jobs}, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    subprocess.run([sys.executable, tool("generating-video-clips", "scripts", "omni_generate.py"), f, ep.path("clips"),
                    "--takes", str(takes)])


def pick_take(ep, sid, k):
    src, dst = ep.path("clips", f"{sid}_t{k}.mp4"), ep.path("clips", f"{sid}.mp4")
    if not os.path.exists(src):
        raise SystemExit(f"no take {src}")
    if os.path.exists(dst):
        os.makedirs(ep.path("clips", "_old"), exist_ok=True)
        shutil.move(dst, ep.path("clips", "_old", f"{sid}-{time.strftime('%Y%m%d-%H%M%S')}.mp4"))
    shutil.copy(src, dst)
    print(f"  {sid}: take {k} installed")
