# Formula 1 All-Time Championship Animation — Design

## Status

Project design. Implementation details are divided into numbered specifications.

## Objective

Build a Python application that turns the final World Drivers' Championship
order for each season into one fictional all-time championship. Each season is
scored as one event using the modern top-ten points table. The application will
produce a deterministic, polished 1920×1080 horizontal bar chart race from 1950
through a configurable end season such as 2026.

The same normalized data and computed rankings must remain usable by a future
interactive application. Rendering must never require live API access.

## Repository baseline

At the time this proposal was written, the repository contains only:

- `Agents.md`, defining a spec-driven development workflow.
- `LICENSE`, an MIT license.

There is no Python package, dependency definition, test suite, data cache, or
rendering code to preserve or migrate.

## Scope

### In scope

- Download season-ending driver standings from the Jolpica F1 API.
- Cache raw API responses by season and allow any selected season to refresh.
- Normalize standings and driver identities into stable, versioned files.
- Validate season coverage, positions, and driver IDs.
- Apply fictional points `25, 18, 15, 12, 10, 8, 6, 4, 2, 1` to official
  championship positions 1–10.
- Accumulate points and deterministic tie-break statistics by stable driver ID.
- Resolve display names, nationalities, colors, and local flag assets.
- Build an eased animation timeline and render an MP4 with FFmpeg.
- Provide fast preview renders and machine-readable ranking exports.
- Cover 1950 through 2026 by default, while keeping the range configurable.
- Unit and integration tests for the acquisition boundary, scoring, ranking,
  identities, validation, timeline, and a short render smoke test.
- Windows/PowerShell setup and reproducible usage documentation.

### Out of scope for the first version

- A web application or interactive viewer.
- Race-by-race animation within a season.
- Live timing or automatic background refreshes.
- Reconstructing official championship order from individual race results.
- Team-based colors that change when a driver changes constructor.
- Commentary, narration, music, or automated YouTube publishing.
- Manual manipulation of points or ranks to feature particular drivers.

## Interpretation of the all-time championship

For every included season, use the official driver championship position
reported by Jolpica. Award fictional points as follows:

| Championship position | Fictional points |
| ---: | ---: |
| 1 | 25 |
| 2 | 18 |
| 3 | 15 |
| 4 | 12 |
| 5 | 10 |
| 6 | 8 |
| 7 | 6 |
| 8 | 4 |
| 9 | 2 |
| 10 | 1 |
| Other, excluded, disqualified, or ineligible | 0 |

Points are accumulated by Jolpica `driverId`. A driver retains all accumulated
points indefinitely. No adjustment is made for the historical points system,
number of races, quality of competition, career length, or era.

### Official-position rule

The application does not derive season positions from reported season points.
It trusts the API's official `position`/`positionText`, because historical F1
championships used changing discard rules and tie-break regulations. A numeric
official position determines the fictional award. Non-numeric position text
such as `D`, `E`, or `-` receives zero and is retained in normalized data for
auditability.

### All-time tie rule

Drivers with equal cumulative fictional points are ordered by:

1. Most championships (official season finishes in first place, which receive
   25 fictional points).
2. Earliest first championship year, with drivers who have never won a
   championship ordered after drivers who have.
3. Ascending stable `driverId` as a deterministic last resort when neither
   championship count nor first championship year separates the drivers.

The exported rankings contain championship count and first championship year
so the result is explainable and reusable. Equal totals remain equal in the
displayed point label; the ordering rule only determines vertical placement.

## Data source and acquisition

### Source

Use Jolpica's Ergast-compatible endpoint:

```text
GET https://api.jolpi.ca/ergast/f1/{season}/driverstandings/?limit=100&offset=0
```

The client must send an application/version `User-Agent`. The endpoint returns
official standings, driver identity data, the represented round, and pagination
metadata. Jolpica currently documents a default limit of 30, a maximum request
limit of 100, offset pagination, an unauthenticated burst limit of four requests
per second, and a sustained limit of 500 per hour. These values are external
policy and must be configurable rather than scattered through the code.

