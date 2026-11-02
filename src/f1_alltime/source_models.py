"""Validation and assembly of Jolpica source responses."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


class SourceValidationError(ValueError):
    """Raised when a Jolpica response violates acquisition invariants."""


def _non_negative_int(value: Any, field: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise SourceValidationError(f"{field} must be an integer") from error
    if parsed < 0:
        raise SourceValidationError(f"{field} cannot be negative")
    return parsed


@dataclass(frozen=True)
class ParsedPage:
    payload: dict[str, Any]
    total: int
    limit: int
    offset: int
    represented_round: int
    standings: list[dict[str, Any]]


def parse_page(payload: Any, requested_season: int) -> ParsedPage:
    """Validate one Jolpica page and expose its pagination data."""

    if not isinstance(payload, dict) or not isinstance(payload.get("MRData"), dict):
        raise SourceValidationError("response must contain an MRData object")

    mrdata = payload["MRData"]
    total = _non_negative_int(mrdata.get("total"), "MRData.total")
    limit = _non_negative_int(mrdata.get("limit"), "MRData.limit")
    offset = _non_negative_int(mrdata.get("offset"), "MRData.offset")
    table = mrdata.get("StandingsTable")
    if not isinstance(table, dict):
        raise SourceValidationError("response must contain a StandingsTable object")
    if str(table.get("season")) != str(requested_season):
        raise SourceValidationError(
            f"requested season {requested_season}, received {table.get('season')!r}"
        )

    represented_round = _non_negative_int(table.get("round"), "StandingsTable.round")
    lists = table.get("StandingsLists")
    if not isinstance(lists, list) or len(lists) != 1:
        raise SourceValidationError("response must contain exactly one standings list")
    standings = lists[0].get("DriverStandings") if isinstance(lists[0], dict) else None
    if not isinstance(standings, list):
        raise SourceValidationError("standings list must contain DriverStandings")
    return ParsedPage(payload, total, limit, offset, represented_round, standings)


def assemble_pages(pages: list[ParsedPage], requested_season: int) -> dict[str, Any]:
    """Combine validated pages and validate record-level acquisition invariants."""

    if not pages:
        raise SourceValidationError("at least one response page is required")
    expected_total = pages[0].total
    represented_round = pages[0].represented_round
    standings: list[dict[str, Any]] = []
    for page in pages:
        if page.total != expected_total:
            raise SourceValidationError("pagination total changed between responses")
        if page.represented_round != represented_round:
            raise SourceValidationError("represented round changed between responses")
        standings.extend(page.standings)

    if not standings:
        raise SourceValidationError("driver standings cannot be empty")
    if len(standings) != expected_total:
        raise SourceValidationError(
            f"advertised {expected_total} records but collected {len(standings)}"
        )

    driver_ids: list[str] = []
    for index, standing in enumerate(standings):
        driver = standing.get("Driver") if isinstance(standing, dict) else None
        driver_id = driver.get("driverId") if isinstance(driver, dict) else None
        if not isinstance(driver_id, str) or not driver_id.strip():
            raise SourceValidationError(f"standing {index} has no driverId")
        driver_ids.append(driver_id)
    if len(driver_ids) != len(set(driver_ids)):
        raise SourceValidationError("driver IDs must be unique within a season")

    assembled = deepcopy(pages[0].payload)
    mrdata = assembled["MRData"]
    mrdata["limit"] = str(expected_total)
    mrdata["offset"] = "0"
    table = mrdata["StandingsTable"]
    table["season"] = str(requested_season)
    table["StandingsLists"][0]["DriverStandings"] = standings
    return assembled

