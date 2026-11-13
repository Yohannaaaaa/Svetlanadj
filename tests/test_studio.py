import io
import time

import synth


def wait(client, pid, pred, timeout=240):
    t = time.time()
    while time.time() - t < timeout:
        p = client.get(f"/api/projects/{pid}").get_json()["project"]
        if pred(p):
            return p
        time.sleep(0.5)
    raise AssertionError("timeout: " + str(p))


def test_full_demo_pipeline(client, portrait, tmp_path):
    r = client.post("/api/identity", data={"reference": (open(portrait, "rb"), "svetlana.png"),
                                           "description": "SVETLANA test"},
                    content_type="multipart/form-data")
    assert r.status_code == 200, r.get_json()
    r = client.post("/api/projects", json={"template": "awakening", "provider": "demo", "aspect": "9:16"})
    p = r.get_json()["project"]
    pid = p["id"]
    assert len(p["shots"]) == 4
    assert "Pioneer" in p["shots"][2]["prompt"]

    wav = tmp_path / "t.wav"
    synth.make_track(wav, bpm=152)
    r = client.post(f"/api/projects/{pid}/audio", data={"audio": (open(wav, "rb"), "my track.wav")},
                    content_type="multipart/form-data")
    p = r.get_json()["project"]
    assert abs(p["analysis"]["bpm"] - 152) < 0.2
    assert p["audio_start"] > 0

    client.post(f"/api/projects/{pid}/generate_all", json={"what": "keyframes"})
    wait(client, pid, lambda p: all(s["status"] == "keyframe_ready" for s in p["shots"]))
    client.post(f"/api/projects/{pid}/generate_all", json={"what": "clips"})
    p = wait(client, pid, lambda p: all(s["status"] in ("ready", "error") for s in p["shots"]))
    assert all(s["status"] == "ready" for s in p["shots"]), [s.get("error") for s in p["shots"]]

    client.patch(f"/api/projects/{pid}", json={"logo": {"mode": "both", "at": 10.6}})
    client.post(f"/api/projects/{pid}/render", json={"formats": ["vertical", "horizontal"]})
    p = wait(client, pid, lambda p: p["render"]["status"] in ("done", "error"), timeout=600)
    assert p["render"]["status"] == "done", p["render"]
    outs = {o["format"]: o for o in p["render"]["outputs"]}
    assert set(outs) == {"vertical", "horizontal"}
    r = client.get(f"/media/p/{pid}/exports/{outs['vertical']['video']}")
    assert r.status_code == 200 and len(r.data) > 10000


def test_csrf_and_auth(app, tmp_path):
    c = app.test_client()
    assert c.post("/api/projects", json={}).status_code == 403
    app.config["STUDIO_PASSWORD"] = "pw"
    assert c.get("/api/state").status_code == 401
    assert c.post("/login", data={"password": "pw"}).status_code == 302
    assert c.get("/api/state").status_code == 200


def test_secrets_encrypted(client, app):
    r = client.post("/api/secrets", json={"name": "fal", "value": "fal-key-1234567890"})
    st = r.get_json()["secrets"]["fal"]
    assert st["configured"] and st["masked"] == "fal…7890"
    raw = (app.config["DATA_DIR"] / "secrets.enc").read_bytes()
    assert b"fal-key" not in raw