One request per season should normally be enough, but acquisition must follow
`MRData.total`, `limit`, and `offset` until complete. Requests use finite
timeouts, bounded exponential backoff with jitter for transient failures and
HTTP 429, and actionable errors for permanent failures. A failed refresh must
never destroy a valid cached season.

Jolpica data is offered under terms separate from this repository's MIT code
license. Documentation must preserve source attribution, record the endpoint,
and note the API's non-commercial/share-alike data terms so publication usage
can be reviewed before release.

### Cache model

Use plain, inspectable files rather than a database:

```text
data/
  raw/
    jolpica/
      1950.json
      ...
      2025.json
      2026.json
  normalized/
    standings.jsonl
    drivers.json
  derived/
    rankings.json
    rankings.csv
assets/
  flags/
  fonts/
config/
  default.toml
  identity-overrides.toml
```

Season files are reused by default. A deliberate `--refresh` operation may
replace any selected season after validation. Scoring and rendering use the
cached season files and record their content hashes in generated outputs.
Rendering performs no HTTP calls.

### Proposed commands

Names are provisional but define the required separation of concerns:

```powershell
f1-alltime fetch --from 1950 --to 2026
f1-alltime fetch --from 2026 --to 2026 --refresh
f1-alltime validate
f1-alltime build-rankings
f1-alltime preview --seasons 1950,1988,2000,2026
f1-alltime render --output output/all-time.mp4
```

All seasons use the same cache layout, validation, refresh option, and downstream
processing. Antonelli and every other driver are treated identically: identity
is keyed by `driverId`, and fictional points come only from the official
position in the cached season data. No driver-specific scoring or placement
override is permitted.

## Validation

Validation runs after download and before normalized or derived files are
published atomically.

Required checks:

- Every configured season is present exactly once.
- The response's season matches the request.
- A standings list exists and contains at least one driver.
- Stable driver IDs are non-empty and unique within a season.
- Numeric positions are positive and unique within a season.
- Position and position text are consistent when both are numeric.
- Pagination yields the advertised total without duplicates.
- Required driver name and nationality fields have explicit fallback handling.
- Fictional season awards sum to 101 when numeric positions 1–10 all exist;
  otherwise the validator reports the exact missing/non-numeric positions and
  treats the season as an error unless an audited override is configured.
- Cumulative totals never decrease across seasons.
- Rebuilding from the same cached season files produces byte-equivalent
  normalized and ranking data, excluding intentionally variable build metadata.

Warnings and errors are distinct. Unknown nationality is a warning with a
visual fallback; missing/duplicate driver IDs or championship positions are
errors. Any historical correction must be made through a documented data or
identity override, never by silently editing derived output.

## Historical identity and nationality complications

Jolpica supplies nationality labels, not guaranteed ISO country codes. Labels
must be mapped explicitly to canonical identity keys and flag assets. Important
complications include:

- nationality spelling and demonym differences (`British` versus `GB`);
- drivers whose citizenship or represented nation changed over time;
- historical countries and flags that no longer exist;
- one driver appearing with inconsistent metadata across seasons;
- diacritics, suffixes, and preferred display-name differences;
- several drivers from one country intentionally sharing one country color;
- missing, ambiguous, or unsupported flag assets.

The first observed API response must not silently become canonical. Build a
driver registry keyed by `driverId`, merge observations, and fail validation on
conflicting core identity fields unless `identity-overrides.toml` resolves the
conflict. Overrides are version-controlled, narrowly scoped, and tested.

For the initial release, use one canonical nationality/flag per driver across
the whole animation. This gives the stable identity requested and avoids a flag
changing mid-career. The override file may choose a historically appropriate
identity. Supporting per-season nationality later requires a new spec because
it conflicts with a fully stable visual identity.

Flag assets must be local, licensed for redistribution, and attributed. Vendor
only the required set from one consistent SVG flag collection, then rasterize
to deterministic cached PNGs during an asset-build step. Do not download flags
during rendering. Unknown identities use a neutral globe/monogram fallback,
never an empty label or a broken-image marker.

## Driver colors

