import json, os, subprocess, sys, types
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import gslides_narration as N

EMU_W, EMU_H = 9144000, 5143500  # a 10 x 5.625 in page


def tone(path, seconds):
    subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"sine=f=220:d={seconds}", "-ar", "44100", "-ac", "1", str(path)], check=True)


def pres(n_slides, extra=None):
    slides = [{"objectId": f"p{i}", "pageElements": []} for i in range(1, n_slides + 1)]
    for i, els in (extra or {}).items():
        slides[i - 1]["pageElements"] = els
    return {"pageSize": {"width": {"magnitude": EMU_W, "unit": "EMU"}, "height": {"magnitude": EMU_H, "unit": "EMU"}},
            "slides": slides}


class FakeApi:
    """Records calls; answers from a script of canned responses."""
    def __init__(self, folder=None, deck=None, create_status=200):
        self.folder, self.deck, self.create_status, self.calls = folder or {}, deck, create_status, []

    def folder_videos(self, folder):
        return self.folder

    def call(self, method, url, body=None, raw=None, ctype="application/json"):
        self.calls.append((method, url, body))
        if method == "GET" and "presentations" in url:
            return 200, self.deck
        if method == "PATCH":
            return 200, {}
        if method == "POST" and "upload" in url:
            if self.create_status == 403:
                return 403, {"error": {"message": "Service Accounts do not have storage quota.",
                                       "errors": [{"reason": "storageQuotaExceeded"}]}}
            return 200, {"id": "new"}
        if method == "POST" and "batchUpdate" in url:
            created = [r["createVideo"] for r in body["requests"] if "createVideo" in r]
            for c in created:  # apply to the fake deck so the re-read sees them
                i = int(c["objectId"][len(N.PREFIX):])
                self.deck["slides"][i - 1]["pageElements"].append(
                    {"objectId": c["objectId"], "video": {"id": c["id"], "videoProperties": {"autoPlay": True}}})
            return 200, {}
        raise AssertionError(f"unexpected {method} {url}")


# --- videos --------------------------------------------------------------------------------------

def test_video_cmd_cuts_to_audio_length_not_shortest():
    cmd = N.video_cmd("still.png", "a.mp3", 12.3456, "out.mp4")
    assert cmd[:2] == ["ffmpeg", "-nostdin"] and "-shortest" not in cmd
    assert cmd[cmd.index("-t") + 1] == "12.346"


def test_videos_match_their_audio(tmp_path, monkeypatch):
    audio = tmp_path / "audio"; audio.mkdir()
    tone(audio / "slide01.mp3", 2.0); tone(audio / "slide03.mp3", 3.5)
    out = tmp_path / "videos"
    N.main(["videos", str(audio), str(out)])
    for n, secs in ((1, 2.0), (3, 3.5)):
        v = out / f"narration-slide{n:02d}.mp4"
        assert abs(N.probe_seconds(str(v)) - secs) < 0.25
    assert not (out / "narration-slide02.mp4").exists()


# --- placement and insert ------------------------------------------------------------------------

def test_placement_scales_with_the_page():
    s1, x1, y1 = N.placement(EMU_W, EMU_H, "bottom-right", 0.05)
    s2, x2, y2 = N.placement(EMU_W * 4 / 3, EMU_H * 4 / 3, "bottom-right", 0.05)  # 720pt -> 960pt re-sync
    assert s2 == pytest.approx(s1 * 4 / 3) and x2 == pytest.approx(x1 * 4 / 3) and y2 == pytest.approx(y1 * 4 / 3)
    assert x1 + s1 < EMU_W and y1 + s1 < EMU_H
    _, xl, yt = N.placement(EMU_W, EMU_H, "top-left", 0.05)
    assert xl < EMU_W / 2 and yt < EMU_H / 2


def test_insert_requests_replace_old_videos_and_skip_appendix():
    deck = pres(4, {2: [{"objectId": "narr_02", "video": {"id": "old"}}, {"objectId": "title"}]})
    files = {1: {"id": "f1"}, 2: {"id": "f2"}, 4: {"id": "f4"}}
    reqs, placed = N.insert_requests(deck, files, skip={4})
    assert placed == [1, 2]
    assert reqs[0] == {"deleteObject": {"objectId": "narr_02"}}
    assert not any(r.get("deleteObject", {}).get("objectId") == "title" for r in reqs)
    created = [r["createVideo"] for r in reqs if "createVideo" in r]
    assert [c["id"] for c in created] == ["f1", "f2"] and all(c["source"] == "DRIVE" for c in created)
    props = [r["updateVideoProperties"] for r in reqs if "updateVideoProperties" in r]
    assert all(p["videoProperties"] == {"autoPlay": True, "mute": False} for p in props)


