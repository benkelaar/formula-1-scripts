# TODO

## Next

- Write and implement a spec for fictional scoring, cumulative rankings, and
  deterministic tie-breaking.

## Later

- Write and implement a spec for driver identity, nationality mapping, local
  flag assets, accessible colors, and fonts.
- Write and implement a spec for the animation timeline and interpolation.
- Write and implement a spec for the static visual renderer.
- Write and implement a spec for FFmpeg video export, preview presets, render
  metadata, and the final leaderboard hold.
- Audit the complete 1950–2026 dataset and identity overrides.
- Produce and review the final 1080p animation.
- Revisit an interactive web application after the reusable data pipeline is
  stable.

## Done

- Added the repository development workflow.
- Wrote the overall architecture and visual design in `DESIGN.md`.
- Scoped the first numbered specification to Jolpica data acquisition.
- Implemented the `uv`-managed Python project foundation.
- Implemented Jolpica pagination, pacing, retries, validation, and historical
  caching.
- Implemented atomic replacement for refreshed season caches.
- Added mocked acquisition, cache, validation, and CLI tests.
- Added the minimal README and Windows/PowerShell setup documentation.
- Unified every season under one cache format, fetch command, and refresh path.
- Validated all cached 1950–2026 standings for coverage, source structure,
  top-ten positions, driver IDs, points, and identity-field completeness.
