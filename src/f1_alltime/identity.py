"""Deterministic driver presentation identities and local asset validation."""

from __future__ import annotations

import hashlib
import json
import re
import struct
import tomllib
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cache import CacheStore, _write_bytes_atomic, canonical_json_bytes
from .source_models import assemble_pages, parse_page


SCHEMA_VERSION = 1
_HEX_COLOR = re.compile(r"^#[0-9A-F]{6}$")
_SAFE_KEY = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_FONT_PATH = "assets/fonts/AtkinsonHyperlegibleNext-Variable.ttf"


class IdentityValidationError(ValueError):
    """Raised when identity observations, mappings, or assets are invalid."""


@dataclass(frozen=True)
class IdentityBuild:
    dataset: dict[str, Any]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class _Presentation:
    nationality_key: str
    flag_key: str
    bar_color: str


def build_identities_from_cache(
    cache_dir: Path,
    start_season: int,
    end_season: int,
    *,
    config_path: Path = Path("config/identity.toml"),
    overrides_path: Path = Path("config/identity-overrides.toml"),
    assets_root: Path = Path("."),
    manifest_path: Path = Path("assets/manifest.json"),
) -> IdentityBuild:
    """Build a separate visual reference dataset from cached standings."""

    if end_season < start_season:
        raise ValueError("--to must be greater than or equal to --from")
    config = _read_toml(config_path, "identity configuration")
    overrides = _load_overrides(overrides_path)
    mappings, fallback = _load_presentations(config)
    _validate_palette(config, mappings, fallback)

    observations: dict[str, dict[str, set[str]]] = {}
    source_seasons: list[dict[str, Any]] = []
    store = CacheStore(cache_dir)
    for season in range(start_season, end_season + 1):
        path = store.season_path(season)
        try:
            raw = path.read_bytes()
        except FileNotFoundError as error:
            raise IdentityValidationError(
                f"missing cached season {season}: {path}"
            ) from error
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise IdentityValidationError(
                f"invalid JSON for cached season {season}: {path}"
            ) from error
        page = parse_page(payload, season)
        assembled = assemble_pages([page], season)
        standings = assembled["MRData"]["StandingsTable"]["StandingsLists"][0][
            "DriverStandings"
        ]
        source_seasons.append(
            {
                "season": season,
                "source_sha256": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
            }
        )
        for standing in standings:
            driver = standing["Driver"]
            driver_id = driver["driverId"].strip()
            observed = observations.setdefault(
                driver_id,
                {"given_name": set(), "family_name": set(), "nationality": set()},
            )
            for source_key, output_key in (
                ("givenName", "given_name"),
                ("familyName", "family_name"),
                ("nationality", "nationality"),
            ):
                value = driver.get(source_key)
                observed[output_key].add(_normalize(value) if isinstance(value, str) else "")

    warnings: list[str] = []
    rows: list[dict[str, Any]] = []
    used_mappings: dict[str, _Presentation] = {}
    for driver_id in sorted(observations):
        observed = observations[driver_id]
        override = overrides.get(driver_id, {})
        given_name = _resolve_field(driver_id, "given_name", observed["given_name"], override)
        family_name = _resolve_field(
            driver_id, "family_name", observed["family_name"], override
        )
        nationality = _resolve_field(
            driver_id, "nationality", observed["nationality"], override
        )
        display_name = " ".join(part for part in (given_name, family_name) if part)
        if not display_name:
            display_name = driver_id
            warnings.append(f"{driver_id}: missing name; using driver ID")

        presentation = mappings.get(nationality)
        if presentation is None:
            presentation = fallback
            warnings.append(
                f"{driver_id}: unmapped nationality {nationality!r}; using fallback"
            )
        else:
            used_mappings[nationality] = presentation
        rows.append(
            {
                "driver_id": driver_id,
                "given_name": given_name,
                "family_name": family_name,
                "display_name": display_name,
                "nationality": nationality,
                "nationality_key": presentation.nationality_key,
                "flag_key": presentation.flag_key,
                "flag_path": f"assets/flags/{presentation.flag_key}.svg",
                "bar_color": presentation.bar_color,
            }
        )

    _validate_assets(
        assets_root,
        manifest_path,
        used_mappings,
        fallback,
    )
    unknown_overrides = sorted(set(overrides) - set(observations))
    if unknown_overrides:
        warnings.extend(f"unused override for unknown driver {value}" for value in unknown_overrides)

    dataset = {
        "schema_version": SCHEMA_VERSION,
        "from_season": start_season,
        "to_season": end_season,
        "source_seasons": source_seasons,
        "drivers": rows,
    }
    return IdentityBuild(dataset, tuple(sorted(warnings)))


def write_identities(path: Path, dataset: dict[str, Any]) -> str:
    """Atomically publish canonical identity JSON and return its SHA-256."""

    data = canonical_json_bytes(dataset)
    _write_bytes_atomic(path, data)
    return hashlib.sha256(data).hexdigest()