Assign one stable, accessible color to each canonical nationality. Every driver
with the same canonical nationality uses exactly the same color. Colors never
depend on driver, constructor, or season; the flag, name, and rank distinguish
drivers who share a country.

Palette generation must:

- meet a documented minimum contrast against the background;
- keep white point labels readable inside or beside bars;
- avoid relying on red/green distinction alone;
- remain deterministic when rendering only a subset of seasons;
- allow audited per-nationality overrides for accessibility, while preserving
  the rule that all drivers of that nationality share the resolved color.

Store the resolved color in the normalized driver registry so every output
consumer uses the same identity.

## Proposed architecture

Use Python 3.15 with a `src/` package and a small command-line interface:

```text
src/f1_alltime/
  cli.py             # command routing and user-facing errors
  config.py          # typed TOML configuration
  acquisition.py     # Jolpica HTTP client, retries, pagination
  cache.py           # atomic season storage
  models.py          # typed source, normalized, and ranking records
  normalize.py       # source parsing and identity observation merging
  identity.py        # nationality, flag, name, and color resolution
  scoring.py         # fictional awards, cumulative totals, tie-breaks
  validation.py      # dataset invariants and reports
  timeline.py        # frames, interpolation, easing, visibility
  render.py          # static frame composition
  video.py           # FFmpeg streaming/export and final hold
tests/
docs/
```

Dependencies should remain modest:

- `httpx` for explicit timeouts, headers, and testable HTTP transport;
- `pydantic` (or standard-library dataclasses plus explicit validation) for
  boundary models; choose one during the foundation increment, not both;
- `numpy` for vectorized interpolation;
- `pandas` only at import/export boundaries if it materially simplifies table
  work; core scoring should use typed records and remain easy to test;
- `matplotlib` with its non-interactive Agg backend for typography, shapes, and
  deterministic frame composition;
- `Pillow` for local raster asset preparation;
- `Typer` for a discoverable CLI, if its dependency cost is accepted;
- `pytest`, `respx`, and coverage tooling for tests;
- the system FFmpeg executable for H.264 MP4 encoding.

Matplotlib is preferred over a prebuilt bar-chart-race library. The desired
entry/exit transitions, flags, stable label layout, easing, and branded final
screen need direct scene control; a convenience library would be faster for a
prototype but harder to polish. A browser/canvas stack could improve complex
motion design, but would add a second language and headless-browser toolchain.
It is not justified for the first version. The renderer interface should remain
separate so a later Skia, Cairo, or web renderer can consume the same timeline.

Use `pyproject.toml` with a locked dependency workflow. `uv` is recommended for
fast Windows setup and deterministic locking, while standard virtual-environment
instructions may be documented as a fallback.

## Ranking and reusable data products

For every season and driver, the derived dataset contains at least:

- season;
- stable driver ID and resolved display name;
- official season position and fictional points awarded;
- cumulative fictional points;
- championship count, first championship year, and deterministic rank;
- canonical nationality key, flag asset key, and resolved color;
- source season-file hash.

Write JSON for lossless application reuse and CSV for inspection. Schema
versions are explicit. The animation consumes this derived data, not the raw
API response, which keeps acquisition, scoring, and presentation testable in
isolation.

## Visual design

### Canvas and hierarchy

- Default 1920×1080, 16:9, configurable.
- Near-black navy background with a restrained vignette or subtle grid.
- Warm off-white primary text and muted gray-blue secondary text.
- Thin red accent line inspired by motorsport timing graphics, without copying
  Formula 1 trademarks or broadcast layouts.
- Top-left title: `Formula 1 — The All-Time Championship`.
- Large right-aligned year display.
- Main field shows 15 bars with rank, flag, name, and cumulative total.
- Bottom edge contains a minimal progress line from start to end season.
- Safe margins preserve readability after YouTube compression and television
  overscan.

Bundle or require one redistributable variable sans-serif font so output does
not vary with the host's installed fonts. A condensed display face may be used
for the year, but no visual depends on proprietary Formula 1 fonts.

### Bar and label behavior

