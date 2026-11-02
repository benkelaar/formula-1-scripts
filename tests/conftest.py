from __future__ import annotations

from typing import Any

import httpx
import pytest

from f1_alltime.config import AcquisitionSettings


def standings_payload(
    season: int = 2026,
    *,
    offset: int = 0,
    total: int = 2,
    driver_ids: tuple[str, ...] = ("antonelli", "verstappen"),
    represented_round: int = 19,
) -> dict[str, Any]:
    standings = [
        {
            "position": str(offset + index + 1),
            "positionText": str(offset + index + 1),
            "points": "0",
            "wins": "0",
            "Driver": {
                "driverId": driver_id,
                "givenName": driver_id.title(),
                "familyName": "Driver",
                "nationality": "Test",
            },
            "Constructors": [],
        }
        for index, driver_id in enumerate(driver_ids)
    ]
    return {
        "MRData": {
            "series": "f1",
            "url": f"https://api.jolpi.ca/ergast/f1/{season}/driverstandings/",
            "limit": str(len(driver_ids)),
            "offset": str(offset),
            "total": str(total),
            "StandingsTable": {
                "season": str(season),
                "round": str(represented_round),
                "StandingsLists": [
                    {
                        "season": str(season),
                        "round": str(represented_round),
                        "DriverStandings": standings,
                    }
                ],
            },
        }
    }


@pytest.fixture
def make_payload():
    return standings_payload


@pytest.fixture
def settings(tmp_path):
    return AcquisitionSettings(
        base_url="https://example.test/ergast/f1",
        cache_dir=tmp_path,
        page_size=2,
        timeout_seconds=1,
        max_attempts=3,
        request_interval_seconds=0,
        backoff_base_seconds=1,
        backoff_max_seconds=10,
    )


@pytest.fixture
def client_factory(settings):
    clients: list[httpx.Client] = []

    def create(handler):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        clients.append(client)
        return client

    yield create

    for client in clients:
        client.close()