def contrast_ratio(first: str, second: str) -> float:
    """Return the WCAG relative-luminance contrast ratio for two hex colors."""

    high, low = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _read_toml(path: Path, label: str) -> dict[str, Any]:
    try:
        with path.open("rb") as file:
            value = tomllib.load(file)
    except FileNotFoundError as error:
        raise IdentityValidationError(f"missing {label}: {path}") from error
    except tomllib.TOMLDecodeError as error:
        raise IdentityValidationError(f"invalid {label} {path}: {error}") from error
    if not isinstance(value, dict):
        raise IdentityValidationError(f"{label} must contain a TOML table")
    return value


def _load_presentations(
    config: dict[str, Any],
) -> tuple[dict[str, _Presentation], _Presentation]:
    if config.get("schema_version") != 1:
        raise IdentityValidationError("identity config schema_version must be 1")
    table = config.get("nationalities")
    if not isinstance(table, dict):
        raise IdentityValidationError("identity config has no nationalities table")
    mappings = {
        label: _parse_presentation(value, f"nationality {label!r}")
        for label, value in table.items()
    }
    fallback = _parse_presentation(config.get("fallback"), "fallback")
    return mappings, fallback


def _parse_presentation(value: Any, label: str) -> _Presentation:
    if not isinstance(value, dict):
        raise IdentityValidationError(f"{label} must be a table")
    nationality_key = value.get("key") or value.get("nationality_key")
    flag_key = value.get("flag_key")
    color = value.get("bar_color")
    if not isinstance(nationality_key, str) or not _SAFE_KEY.fullmatch(nationality_key):
        raise IdentityValidationError(f"{label} has an unsafe nationality key")
    if not isinstance(flag_key, str) or not _SAFE_KEY.fullmatch(flag_key):
        raise IdentityValidationError(f"{label} has an unsafe flag key")
    if not isinstance(color, str) or not _HEX_COLOR.fullmatch(color):
        raise IdentityValidationError(f"{label} has an invalid uppercase hex color")
    return _Presentation(nationality_key, flag_key, color)


def _load_overrides(path: Path) -> dict[str, dict[str, str]]:
    config = _read_toml(path, "identity overrides")
    drivers = config.get("drivers", {})
    if not isinstance(drivers, dict):
        raise IdentityValidationError("identity overrides drivers value must be a table")
    parsed: dict[str, dict[str, str]] = {}
    allowed = {"given_name", "family_name", "nationality"}
    for driver_id, values in drivers.items():
        if not isinstance(driver_id, str) or not driver_id.strip() or not isinstance(values, dict):
            raise IdentityValidationError("identity override keys must be non-empty driver IDs")
        unsupported = sorted(set(values) - allowed)
        if unsupported:
            raise IdentityValidationError(
                f"{driver_id}: unsupported override field(s): {', '.join(unsupported)}"
            )
        if any(not isinstance(value, str) for value in values.values()):
            raise IdentityValidationError(f"{driver_id}: override values must be strings")
        parsed[driver_id] = {key: _normalize(value) for key, value in values.items()}
    return parsed


def _resolve_field(
    driver_id: str,
    field: str,
    observations: set[str],
    override: dict[str, str],
) -> str:
    if field in override:
        return override[field]
    non_empty = sorted(value for value in observations if value)
    if len(non_empty) > 1:
        choices = ", ".join(repr(value) for value in non_empty)
        raise IdentityValidationError(f"{driver_id}: conflicting {field}: {choices}")
    return non_empty[0] if non_empty else ""


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFC", " ".join(value.strip().split()))


def _validate_palette(
    config: dict[str, Any],
    mappings: dict[str, _Presentation],
    fallback: _Presentation,
) -> None:
    background = config.get("background_color")
    white = config.get("white_text_color")
    if not isinstance(background, str) or not _HEX_COLOR.fullmatch(background):
        raise IdentityValidationError("identity config has an invalid background_color")
    if not isinstance(white, str) or not _HEX_COLOR.fullmatch(white):
        raise IdentityValidationError("identity config has an invalid white_text_color")
    for label, presentation in [*mappings.items(), ("fallback", fallback)]:
        if contrast_ratio(presentation.bar_color, white) < 4.5:
            raise IdentityValidationError(f"{label}: bar color has less than 4.5:1 white contrast")
        if contrast_ratio(presentation.bar_color, background) < 3.0:
            raise IdentityValidationError(
                f"{label}: bar color has less than 3:1 background contrast"
            )
    dutch = mappings.get("Dutch")
    if dutch is None or not _is_orange(dutch.bar_color):
        raise IdentityValidationError("Dutch bar color must be recognizably orange")


def _is_orange(value: str) -> bool:
    red, green, blue = _rgb(value)
    return red >= 140 and 45 <= green <= 130 and blue <= 45 and red > green * 1.4


def _luminance(value: str) -> float:
    channels = []
    for channel in _rgb(value):
        component = channel / 255
        channels.append(
            component / 12.92
            if component <= 0.04045
            else ((component + 0.055) / 1.055) ** 2.4
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _rgb(value: str) -> tuple[int, int, int]:
    return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))  # type: ignore[return-value]


