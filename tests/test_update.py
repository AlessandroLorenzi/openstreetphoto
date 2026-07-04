from openstreetphoto import update


def test_update_runs_download_then_extract(monkeypatch):
    calls = []
    monkeypatch.setattr(update, "download_main", lambda argv: calls.append("download") or 0)
    monkeypatch.setattr(update, "extract_main", lambda argv: calls.append("extract") or 0)
    assert update.main([]) == 0
    assert calls == ["download", "extract"]


def test_update_stops_if_download_fails(monkeypatch):
    calls = []
    monkeypatch.setattr(update, "download_main", lambda argv: calls.append("download") or 1)
    monkeypatch.setattr(update, "extract_main", lambda argv: calls.append("extract") or 0)
    assert update.main([]) == 1
    assert calls == ["download"]


def test_update_propagates_extract_failure(monkeypatch):
    monkeypatch.setattr(update, "download_main", lambda argv: 0)
    monkeypatch.setattr(update, "extract_main", lambda argv: 1)
    assert update.main([]) == 1
