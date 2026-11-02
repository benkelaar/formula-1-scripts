# 002 — Score cumulative all-time rankings

## Status

Implemented.

## Objective

Turn cached season-ending Jolpica standings into deterministic cumulative
all-time rankings. Each season is treated as one fictional event. This
increment implements scoring and ranking only; it does not resolve driver
identity, nationality, visual assets, or animation behavior.

## Inputs and command

Read the same per-season JSON files written by the acquisition increment. The
command is:

```powershell
uv run f1-alltime build-rankings --from 1950 --to 2026
```

The default cache directory is `data/raw/jolpica` and the default output is
`data/derived/rankings.json`. Every requested season must exist and pass the
existing source validation before an output file is published.

## Fictional scoring

Award points from the official `position` value only:

| Position | Points |
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

Non-numeric, non-positive, and out-of-range positions receive zero. Do not use
the source championship points or wins fields to derive an official position.

## Cumulative snapshots and ordering

Process seasons in ascending numeric order. A snapshot contains every driver
who has earned at least one cumulative fictional point by that season,
including scoring drivers who did not participate in the current season.
Drivers whose cumulative fictional score is zero are omitted. Accumulate by
exact, non-empty Jolpica `driverId`.

Order equal cumulative totals by:

1. descending championship count;
2. ascending first championship year, with no championship after any year;
3. ascending `driverId`.

Rank is the one-based position in this fully ordered list. The tie-break does
not change the cumulative point value.

## Deterministic output

Write canonical, UTF-8 JSON atomically with an explicit schema version. Store
the requested season range and one snapshot per season. Each snapshot row
contains `rank`, `driver_id`, `season_position` (or null when absent),
`fictional_points`, `cumulative_points`, `championship_count`, and
`first_championship_year`. The snapshot also records the SHA-256 hash of that
season's canonical cache bytes.

Given byte-identical cache inputs and the same season range, rebuilding must
produce byte-identical output. Input standing order must not affect ranking.

## Out of scope

- Canonical names, identity observation merging, and identity overrides.
- Nationality mapping, flags, colors, and fonts.
- CSV tailored for human presentation.
- Full-dataset semantic validation and audited historical overrides.
- Timeline, rendering, and video export.

## Tests and acceptance criteria

- Every points-table position and all zero-point cases are covered.
- Retired or absent drivers remain in later snapshots.
- Drivers remain excluded until they earn a fictional point.
- All three tie-break stages are covered.
- Reordering source standings does not alter output ordering.
- Missing or invalid cache input fails without replacing an existing output.
- Repeated builds from identical inputs are byte-equivalent.

