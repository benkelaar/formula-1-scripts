# TODO

## Later

- Add the animation timeline and interpolation.
- Add the static visual renderer.
- Add FFmpeg video export, preview presets, render
  metadata, and the final leaderboard hold.
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
- Wrote and implemented fictional scoring, cumulative rankings, deterministic
  tie-breaking, and atomic JSON export.
- Added year of first points as the third cumulative-ranking tie-breaker.
- Added the separate driver visual-reference dataset with stable names,
  nationality mapping, local licensed flags, accessible nationality colors,
  the orange Dutch palette entry, and a bundled variable font.
