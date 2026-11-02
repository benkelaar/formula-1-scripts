from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from f1_alltime.acquisition import AcquisitionError, JolpicaClient
from f1_alltime.config import AcquisitionSettings


NOW = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)


def make_client(settings, http_client, *, sleeps=None):
    sleeps = sleeps if sleeps is not None else []
    return JolpicaClient(
        settings,
        client=http_client,
        sleep=sleeps.append,
        random_value=lambda: 0,
        now=lambda: NOW,
    )


def test_fetches_single_page(settings, client_factory, make_payload):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=make_payload(), request=request)

    with make_client(settings, client_factory(handler)) as client:
        result = client.fetch_season(2026)

    assert len(result.payload["MRData"]["StandingsTable"]["StandingsLists"][0]["DriverStandings"]) == 2
    assert requests[0].url.params["limit"] == "2"
    assert requests[0].url.params["offset"] == "0"
    assert requests[0].headers["User-Agent"].startswith("f1-alltime/")


def test_assembles_multiple_pages(settings, client_factory, make_payload):
    def handler(request):
        offset = int(request.url.params["offset"])
        ids = ("one", "two") if offset == 0 else ("three",)
        return httpx.Response(
            200,
            json=make_payload(offset=offset, total=3, driver_ids=ids),
            request=request,
        )

    with make_client(settings, client_factory(handler)) as client:
        result = client.fetch_season(2026)

    standings = result.payload["MRData"]["StandingsTable"]["StandingsLists"][0]["DriverStandings"]
    assert [item["Driver"]["driverId"] for item in standings] == ["one", "two", "three"]
    assert result.payload["MRData"]["limit"] == "3"
    assert result.payload["MRData"]["offset"] == "0"


def test_retries_timeout_then_succeeds(settings, client_factory, make_payload):
    attempts = 0
    sleeps = []

    def handler(request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectTimeout("timed out", request=request)
        return httpx.Response(200, json=make_payload(), request=request)

    with make_client(settings, client_factory(handler), sleeps=sleeps) as client:
        client.fetch_season(2026)

    assert attempts == 2
    assert sleeps == [0.5]


def test_honors_retry_after_for_429(settings, client_factory, make_payload):
    attempts = 0
    sleeps = []

    def handler(request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "2"}, request=request)
        return httpx.Response(200, json=make_payload(), request=request)

    with make_client(settings, client_factory(handler), sleeps=sleeps) as client:
        client.fetch_season(2026)

    assert sleeps == [2.0]


def test_exhausts_server_error_retries(settings, client_factory):
    settings = AcquisitionSettings(**{**settings.__dict__, "max_attempts": 2})
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(503, request=request)

    with make_client(settings, client_factory(handler)) as client:
        with pytest.raises(AcquisitionError, match="after 2 attempts"):
            client.fetch_season(2026)
    assert attempts == 2


def test_does_not_retry_client_error(settings, client_factory):
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(404, request=request)

    with make_client(settings, client_factory(handler)) as client:
        with pytest.raises(AcquisitionError, match="404"):
            client.fetch_season(2026)
    assert attempts == 1


def test_rejects_malformed_json(settings, client_factory):
    def handler(request):
        return httpx.Response(200, content=b"not json", request=request)

    with make_client(settings, client_factory(handler)) as client:
        with pytest.raises(AcquisitionError, match="invalid JSON"):
            client.fetch_season(2026)

