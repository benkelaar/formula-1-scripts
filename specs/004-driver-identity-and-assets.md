# 004 — Resolve driver identity and presentation assets

## Status

Implemented.

## Objective

Turn the identity observations already present in the cached 1950–2026
standings into a deterministic visual reference dataset containing stable
display names, canonical nationalities, local flag keys, and accessible
nationality colors. Keep this presentation data separate from the existing
rankings. Vendor one redistributable font and the required flag subset so later
rendering remains offline and independent of host fonts.

The current cache contains 819 driver IDs and 40 nationality labels. No driver
currently has conflicting observed name or nationality values, but conflict and
fallback behavior must still be explicit and tested.

## Identity registry and command

Add:

```powershell
uv run f1-alltime build-identities --from 1950 --to 2026
```

Read and validate the requested cached seasons through the existing cache
boundary. Write canonical UTF-8 JSON atomically to
`data/normalized/drivers.json`, with an explicit schema version and the source
season hashes needed to reproduce it. This is a reference dataset keyed by
`driver_id`; it is not part of the ranking schema.

The command does not retrieve, generate, or modify flag assets. It checks the
resolved mappings against the flags already committed to `assets/flags/` and
reports all missing flag keys and affected nationality labels together. A
missing mapped flag fails the build before replacing an existing reference
dataset; an unknown nationality uses the explicit fallback and emits a warning.

Create one row per observed `driverId`. Merge exact repeated observations and
record:

- `driver_id`;
- NFC-normalized `given_name` and `family_name`, preserving the two source
  identity fields after trimming;
- NFC-normalized `display_name`, formed from `given_name` and `family_name`;
- the observed Jolpica nationality label;
- `nationality_key`, using an explicit version-controlled mapping;
- `flag_key` and a relative local SVG path;
- an uppercase six-digit `bar_color` hex value.

Input order must not affect output. Conflicting non-empty names or
nationalities for one driver are errors unless a narrowly scoped entry in
`config/identity-overrides.toml` selects the canonical value. Missing names use
the driver ID as a visible `display_name` fallback while retaining explicit
empty source-name fields. Missing or unmapped nationalities use an `unknown`
key, neutral color, and bundled fallback globe asset with a warning. Overrides
may resolve presentation identity only; they cannot merge driver IDs or alter
scores and ranks.

## Nationality mapping and colors

Add a checked-in mapping for all 40 nationality labels currently observed.
Canonical keys use stable lowercase ASCII country or historical-territory keys,
not display demonyms. `East German` and `Rhodesian` remain distinct historical
keys rather than being silently rewritten to modern states. The cached East
German observations are from 1952–1953, when both German states used the same
black-red-gold tricolor, so `east-germany` deliberately references the same
flag artwork as `germany` while remaining a separate nationality key. Use the
1968–1979 Rhodesian flag as the single stable visual identity for `rhodesia`;
do not substitute the current Zimbabwean flag or change it between seasons.

Store the palette explicitly in version control. Every driver with the same
`nationality_key` receives the same color, regardless of season, constructor,
or selected build range. Each color must reach WCAG 2.1 contrast ratio 4.5:1
against white text and 3:1 against the configured near-black background. Tests
calculate these ratios from the stored hex values. Color is supplementary to
the written name and flag; no distinction relies on red versus green alone.
The `dutch` nationality color must be recognizably orange, not red, yellow,
blue, or a neutral shade, while meeting both contrast thresholds.

## Local assets and licensing

Vendor only the mapped 4×3 flag SVGs from `lipis/flag-icons` version 7.6.0
(MIT), the Wikimedia Commons 2:3 SVG of the 1968–1979 Rhodesian flag (public
domain), and one neutral fallback under `assets/flags/`. Preserve each
upstream source, license or public-domain rationale, original filename, and
downloaded-file SHA-256 in `assets/flags/LICENSE.md`. Add these as reviewed,
version-controlled repository files during implementation; no application
command downloads them.

Vendor the upright Atkinson Hyperlegible Next version 2.001 variable font under
`assets/fonts/`, together with its SIL Open Font License 1.1. Validate that the
font exposes the required family name, variable weight range, and tabular
numerals. Record the exact source and file SHA-256 in
`assets/fonts/LICENSE.md`. This increment only establishes and validates the
font asset; typography layout is part of the static-renderer increment.

Asset validation reports every referenced missing flag in one run rather than
stopping at the first. It fails for a missing file, unsafe path, malformed SVG,
missing license record, or changed file hash. Identity generation performs no
network requests and there is no flag-retrieval command in this increment.

## Separation from rankings

Do not modify `build-rankings`, the ranking schema, or existing ranking output.
In particular, ranking rows retain only `driver_id` as their identity reference
and must not contain `given_name`, `family_name`, or `display_name`. The visual
reference dataset is built and validated independently. Later visual consumers
will join `data/derived/rankings.json` to
`data/normalized/drivers.json` by exact `driver_id` and must report a missing
reference instead of silently changing ranking data. That consumer-side join is
out of scope for this increment.

## Documentation

Document the identity build, its independence from rankings, local asset
provenance, override format, warnings/failures, and the command for rebuilding
the reference dataset from the cache. Dependency changes, if any, must be made
with `uv` and locked; prefer the standard library when it is sufficient.

## Out of scope

- Per-season nationality or flag changes.
- Driver portraits, constructor identity, or driver-specific colors.
- Downloading assets at render time.
- Downloading or generating flags through `build-identities` or another CLI
  command.
- PNG rasterization, typography layout, static frames, animation, or video.
- CSV presentation exports or a general asset-management framework.
- Hand-authoring unsupported historical flag artwork.
- Enriching, rewriting, or otherwise changing ranking output.
- Joining rankings to the visual reference dataset in a renderer or export.

## Acceptance criteria

- The full cached range deterministically produces one registry row for each of
  the 819 observed driver IDs and covers all 40 observed nationality labels.
- Reordered seasons and standings produce a byte-identical visual reference
  dataset.
- Exact repeated observations merge; unresolved core-identity conflicts fail;
  a scoped override resolves the matching conflict only.
- Missing identity data and unknown future nationality mappings use visible,
  deterministic fallbacks and warnings rather than broken or empty
  presentation fields.
- East German observations use the period-correct plain German tricolor;
  Rhodesian observations use the locally vendored public-domain 1968–1979
  historical flag rather than a modern-state substitution.
- Every mapped color is shared by nationality and passes the documented
  contrast tests.
- The resolved Dutch color is visibly orange and passes the same automated
  contrast checks.
- Every referenced flag and font is local, hash-validated, and accompanied by
  its redistribution license and source attribution.
- `build-identities` performs no network access and reports all missing mapped
  flags with their affected nationalities before failing atomically.
- Existing ranking code, schema, and generated output remain unchanged.
- Given name, family name, and display name are available from the visual
  reference dataset by `driver_id` and remain absent from ranking rows.
- Failed identity or asset validation leaves existing generated outputs intact.
- Unit and CLI tests run offline and cover mapping, overrides, fallbacks,
  conflicts, contrast, asset validation, and deterministic output.