def _validate_assets(
    root: Path,
    manifest_path: Path,
    mappings: dict[str, _Presentation],
    fallback: _Presentation,
) -> None:
    manifest_file = manifest_path if manifest_path.is_absolute() else root / manifest_path
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise IdentityValidationError(f"missing asset manifest: {manifest_file}") from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise IdentityValidationError(f"invalid asset manifest: {manifest_file}") from error
    expected = manifest.get("files") if isinstance(manifest, dict) else None
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != 1
        or not isinstance(expected, dict)
    ):
        raise IdentityValidationError("asset manifest schema_version must be 1")

    flag_labels: dict[str, list[str]] = {}
    for label, presentation in mappings.items():
        flag_labels.setdefault(presentation.flag_key, []).append(label)
    flag_labels.setdefault(fallback.flag_key, []).append("fallback")
    missing = []
    for flag_key, labels in sorted(flag_labels.items()):
        relative = f"assets/flags/{flag_key}.svg"
        if not (root / relative).is_file():
            missing.append(f"{flag_key} ({', '.join(sorted(labels))})")
    if missing:
        raise IdentityValidationError("missing mapped flags: " + "; ".join(missing))

    required = [f"assets/flags/{key}.svg" for key in flag_labels]
    required.append(_FONT_PATH)
    for relative in sorted(required):
        path = root / relative
        declared_hash = expected.get(relative)
        if not isinstance(declared_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", declared_hash):
            raise IdentityValidationError(f"asset has no valid manifest hash: {relative}")
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != declared_hash:
            raise IdentityValidationError(f"asset hash mismatch: {relative}")
        if relative.endswith(".svg"):
            try:
                root_element = ET.parse(path).getroot()
            except ET.ParseError as error:
                raise IdentityValidationError(f"malformed SVG: {relative}") from error
            if root_element.tag.rsplit("}", 1)[-1] != "svg":
                raise IdentityValidationError(f"asset is not an SVG: {relative}")

    for license_path in (
        "assets/flags/LICENSE.md",
        "assets/flags/LICENSE.flag-icons.txt",
        "assets/fonts/LICENSE.md",
        "assets/fonts/OFL.txt",
    ):
        if not (root / license_path).is_file():
            raise IdentityValidationError(f"missing asset license record: {license_path}")
    _validate_font(root / _FONT_PATH)


def _validate_font(path: Path) -> None:
    data = path.read_bytes()
    if len(data) < 12 or data[:4] not in (b"\x00\x01\x00\x00", b"OTTO"):
        raise IdentityValidationError(f"invalid TrueType/OpenType font: {path}")
    table_count = struct.unpack_from(">H", data, 4)[0]
    tables: dict[bytes, bytes] = {}
    for index in range(table_count):
        offset = 12 + index * 16
        tag, _, table_offset, length = struct.unpack_from(">4sIII", data, offset)
        if table_offset + length > len(data):
            raise IdentityValidationError(f"font contains an invalid {tag!r} table")
        tables[tag] = data[table_offset : table_offset + length]
    if b"name" not in tables or b"fvar" not in tables:
        raise IdentityValidationError("font lacks required name or variable-axis table")
    if "Atkinson Hyperlegible Next" not in _font_names(tables[b"name"]):
        raise IdentityValidationError("font family is not Atkinson Hyperlegible Next")
    if _font_weight_range(tables[b"fvar"]) != (200.0, 800.0):
        raise IdentityValidationError("font weight range must be 200–800")
    feature_tags = _layout_feature_tags(tables.get(b"GSUB", b"")) | _layout_feature_tags(
        tables.get(b"GPOS", b"")
    )
    if b"tnum" not in feature_tags:
        raise IdentityValidationError("font does not expose tabular numerals")


def _font_names(table: bytes) -> set[str]:
    _, count, string_offset = struct.unpack_from(">HHH", table, 0)
    names = set()
    for index in range(count):
        platform, _, _, name_id, length, offset = struct.unpack_from(">HHHHHH", table, 6 + 12 * index)
        if name_id not in (1, 4, 6, 16):
            continue
        raw = table[string_offset + offset : string_offset + offset + length]
        try:
            names.add(raw.decode("utf-16-be" if platform in (0, 3) else "latin-1"))
        except UnicodeDecodeError:
            continue
    return names


def _font_weight_range(table: bytes) -> tuple[float, float] | None:
    _, offset, _, axis_count, axis_size, _, _ = struct.unpack_from(">IHHHHHH", table, 0)
    for index in range(axis_count):
        axis_offset = offset + index * axis_size
        tag, minimum, _, maximum = struct.unpack_from(">4siii", table, axis_offset)
        if tag == b"wght":
            return minimum / 65536, maximum / 65536
    return None


def _layout_feature_tags(table: bytes) -> set[bytes]:
    if len(table) < 10:
        return set()
    feature_offset = struct.unpack_from(">H", table, 6)[0]
    if feature_offset + 2 > len(table):
        return set()
    count = struct.unpack_from(">H", table, feature_offset)[0]
    tags = set()
    for index in range(count):
        record = feature_offset + 2 + index * 6
        if record + 6 <= len(table):
            tags.add(table[record : record + 4])
    return tags
