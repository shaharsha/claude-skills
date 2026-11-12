# /// script
# requires-python = ">=3.9"
# dependencies = ["websockets>=13"]
# ///
"""Stream a local file to Scribe v3 Live at real-time pace and print what comes back.

  uv run stream_live.py FILE [--secs 60] [--param commit_strategy=turn_prediction --param diarize=true ...]

A test bench for realtime settings before you build an integration: it decodes FILE to
16 kHz mono PCM with ffmpeg, sends 100 ms chunks every 100 ms over
wss://api.elevenlabs.io/v1/speech-to-text/realtime, commits at the end, and prints the
session config the server accepted plus every committed, diarized, entity and error
message with its arrival time. Partial transcripts are counted, not printed.

Defaults: model_id=scribe_v3_live, audio_format=pcm_16000, commit_strategy=turn_prediction,
diarize=true, include_timestamps=true. Any --param KEY=VALUE overrides or adds a query
parameter (e.g. language_code=he, multilang_mode=true, keyterms=Acme, no_verbatim=true).
The key comes from ELEVENLABS_API_KEY or ~/.config/elevenlabs/api_key and is sent as the
xi-api-key header. Realtime is billed per second of audio streamed ($0.22/h list).
"""
import argparse, asyncio, base64, json, os, subprocess, sys, time, urllib.parse

import websockets

URL = "wss://api.elevenlabs.io/v1/speech-to-text/realtime"
DEFAULTS = {"model_id": "scribe_v3_live", "audio_format": "pcm_16000", "commit_strategy": "turn_prediction",
            "diarize": "true", "include_timestamps": "true"}


def key():
    k = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    path = os.path.expanduser("~/.config/elevenlabs/api_key")
    if not k and os.path.exists(path):
        k = open(path).readline().strip()
    if not k:
        sys.exit("no ElevenLabs key: set ELEVENLABS_API_KEY or ~/.config/elevenlabs/api_key")
    return k


async def run(pcm, params):
    query = urllib.parse.urlencode([(k, v) for k, vs in params.items() for v in vs])
    counts, t0 = {}, time.time()
    async with websockets.connect(f"{URL}?{query}", additional_headers={"xi-api-key": key()}, max_size=None) as ws:
        async def send():
            step = 3200  # 100 ms of 16-bit 16 kHz mono
            for i in range(0, len(pcm), step):
                await ws.send(json.dumps({"message_type": "input_audio_chunk", "commit": False, "sample_rate": 16000,
                                          "audio_base_64": base64.b64encode(pcm[i:i + step]).decode()}))
                await asyncio.sleep(0.1)
            await ws.send(json.dumps({"message_type": "input_audio_chunk", "commit": True, "sample_rate": 16000,
                                      "audio_base_64": ""}))
        sender = asyncio.create_task(send())
        try:
            while True:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
                kind = msg.get("message_type", "?")
                counts[kind] = counts.get(kind, 0) + 1
                if kind == "session_started":
                    print("config:", json.dumps(msg.get("config"), ensure_ascii=False))
                elif kind == "partial_transcript":
                    continue
                else:
                    spk = ""
                    if msg.get("words") and kind == "diarized_transcript":
                        spk = " [" + ",".join(sorted({w.get("speaker_id") or "-" for w in msg["words"]})) + "]"
                    body = msg.get("text") or msg.get("error") or msg.get("warning") or json.dumps(msg, ensure_ascii=False)
                    print(f"{time.time() - t0:6.1f}s {kind}{spk}: {body}")
        except asyncio.TimeoutError:
            pass
        except websockets.ConnectionClosed as e:
            print(f"closed: {e.code} {e.reason}")
        sender.cancel()
    print("message counts:", counts)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--secs", type=float, default=60, help="seconds of the file to stream (default 60)")
    ap.add_argument("--start", type=float, default=0, help="start offset in seconds")
    ap.add_argument("--param", action="append", default=[], metavar="KEY=VALUE",
                    help="query parameter; repeat a key (keyterms=A --param keyterms=B) for a list")
    a = ap.parse_args()
    params = {k: [v] for k, v in DEFAULTS.items()}
    overridden = set()
    for p in a.param:
        k, _, v = p.partition("=")
        if k not in overridden:
            params[k] = []
            overridden.add(k)
        params[k].append(v)
    pcm = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", str(a.start), "-t", str(a.secs), "-i", a.file,
                          "-f", "s16le", "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
    asyncio.run(run(pcm, params))


if __name__ == "__main__":
    main()
