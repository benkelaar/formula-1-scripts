"""Jolpica HTTP acquisition with pagination, pacing, and retries."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable

import httpx

from . import __version__
from .config import AcquisitionSettings
from .source_models import ParsedPage, assemble_pages, parse_page


class AcquisitionError(RuntimeError):
    """Raised when Jolpica data cannot be acquired."""


@dataclass(frozen=True)
class FetchedSeason:
    season: int
    payload: dict[str, Any]


class JolpicaClient:
    """Small synchronous client for the driver standings endpoint."""

    def __init__(
        self,
        settings: AcquisitionSettings,
        *,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        random_value: Callable[[], float] = random.random,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.settings = settings
        self._sleep = sleep
        self._monotonic = monotonic
        self._random_value = random_value
        self._now = now
        self._last_request_at: float | None = None
        self._owns_client = client is None
        timeout = httpx.Timeout(settings.timeout_seconds)
        self._client = client or httpx.Client(
            timeout=timeout,
        )
        self._client.headers["User-Agent"] = (
            f"f1-alltime/{__version__} httpx/{httpx.__version__}"
        )

    def __enter__(self) -> JolpicaClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def fetch_season(self, season: int) -> FetchedSeason:
        """Fetch and assemble every standings page for one season."""

        if season < 1950:
            raise ValueError("Formula 1 seasons start in 1950")
        pages: list[ParsedPage] = []
        offset = 0
        while True:
            response = self._request(season, offset)
            try:
                payload = response.json()
            except ValueError as error:
                raise AcquisitionError(
                    f"invalid JSON returned by {response.request.url}"
                ) from error
            page = parse_page(payload, season)
            if page.offset != offset:
                raise AcquisitionError(
                    f"requested offset {offset}, received offset {page.offset}"
                )
            pages.append(page)
            collected = sum(len(item.standings) for item in pages)
            if collected >= page.total:
                break
            if not page.standings:
                raise AcquisitionError("pagination returned an empty page before completion")
            offset += len(page.standings)

        assembled = assemble_pages(pages, season)
        return FetchedSeason(season=season, payload=assembled)

    def _request(self, season: int, offset: int) -> httpx.Response:
        url = f"{self.settings.base_url.rstrip('/')}/{season}/driverstandings/"
        params = {"limit": self.settings.page_size, "offset": offset}
        last_error: Exception | None = None
        for attempt in range(1, self.settings.max_attempts + 1):
            self._pace()
            try:
                response = self._client.get(url, params=params)
            except (httpx.TimeoutException, httpx.NetworkError) as error:
                last_error = error
                if attempt == self.settings.max_attempts:
                    break
                self._sleep(self._backoff(attempt))
                continue

            if response.status_code < 400:
                return response
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == self.settings.max_attempts:
                    last_error = AcquisitionError(self._http_error(response))
                    break
                self._sleep(self._retry_delay(response, attempt))
                continue
            raise AcquisitionError(self._http_error(response))

        reason = str(last_error) if last_error else "unknown failure"
        raise AcquisitionError(
            f"request failed after {self.settings.max_attempts} attempts: {url}: {reason}"
        ) from last_error

    def _pace(self) -> None:
        now = self._monotonic()
        if self._last_request_at is not None:
            remaining = self.settings.request_interval_seconds - (now - self._last_request_at)
            if remaining > 0:
                self._sleep(remaining)
                now = self._monotonic()
        self._last_request_at = now

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                try:
                    retry_time = parsedate_to_datetime(retry_after)
                    return max(0.0, (retry_time - self._now()).total_seconds())
                except (TypeError, ValueError, OverflowError):
                    pass
        return self._backoff(attempt)

    def _backoff(self, attempt: int) -> float:
        base = self.settings.backoff_base_seconds * (2 ** (attempt - 1))
        jittered = base * (0.5 + self._random_value() * 0.5)
        return min(self.settings.backoff_max_seconds, jittered)

    @staticmethod
    def _http_error(response: httpx.Response) -> str:
        reason = response.reason_phrase or "HTTP error"
        return f"{response.status_code} {reason} from {response.request.url}"

