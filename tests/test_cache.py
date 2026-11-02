from __future__ import annotations

import pytest

from f1_alltime.acquisition import FetchedSeason
from f1_alltime.cache import CacheStore, canonical_json_bytes


def fetched(payload, season=2026):
    return FetchedSeason(season=season, payload=payload)


def test_historical_write_and_hash_are_deterministic(tmp_path, make_payload):
    store = CacheStore(tmp_path)
    first = store.save(fetched(make_payload(), season=2026))
    first_bytes = first.path.read_bytes()
    second = store.save(fetched(make_payload(), season=2026))

    assert first.sha256 == second.sha256
    assert first_bytes == second.path.read_bytes() == canonical_json_bytes(make_payload())


def test_refresh_replaces_any_season(tmp_path, make_payload):
    store = CacheStore(tmp_path)
    old_payload = make_payload(total=1, driver_ids=("old",))
    new_payload = make_payload(total=1, driver_ids=("new",))
    store.save(fetched(old_payload))
    result = store.save(fetched(new_payload))

    assert result.path.read_bytes() == canonical_json_bytes(new_payload)


def test_atomic_write_failure_preserves_existing_season(tmp_path, make_payload, monkeypatch):
    store = CacheStore(tmp_path)
    old_payload = make_payload(total=1, driver_ids=("old",))
    store.save(fetched(old_payload))
    old_data = store.season_path(2026).read_bytes()

    def failing_write(path, data):
        raise OSError("simulated write failure")

    monkeypatch.setattr(store, "_write_bytes_atomic", failing_write)
    with pytest.raises(OSError, match="simulated"):
        store.save(fetched(make_payload(total=1, driver_ids=("new",))))

    assert store.season_path(2026).read_bytes() == old_data

