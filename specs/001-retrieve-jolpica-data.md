# 001 — Retrieve Formula 1 standings from Jolpica

## Status

Implemented.

## Objective

Build the data-acquisition boundary for downloading Formula 1 World Drivers'
Championship standings from the Jolpica F1 API and caching the exact responses
locally. Every season follows the same acquisition and cache workflow. This
increment does not implement normalization, fictional scoring, driver identity,
animation, or video rendering.

## Source endpoint

Use Jolpica's Ergast-compatible driver standings endpoint:

```text
GET https://api.jolpi.ca/ergast/f1/{season}/driverstandings/?limit=100&offset={offset}
```

The client must send a versioned custom `User-Agent`. The base URL, timeout,
retry settings, and client-side request pacing must be configurable.

## Scope

### In scope

- Create the Python project using Python 3.15 managed by `uv`.
- Define the package and command-line entry point.
- Fetch a configurable inclusive season range, defaulting to 1950–2026.
- Follow Jolpica's `MRData.total`, `limit`, and `offset` pagination metadata.
- Respect documented API limits with conservative client-side pacing.
- Retry transient connection failures, timeouts, HTTP 429, and HTTP 5xx
  responses using bounded exponential backoff with jitter.
- Fail immediately with an actionable message for non-retryable HTTP errors.
- Cache seasons as inspectable JSON files.
- Validate source-response structure before publishing cache files.
- Write cache files atomically so a failed refresh cannot damage valid data.
- Allow any configured season or range to be refreshed through the same command.
- Provide one command for fetching and refreshing season data.
- Unit and integration tests using mocked HTTP responses only.
- PowerShell instructions for setup and acquisition.

### Out of scope

- Converting source records into the application's normalized data schema.
- Resolving driver identity, nationality, flags, names, or colors.
- Calculating fictional points or cumulative rankings.
- Checking the semantic completeness of the complete 1950–2026 dataset beyond
  the acquisition invariants listed below.
- Animation, graphics, FFmpeg integration, or video export.
- Live API calls in the normal automated test suite.
- A database or background refresh service.

## Proposed structure

```text
pyproject.toml
.python-version
uv.lock
src/f1_alltime/
  __init__.py
  cli.py
  config.py
  acquisition.py
  cache.py
  source_models.py
tests/
  fixtures/jolpica/
  test_acquisition.py
  test_cache.py
docs/
  setup-windows.md
data/
  raw/jolpica/
```

Generated data directories must be excluded from Git. Small, curated response
fixtures required by tests remain version-controlled under `tests/fixtures`.

## Commands

Exact option spelling may change during implementation, but the supported
operations must remain separate:

```powershell
uv run f1-alltime fetch --from 1950 --to 2026
uv run f1-alltime fetch --from 2026 --to 2026 --refresh
```

Season files are reused by default. An explicit `--refresh` option may replace
any selected season only after the new response passes structural validation
and is safely written. The command prints each cache path and content hash.

## Cache layout

```text
data/
  raw/jolpica/
    1950.json
    ...
    2025.json
    2026.json
```

A season JSON file contains the lossless API payload assembled from all pages.
Page order must not alter the stored standings order. Later increments consume
cached files rather than make implicit live calls.

Hashes cover the canonical bytes of the stored response, not an in-memory
object.

## HTTP behavior

- Set both connection and read timeouts.
- Use one reusable `httpx.Client` per command.
- Include an application name and version in `User-Agent`.
- Request at most 100 results per page.
- Continue requesting pages until the number of collected results matches
  `MRData.total`.
- Pace requests below Jolpica's published unauthenticated burst limit.
- Honor `Retry-After` when present on HTTP 429.
- Otherwise use bounded exponential backoff with jitter.
- Limit retry attempts and report the final URL, status, and reason without
  exposing secrets.
- Never replace a valid cache file with an error body or partial response.

The implementation must not assume that one standings page is sufficient even
though a normal F1 season currently fits within the requested page size.

## Acquisition validation

Before publishing a fetched season, verify:

- the root contains `MRData`;
- pagination fields can be parsed as non-negative integers;
- the standings table exists and identifies the requested season;
- exactly one standings list exists for the requested season;
- the represented round is present and parseable;
- the driver standings collection is non-empty;
- collected pages contain the advertised number of records;
- each record has a non-empty `Driver.driverId`;
- driver IDs are unique within the season.

This increment deliberately preserves non-numeric positions, missing optional
driver fields, and other historically unusual source values. Their semantic
handling belongs to the normalization and validation increment.

## Failure and recovery

- When a season file already exists, ordinary fetch skips it and reports
  that it used the cache.
- A failed new download leaves no final cache file.
- A failed refresh keeps the previous valid file.
- Temporary files are written beside their intended destination and atomically
  renamed only after validation and hashing succeed.
- A multi-season fetch may retain successful seasons when another season fails,
  but exits nonzero and prints a concise failure summary.

## Tests

Use `pytest` and `respx` or `httpx.MockTransport`; tests must not depend on the
live API.

Required cases:

- a successful single-page season;
- multiple pages assembled without loss or duplication;
- a cache hit that makes no HTTP request;
- explicit refresh of an existing season;
- connection timeout followed by success;
- HTTP 429 honoring `Retry-After`;
- bounded retry exhaustion for HTTP 5xx;
- non-retryable HTTP 4xx;
- malformed JSON and missing response fields;
- requested/returned season mismatch;
- duplicate or missing driver IDs;
- advertised-total mismatch;
- atomic-write failure preserving an existing cache;
- deterministic hashes for identical stored content.

Clock, sleep, randomness, and HTTP transport must be injectable so these tests
are fast and deterministic.

## Documentation

Add concise Windows/PowerShell instructions for:

1. Installing `uv`.
2. Installing the managed Python version with `uv python install`.
3. Synchronizing dependencies with `uv sync`.
4. Running tests with `uv run pytest`.
5. Fetching and refreshing seasons.
6. Locating cached files and understanding that they may contain separately
   licensed Jolpica data.

## Acceptance criteria

- A clean Windows checkout can install Python and dependencies through `uv`.
- The configured season range can be downloaded with pagination, pacing,
  retries, validation, and clear error reporting.
- Re-running acquisition uses valid cached responses by default.
- Refreshing any season atomically replaces its previous cached response.
- Acquisition never leaves a partial final file or destroys a valid cache after
  failure.
- Mocked tests cover success, pagination, caching, retry, validation, and atomic
  failure paths without live network access.
- No scoring, identity, or rendering behavior is introduced in this increment.
