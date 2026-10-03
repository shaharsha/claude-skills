import base64, http.server, io, json, os, subprocess, threading
import pytest
from PIL import Image

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "openai-image.sh")
PROMPT = 'CONSTRAINTS: no text anywhere; absolutely no subtitles @home <b> "quoted" end.'


def png_b64():
    buf = io.BytesIO(); Image.new("RGB", (8, 8), "red").save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


@pytest.fixture
def fake_api():
    got = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            got["path"], got["ctype"], got["body"] = self.path, self.headers["Content-Type"], body
            out = json.dumps({"data": [{"b64_json": png_b64()}], "usage": {"output_tokens": 1}}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}", got
    srv.shutdown()


def multipart_field(got, name):
    boundary = got["ctype"].split("boundary=")[1].encode()
    for part in got["body"].split(b"--" + boundary):
        head, _, value = part.partition(b"\r\n\r\n")
        if f'name="{name}"'.encode() in head:
            return value[:-2].decode()          # drop the trailing \r\n
    return None


def test_edit_prompt_reaches_api_intact(fake_api, tmp_path):
    base, got = fake_api
    ref = tmp_path / "ref.png"; Image.new("RGB", (8, 8), "blue").save(ref)
    env = dict(os.environ, OPENAI_IMAGE_API_KEY="dummy", OPENAI_IMAGE_API_BASE=base)
    r = subprocess.run(["bash", SCRIPT, "--prompt", PROMPT, "--ref", str(ref), "--draft", "--output", str(tmp_path / "o.png")],
                       env=env, capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert got["path"] == "/v1/images/edits"
    assert multipart_field(got, "prompt") == PROMPT
    assert (tmp_path / "o.png").exists()
