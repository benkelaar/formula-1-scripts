# Formula 1 All-Time Championship Animation

Python tools for acquiring Formula 1 championship data and building the
cumulative fictional rankings used by a future all-time animation. Rendering
is not implemented yet.

## Quick start

```powershell
uv python install 3.15
uv sync
uv run pytest
uv run f1-alltime fetch --from 1950 --to 2026
uv run f1-alltime build-rankings --from 1950 --to 2026
uv run f1-alltime build-identities --from 1950 --to 2026
```

Cached responses are written to `data/raw/jolpica/`. Refresh any season or range
with the same command and the `--refresh` option.
Ranking output is written to `data/derived/rankings.json`.
The separate visual identity reference is written to
`data/normalized/drivers.json`. It contains names, nationality keys, local flag
references, and accessible colors keyed by `driver_id`; ranking rows remain
unchanged and contain no presentation fields.

See [the Windows setup guide](docs/setup-windows.md),
[the project design](DESIGN.md) and the delta specifications in `/specs` for details.

Jolpica data is governed by Jolpica's own terms; the application source is MIT
licensed.

