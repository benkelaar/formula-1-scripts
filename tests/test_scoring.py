from __future__ import annotations

import json

import pytest

from f1_alltime.acquisition import FetchedSeason
from f1_alltime.cache import CacheStore
from f1_alltime.scoring import build_rankings, build_rankings_from_cache, fictional_points, write_rankings


@pytest.mark.parametrize(
    ("position", "points"),
    [("1", 25), ("2", 18), ("3", 15), ("4", 12), ("5", 10), ("6", 8), ("7", 6), ("8", 4), ("9", 2), ("10", 1)],
)
def test_fictional_points_table(position, points):
    assert fictional_points(position) == points


@pytest.mark.parametrize("position", [None, "", "D", "0", "11", "1.0", -1, True])
def test_non_scoring_positions_receive_zero(position):
    assert fictional_points(position) == 0


def _standing(driver_id, position):
    return {"position": str(position), "Driver": {"driverId": driver_id}}


def test_accumulates_retired_drivers_and_all_tie_breaks():
    result = build_rankings(
        [
            (2000, [_standing("old_champion", 1), _standing("alpha", 2)], "a"),
            (2001, [_standing("new_champion", 1), _standing("beta", 2)], "b"),
            (2002, [_standing("new_champion", 1), _standing("old_champion", 2)], "c"),
        ]
    )

    final = result["seasons"][-1]["rankings"]
    assert [row["driver_id"] for row in final] == ["new_champion", "old_champion", "alpha", "beta"]
    assert next(row for row in final if row["driver_id"] == "alpha")["season_position"] is None


def test_excludes_driver_until_they_score():
    result = build_rankings(
        [
            (2000, [_standing("eventual_scorer", 11), _standing("scorer", 10)], "a"),
            (2001, [_standing("eventual_scorer", 10)], "b"),
        ]
    )

    assert [row["driver_id"] for row in result["seasons"][0]["rankings"]] == ["scorer"]
    assert [row["driver_id"] for row in result["seasons"][1]["rankings"]] == [
        "eventual_scorer",
        "scorer",
    ]


def test_earliest_title_then_driver_id_break_equal_score_ties():
    result = build_rankings(
        [
            (2000, [_standing("early", 1), _standing("zulu", 2), _standing("alpha", 2)], "a"),
            (2001, [_standing("late", 1), _standing("early", 10)], "b"),
            (2002, [_standing("late", 10)], "c"),
        ]
    )
    final = result["seasons"][-1]["rankings"]
    assert [row["driver_id"] for row in final] == ["early", "late", "alpha", "zulu"]


def test_input_order_does_not_affect_rankings():
    standings = [_standing("zulu", 2), _standing("alpha", 3)]
    forward = build_rankings([(2000, standings, "hash")])
    reverse = build_rankings([(2000, list(reversed(standings)), "hash")])
    assert forward == reverse


def test_cache_build_and_write_are_deterministic(tmp_path, make_payload):
    cache = CacheStore(tmp_path / "raw")
    cache.save(FetchedSeason(2025, make_payload(season=2025)))
    rankings = build_rankings_from_cache(cache.root, 2025, 2025)
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    assert write_rankings(first, rankings) == write_rankings(second, rankings)
    assert first.read_bytes() == second.read_bytes()
    assert json.loads(first.read_text(encoding="utf-8"))["schema_version"] == 1


def test_missing_cache_does_not_replace_output(tmp_path):
    output = tmp_path / "rankings.json"
    output.write_text("existing", encoding="utf-8")
    with pytest.raises(ValueError, match="missing cached season"):
        rankings = build_rankings_from_cache(tmp_path / "raw", 2025, 2025)
        write_rankings(output, rankings)
    assert output.read_text(encoding="utf-8") == "existing"
