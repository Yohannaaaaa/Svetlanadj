import synth
from app import audio_analysis


def test_bpm_and_drop(tmp_path):
    path = tmp_path / "track.wav"
    for bpm in (150.0, 155.0):
        drop = synth.make_track(path, bpm=bpm)
        r = audio_analysis.analyze(path)
        assert abs(r["bpm"] - bpm) < 0.2
        assert r["drops"], "drop non détecté"
        assert abs(r["drops"][0]["time"] - drop) < 0.1
        start = audio_analysis.suggest_start(r, 15, 10)
        assert abs((r["drops"][0]["time"] - start) - 10) < 0.01
