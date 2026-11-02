"""Fictional scoring and deterministic cumulative rankings."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .cache import CacheStore, _write_bytes_atomic, canonical_json_bytes
from .source_models import assemble_pages, parse_page


SCHEMA_VERSION = 1
POINTS_BY_POSITION = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}


def fictional_points(position: Any) -> int:
    """Return the fictional award for an official championship position."""

    if isinstance(position, bool):
        return 0
    try:
        parsed = int(position)
    except (TypeError, ValueError):
        return 0
    if str(position).strip() != str(parsed):
        return 0
    return POINTS_BY_POSITION.get(parsed, 0)


@dataclass
class _DriverTotal:
    points: int = 0
    championships: int = 0
    first_championship_year: int | None = None


def build_rankings(seasons: Iterable[tuple[int, list[dict[str, Any]], str]]) -> dict[str, Any]:
    """Build cumulative snapshots from validated season standings."""

    totals: dict[str, _DriverTotal] = {}
    snapshots: list[dict[str, Any]] = []
    ordered_seasons = sorted(seasons, key=lambda item: item[0])
    for season, standings, source_sha256 in ordered_seasons:
        current: dict[str, tuple[int | None, int]] = {}
        for standing in standings:
            driver_id = standing["Driver"]["driverId"]
            raw_position = standing.get("position")
            position = _numeric_position(raw_position)
            award = fictional_points(raw_position)
            total = totals.setdefault(driver_id, _DriverTotal())
            total.points += award
            if position == 1:
                total.championships += 1
                if total.first_championship_year is None:
                    total.first_championship_year = season
            current[driver_id] = (position, award)

        scoring_drivers = (
            driver_id for driver_id, total in totals.items() if total.points > 0
        )
        ordered_drivers = sorted(
            scoring_drivers,
            key=lambda driver_id: _rank_key(driver_id, totals[driver_id]),
        )
        rows = []
        for rank, driver_id in enumerate(ordered_drivers, start=1):
            total = totals[driver_id]
            position, award = current.get(driver_id, (None, 0))
            rows.append(
                {
                    "rank": rank,
                    "driver_id": driver_id,
                    "season_position": position,
                    "fictional_points": award,
                    "cumulative_points": total.points,
                    "championship_count": total.championships,
                    "first_championship_year": total.first_championship_year,
                }
            )
        snapshots.append({"season": season, "source_sha256": source_sha256, "rankings": rows})

    return {
        "schema_version": SCHEMA_VERSION,
        "from_season": ordered_seasons[0][0] if ordered_seasons else None,
        "to_season": ordered_seasons[-1][0] if ordered_seasons else None,
        "seasons": snapshots,
    }


def build_rankings_from_cache(cache_dir: Path, start_season: int, end_season: int) -> dict[str, Any]:
    """Load and validate cached seasons before scoring them."""

    if end_season < start_season:
        raise ValueError("--to must be greater than or equal to --from")
    store = CacheStore(cache_dir)
    seasons = []
    for season in range(start_season, end_season + 1):
        path = store.season_path(season)
        try:
            raw = path.read_bytes()
        except FileNotFoundError as error:
            raise ValueError(f"missing cached season {season}: {path}") from error
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"invalid JSON for cached season {season}: {path}") from error
        page = parse_page(payload, season)
        assembled = assemble_pages([page], season)
        standings = assembled["MRData"]["StandingsTable"]["StandingsLists"][0]["DriverStandings"]
        source_hash = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
        seasons.append((season, standings, source_hash))
    return build_rankings(seasons)


def write_rankings(path: Path, rankings: dict[str, Any]) -> str:
    """Atomically write canonical ranking JSON and return its SHA-256."""

    data = canonical_json_bytes(rankings)
    _write_bytes_atomic(path, data)
    return hashlib.sha256(data).hexdigest()


def _numeric_position(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if str(value).strip() != str(parsed) or parsed <= 0:
        return None
    return parsed


def _rank_key(
    driver_id: str, total: _DriverTotal
) -> tuple[int, int, bool, int, str]:
    first_year = total.first_championship_year
    return (-total.points, -total.championships, first_year is None, first_year or 0, driver_id)
