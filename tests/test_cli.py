from __future__ import annotations

from f1_alltime import cli
from f1_alltime.acquisition import FetchedSeason
from f1_alltime.cache import CacheStore


class FakeClient:
    calls = []
    payload = None

    def __init__(self, settings):
        self.settings = settings

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def fetch_season(self, season):
        self.calls.append(season)
        return FetchedSeason(season=season, payload=self.payload)


def test_fetch_uses_cache_without_http(tmp_path, make_payload, monkeypatch):
    store = CacheStore(tmp_path)
    store.save(FetchedSeason(2025, make_payload(season=2025)))
    FakeClient.calls = []
    FakeClient.payload = make_payload(season=2025)
    monkeypatch.setattr(cli, "JolpicaClient", FakeClient)

    result = cli.main(["fetch", "--from", "2025", "--to", "2025", "--cache-dir", str(tmp_path)])

    assert result == 0
    assert FakeClient.calls == []


def test_refresh_fetches_existing_season(tmp_path, make_payload, monkeypatch):
    store = CacheStore(tmp_path)
    store.season_path(2025).parent.mkdir(parents=True, exist_ok=True)
    store.season_path(2025).write_text("old", encoding="utf-8")
    FakeClient.calls = []
    FakeClient.payload = make_payload(season=2025)
    monkeypatch.setattr(cli, "JolpicaClient", FakeClient)

    result = cli.main(
        [
            "fetch",
            "--from",
            "2025",
            "--to",
            "2025",
            "--cache-dir",
            str(tmp_path),
            "--refresh",
        ]
    )

    assert result == 0
    assert FakeClient.calls == [2025]
    assert store.season_path(2025).read_text(encoding="utf-8").startswith("{")