- Bar length encodes cumulative points from a zero baseline.
- Scale changes smoothly with a padded, eased maximum rather than snapping.
- Rank and flag sit in a fixed gutter; name follows in a stable label region.
- Point totals use tabular numerals and animate as rounded integers while the
  underlying value interpolates.
- When a short bar cannot contain its label, the value moves outside with a
  contrast-aware style.
- A faint trail or highlight may emphasize motion, but no glow may reduce text
  clarity.

### Motion model

Build a frame-independent timeline measured in seconds, then sample at the
configured FPS. Each season has:

1. a short settle/reading phase;
2. an eased transition to new totals and ranks;
3. optional pacing variation for milestone seasons, configured explicitly.

Use a monotonic ease-in-out curve (for example smootherstep) for bar totals and
vertical positions. Interpolate each driver's rank coordinate continuously so
overtakes are visible. Drivers entering the visible field begin just below the
last slot with zero opacity; departing drivers continue moving before fading.
Render a small overscan set around the top 15 to avoid popping at the boundary.

Interpolation is presentation only. Integer season endpoints must exactly equal
the derived ranking data.

### Timing

Default target duration is approximately 120 seconds:

- about 110 seconds for 77 season endpoints (1950–2026), roughly 1.43 seconds
  each including transition and settle time;
- 2 seconds for title/intro treatment;
- 8 seconds for the final leaderboard hold.

All timings are configurable. Preview mode may render selected seasons at
1280×720, 30 FPS, with shorter transitions. Production defaults to 1920×1080
and 60 FPS, subject to an early performance benchmark; 30 FPS remains a valid
quality preset for slower machines.

### Final screen

The final season transition uses the same honest ranking motion, then expands
into a cleaner leaderboard composition. Hold for a configurable duration before
a short fade to black. The final rank values are generated from the same derived
records as the preceding frame, preventing a mismatch between animation and
ending.

## Rendering and export

Render frames with the non-interactive backend and stream raw RGB frames to one
FFmpeg process; avoid writing thousands of PNGs by default. An optional debug
mode writes selected frames. Production encoding defaults should target broad
YouTube compatibility:

```text
H.264 (libx264), yuv420p, constant frame rate, fast-start MP4
```

The exact CRF/preset are configurable and recorded in a render manifest along
with configuration, application version, dataset hashes, resolution,
FPS, frame count, duration, font and asset versions, FFmpeg version, and output
SHA-256. Set explicit metadata and avoid wall-clock-dependent frame content so
the visual frame sequence is deterministic. Bit-identical MP4 bytes across
different FFmpeg builds are not promised; identical inputs must produce the
same frame sequence and rankings.

Check FFmpeg availability before an expensive render and report a PowerShell-
friendly installation hint when absent.

## Configuration

`config/default.toml` defines:

- start/end season;
- season range and cache path;
- visible driver count;
- width, height, FPS, and quality preset;
- transition, settle, intro, and final-hold durations;
- colors, typography, margins, and accessibility thresholds;
- cache/output directories;
- HTTP timeout, retry, and rate-limit settings;
- FFmpeg executable and encoding options;
- display timezone and date format.

CLI options override configuration explicitly. Every command prints the merged
configuration and stores it with generated artifacts. Paths are resolved
relative to the project/config file rather than the caller's current directory.

## Testing strategy

### Unit tests

- Every official position maps to the correct fictional score.
- Non-numeric and out-of-range positions score zero.
- Accumulation never loses retired drivers' points.
- Championship count, earliest first championship year, and driver-ID fallback
  resolve ties deterministically.
- Input row order cannot affect rankings or colors.
- Identity observations merge or raise expected conflicts.
- Nationality mappings, fallback flag, shared country colors, and contrast pass.
- Interpolation lands exactly on season endpoints and remains monotonic.
- Enter/exit visibility is stable around the top-15 boundary.

### Acquisition and validation tests

- Mock paginated responses, timeouts, 429 responses, retry exhaustion, and
  malformed JSON without contacting Jolpica.
- Verify conditional replacement and atomic season-file writes.
- Validate representative fixtures from early, mid-century, and modern seasons.
- Exercise excluded/disqualified/non-numeric position records.
- Confirm a failed refresh leaves the previous season file intact.