def test_insert_end_to_end_with_fake_api(capsys):
    api = FakeApi(folder={1: {"id": "f1"}, 2: {"id": "f2"}}, deck=pres(3))
    a = types.SimpleNamespace(pres="P", folder="F", sa_key=None, skip=[3], corner="bottom-right", size=0.05,
                              dry_run=False, no_share=True)
    N.cmd_insert(a, api)
    assert "autoplaying narration on 2 of 2" in capsys.readouterr().out


class FakeApiWithSharing(FakeApi):
    def call(self, method, url, body=None, raw=None, ctype="application/json"):
        if "/about" in url:
            self.calls.append((method, url, body))
            return 200, {"user": {"emailAddress": "bot@proj.iam.gserviceaccount.com"}}
        if method == "GET" and "/permissions" in url:
            self.calls.append((method, url, body))
            perms = [{"id": "g", "type": "user", "role": "reader", "emailAddress": "guest@example.com"}] if "/P/" in url else []
            return 200, {"permissions": perms}
        return super().call(method, url, body, raw, ctype)


def test_insert_dry_run_sends_nothing(capsys):
    api = FakeApiWithSharing(folder={1: {"id": "f1"}}, deck=pres(2))
    a = types.SimpleNamespace(pres="P", folder="F", sa_key=None, skip=None, corner="top-right", size=0.05,
                              dry_run=True, no_share=False)
    N.cmd_insert(a, api)
    assert not any("batchUpdate" in c[1] for c in api.calls)
    assert not any(c[0] in ("POST", "PATCH", "DELETE") for c in api.calls)  # no grants either
    out = capsys.readouterr().out
    assert "no video for slides [2]" in out and "dry run" in out
    assert "would let ['guest@example.com'] view the folder" in out


# --- upload and wait -----------------------------------------------------------------------------

def test_upload_updates_existing_in_place_and_lists_files_it_cannot_create(tmp_path, capsys):
    for n in (1, 2):
        (tmp_path / f"narration-slide{n:02d}.mp4").write_bytes(b"mp4")
    api = FakeApi(folder={1: {"id": "f1"}}, create_status=403)
    a = types.SimpleNamespace(videos_dir=str(tmp_path), folder="F", sa_key=None)
    with pytest.raises(SystemExit) as e:
        N.cmd_upload(a, api)
    assert e.value.code == 2
    out = capsys.readouterr().out
    assert "narration-slide01.mp4: updated in place" in out
    assert "drag these 1 file(s)" in out and "narration-slide02.mp4" in out
    assert any(m == "PATCH" and "/f1?" in u for m, u, _ in api.calls)


def test_processed_needs_same_file_thumbnail_and_length():
    files = {1: {"hasThumbnail": True, "md5Checksum": "a", "videoMediaMetadata": {"durationMillis": "10100"}},
             2: {"hasThumbnail": False, "md5Checksum": "b", "videoMediaMetadata": {"durationMillis": "5000"}},
             3: {"hasThumbnail": True, "md5Checksum": "OLD", "videoMediaMetadata": {"durationMillis": "12000"}},
             4: {"hasThumbnail": True, "videoMediaMetadata": {"durationMillis": "8000"}}}  # no checksum reported
    local = {1: (10000, "a"), 2: (5000, "b"), 3: (12000, "c"), 4: (8000, "d")}
    assert N.processed(files, local) == [1, 4]


def test_wait_times_out_naming_the_slow_slides(tmp_path, monkeypatch):
    monkeypatch.setattr(N, "local_lengths", lambda d: {1: (1000, "x"), 2: (2000, "y")})
    api = FakeApi(folder={1: {"hasThumbnail": True, "md5Checksum": "x",
                              "videoMediaMetadata": {"durationMillis": "1000"}}})
    t = iter(range(0, 10_000, 300))
    a = types.SimpleNamespace(videos_dir="v", folder="F", sa_key=None, timeout=600)
    with pytest.raises(SystemExit) as e:
        N.cmd_wait(a, api, sleep=lambda s: None, clock=lambda: next(t))
    assert "[2]" in str(e.value)


# --- check ---------------------------------------------------------------------------------------

def test_check_reports_stale_and_missing(capsys):
    deck = pres(3, {1: [{"objectId": "narr_01", "video": {"id": "f1", "videoProperties": {"autoPlay": True}}}],
                    2: [{"objectId": "narr_02", "video": {"id": "old", "videoProperties": {"autoPlay": True}}}]})
    api = FakeApi(folder={1: {"id": "f1"}, 2: {"id": "f2"}, 3: {"id": "f3"}}, deck=deck)
    a = types.SimpleNamespace(pres="P", folder="F", sa_key=None, skip=None, videos_dir=None)
    with pytest.raises(SystemExit):
        N.cmd_check(a, api)
    out = capsys.readouterr().out
    assert "slide 01: OK" in out and "older file" in out and "slide 03: no narration video" in out


