# Windows and PowerShell setup

## Install and synchronize

Install `uv` using one of the methods in the official `uv` documentation, then
open PowerShell in the repository root:

```powershell
uv python install 3.15
uv sync
```

`uv` reads `.python-version`, creates the local `.venv`, and installs the locked
runtime and development dependencies. Do not create a separate
`requirements.txt` workflow.

## Run tests

```powershell
uv run pytest
```

Tests use mocked HTTP transports and do not contact Jolpica.

## Fetch standings

```powershell
uv run f1-alltime fetch --from 1950 --to 2026
```

Existing season files are reused. To deliberately redownload a season or range:

```powershell
uv run f1-alltime fetch --from 2026 --to 2026 --refresh
```

Successful seasons are written to `data/raw/jolpica/<season>.json`. A range
fetch continues after individual season failures, retains successful results,
and exits nonzero with a failure summary. Every season uses the same cache and
refresh behavior. If downloading, validation, or writing fails, the previous
valid season file remains in place.

## Configuration options

The command supports `--cache-dir`, `--base-url`, `--timeout`,
`--max-attempts`, and `--request-interval`. See command help for details:

```powershell
uv run f1-alltime fetch --help
```

Cached API responses are excluded from Git and may be subject to Jolpica's data
license and terms independently of this repository's MIT license.

## Build the visual identity reference

After the requested season cache exists, build the separate driver reference:

```powershell
uv run f1-alltime build-identities --from 1950 --to 2026
```

The command writes `data/normalized/drivers.json` atomically. It does not alter
`data/derived/rankings.json`; future visual consumers join the two datasets by
exact `driver_id`.

Names, nationality mappings, local flag keys, and accessible bar colors are
configured in `config/identity.toml`. Narrow presentation corrections can be
added by exact Jolpica driver ID:

```toml
[drivers.example_driver_id]
given_name = "Preferred"
family_name = "Name"
nationality = "British"
```

in `config/identity-overrides.toml`. Overrides cannot merge driver IDs or
change rankings.

Flags and the font are reviewed repository files under `assets/`; the command
never downloads or generates them. It validates their manifest hashes,
licenses, SVG structure, and font metadata before publication. If mapped flags
are missing, every missing key and affected nationality is reported in one
error. Unknown future nationality labels instead receive the explicit neutral
fallback with a warning.

Asset sources and redistribution terms are recorded in
`assets/flags/LICENSE.md` and `assets/fonts/LICENSE.md`.
