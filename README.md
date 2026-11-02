# Formula 1 All-Time Championship Animation

Python tools for acquiring the Formula 1 championship data used by a future
all-time driver-ranking animation. The current increment downloads and caches
Jolpica driver standings; scoring and rendering are not implemented yet.

## Quick start

```powershell
uv python install 3.15
uv sync
uv run pytest
uv run f1-alltime fetch --from 1950 --to 2026
```

Cached responses are written to `data/raw/jolpica/`. Refresh any season or range
with the same command and the `--refresh` option.

See [the Windows setup guide](docs/setup-windows.md),
[the project design](DESIGN.md), and
[specification 001](specs/001-retrieve-jolpica-data.md) for details.

Jolpica data is governed by Jolpica's own terms; the application source is MIT
licensed.