def test_name_matches_the_hand_made_names_in_use():
    for name, n in [("narration-slide05.mp4", 5), ("narration-slide05-v3.mp4", 5), ("Narration - slide 11.mp4", 11)]:
        assert int(N.NAME.search(name).group(1)) == n
    assert N.NAME.search("narration-slide05.mp3") is None and N.NAME.search("slide05.mp4") is None


# --- sharing the narration folder like the deck -----------------------------------------------------

DECK_PERMS = [
    {"id": "o", "type": "user", "role": "owner", "emailAddress": "owner@corp.example"},
    {"id": "sa", "type": "user", "role": "writer", "emailAddress": "bot@proj.iam.gserviceaccount.com"},
    {"id": "d", "type": "domain", "role": "commenter", "domain": "corp.example", "allowFileDiscovery": False},
    {"id": "g", "type": "user", "role": "reader", "emailAddress": "Guest@Example.com"},
]


def test_share_plan_grants_the_decks_audience_view_access_only():
    folder = [{"id": "m", "type": "user", "role": "organizer", "emailAddress": "owner@corp.example",
               "permissionDetails": [{"inherited": True}]}]
    add, remove = N.share_plan(DECK_PERMS, folder, "bot@proj.iam.gserviceaccount.com")
    assert remove == []
    assert {"type": "domain", "role": "reader", "domain": "corp.example", "allowFileDiscovery": False} in add
    assert {"type": "user", "role": "reader", "emailAddress": "Guest@Example.com"} in add
    assert len(add) == 2  # the owner already has access through the drive; the service account is skipped


def test_share_plan_is_idempotent_and_prunes_only_direct_grants():
    folder = [{"id": "x", "type": "domain", "role": "reader", "domain": "corp.example"},
              {"id": "y", "type": "user", "role": "reader", "emailAddress": "guest@example.com"},
              {"id": "z", "type": "user", "role": "reader", "emailAddress": "former@example.com"},
              {"id": "m", "type": "user", "role": "organizer", "emailAddress": "owner@corp.example",
               "permissionDetails": [{"inherited": True}]}]
    add, remove = N.share_plan(DECK_PERMS, folder, "bot@proj.iam.gserviceaccount.com")
    assert add == [] and remove == []  # no prune: never removes
    add, remove = N.share_plan(DECK_PERMS, folder, "bot@proj.iam.gserviceaccount.com", prune=True)
    assert add == [] and [p["id"] for p in remove] == ["z"]  # drive members (inherited) are never removed


class ShareApi:
    def __init__(self, deck_perms, folder_perms):
        self.perms, self.calls = {"P": deck_perms, "F": folder_perms}, []

    def call(self, method, url, body=None, raw=None, ctype="application/json"):
        self.calls.append((method, url, body))
        if "/about" in url:
            return 200, {"user": {"emailAddress": "bot@proj.iam.gserviceaccount.com"}}
        if method == "GET" and "/permissions" in url:
            return 200, {"permissions": self.perms["P" if "/P/" in url else "F"]}
        return 200, {}


def test_mirror_sharing_posts_reader_grants_without_notification_emails(capsys):
    api = ShareApi(DECK_PERMS, [])
    assert N.mirror_sharing(api, "P", "F") == 0
    posts = [c for c in api.calls if c[0] == "POST"]
    assert len(posts) == 3 and all(c[2]["role"] == "reader" for c in posts)
    assert all("sendNotificationEmail=false" in c[1] for c in posts if c[2]["type"] == "user")
    assert not any("sendNotificationEmail" in c[1] for c in posts if c[2]["type"] == "domain")


def test_insert_dry_run_does_not_share():
    api = ShareApi(DECK_PERMS, [])
    assert N.mirror_sharing(api, "P", "F", dry_run=True) == 0
    assert not any(c[0] == "POST" for c in api.calls)


class DrivesApi:
    def __init__(self, drives, owner):
        self.drives, self.owner = drives, owner

    def call(self, method, url, body=None, raw=None, ctype="application/json"):
        if "/drives?" in url:
            return 200, {"drives": self.drives}
        return 200, {"owners": [{"emailAddress": self.owner}]}


def test_drive_auto_picks_the_drive_named_for_the_deck_owners_domain():
    drives = [{"id": "A", "name": "Deck narration (corp.example)"}, {"id": "S", "name": "Deck narration (home.example)"}]
    assert N.find_shared_drive(DrivesApi(drives, "me@home.example"), "auto", "P") == "S"
    assert N.find_shared_drive(DrivesApi(drives, "owner@corp.example"), "auto", "P") == "A"
    with pytest.raises(SystemExit):
        N.find_shared_drive(DrivesApi(drives, "x@other.org"), "auto", "P")