### Golden and smoke tests

- Store small normalized fixtures and expected ranking JSON.
- Render several deterministic key frames and compare perceptual hashes with a
  documented tolerance, avoiding brittle pixel equality across platforms.
- Run a short low-resolution animation through FFmpeg and assert dimensions,
  frame rate, duration, and final-frame metadata.

Live API checks are opt-in and never required by the normal test suite.

## Windows/PowerShell developer experience

The implementation documentation must cover:

1. Installing Python 3.15 and `uv` (with venv/pip fallback).
2. Installing FFmpeg and confirming `ffmpeg -version` on `PATH`.
3. Creating/syncing the environment from the lockfile.
4. Running tests and validation.
5. Fetching and selectively refreshing seasons.
6. Running a deterministic preview or full render from cached data.
7. Locating the MP4, ranking exports, validation report, and render manifest.

Commands must quote Windows paths safely and avoid assumptions about Bash.

## Implementation increments

Each increment should receive its own follow-up spec and be independently
reviewable and testable.

1. **Project foundation** — `pyproject.toml`, locked environment, `src/`
   package, typed configuration, CLI shell, logging, pytest, and Windows setup.
2. **Jolpica acquisition and cache** — HTTP boundary, custom user agent,
   pagination, retry/rate behavior, atomic season cache, and mocked tests.
3. **Normalization and validation** — source models, normalized schemas,
   season completeness checks, validation reports, and representative fixtures.
4. **Scoring and ranking** — fictional point table, cumulative history,
   championship-count and first-championship-year tie-breaks, deterministic
   exports, and golden tests.
5. **Driver identity and assets** — nationality mapping, overrides, licensed
   flag subset/build step, stable accessible colors, bundled font, and tests.
6. **Timeline engine** — duration model, rank/value/scale interpolation,
   entry/exit behavior, and timeline tests.
7. **Static visual renderer** — 1080p composition, typography, bars, flags,
   labels, year/progress treatments, accessibility and golden frame review.
8. **Video pipeline and preview** — frame streaming, FFmpeg checks/encoding,
   presets, render manifest, final leaderboard hold, and smoke tests.
9. **Historical verification and polish** — full 1950–2026 validation, identity
   audit, performance profiling, visual review, documentation, and final render.

No increment should preemptively implement later work. In particular, the
acquisition/scoring increments should produce inspectable outputs before
animation work begins.

## Acceptance criteria

The project is complete when:

- A clean Windows checkout can install from documented locked dependencies.
- Historical data from 1950 through the configured end season can be fetched,
  cached, validated, and rebuilt without live access.
- Refreshing any season atomically replaces its cache while preserving the
  existing file if the refresh fails.
- Scoring exactly follows the specified top-ten table and stable driver IDs.
- Rankings and tie-breaks are deterministic and covered by tests.
- A full validation report identifies missing or conflicting data before
  rendering.
- Drivers have stable names, local flags, and accessible nationality-inspired
  colors, with graceful fallbacks.
- Preview mode renders a small season selection quickly.
- Production rendering outputs a polished 1920×1080 MP4 with smooth overtakes,
  readable top-15 labels, prominent years, and a held final leaderboard.
- Antonelli is represented solely according to actual cached source data.
- The render manifest records the cached input hashes needed to reproduce the
  same rankings and frame sequence later.

## Review decisions requested

Before implementation, confirm or revise these choices:

1. Use championship count, then earliest first championship year, then
   `driverId` for equal cumulative totals.
2. Use one canonical nationality and flag per driver for the entire animation,
   with version-controlled overrides for historically ambiguous cases.
3. Use Python/Matplotlib/Agg plus FFmpeg rather than a browser renderer.
4. Target 60 FPS production by default, with 30 FPS as a supported preset.
5. Vendor a licensed subset of flag assets and a redistributable font so
   rendering is offline and visually stable.
6. Keep live acquisition, normalized/derived data, and rendering as separate
   commands, with production output using the current local cache.

Implementation must not begin until this proposal is reviewed and the first
follow-up increment is requested.
