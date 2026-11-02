from __future__ import annotations

import pytest

from f1_alltime.source_models import SourceValidationError, assemble_pages, parse_page


def test_rejects_missing_mrdata(make_payload):
    with pytest.raises(SourceValidationError, match="MRData"):
        parse_page({}, 2026)


def test_rejects_season_mismatch(make_payload):
    with pytest.raises(SourceValidationError, match="requested season"):
        parse_page(make_payload(season=2025), 2026)


def test_rejects_duplicate_driver_ids(make_payload):
    page = parse_page(
        make_payload(total=2, driver_ids=("antonelli", "antonelli")), 2026
    )
    with pytest.raises(SourceValidationError, match="unique"):
        assemble_pages([page], 2026)


def test_rejects_missing_driver_id(make_payload):
    payload = make_payload(total=1, driver_ids=("antonelli",))
    del payload["MRData"]["StandingsTable"]["StandingsLists"][0][
        "DriverStandings"
    ][0]["Driver"]["driverId"]
    page = parse_page(payload, 2026)
    with pytest.raises(SourceValidationError, match="no driverId"):
        assemble_pages([page], 2026)


def test_rejects_advertised_total_mismatch(make_payload):
    page = parse_page(make_payload(total=3), 2026)
    with pytest.raises(SourceValidationError, match="advertised 3"):
        assemble_pages([page], 2026)

