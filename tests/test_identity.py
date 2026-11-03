from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from f1_alltime import cli
from f1_alltime.acquisition import FetchedSeason
from f1_alltime.cache import CacheStore, canonical_json_bytes
from f1_alltime.identity import (
    IdentityValidationError,
    build_identities_from_cache,
    contrast_ratio,
)


PROJECT_ROOT = Path(__file__).parents[1]
IDENTITY_CONFIG = PROJECT_ROOT / "config/identity.toml"
IDENTITY_OVERRIDES = PROJECT_ROOT / "config/identity-overrides.toml"
ASSET_MANIFEST = PROJECT_ROOT / "assets/manifest.json"


def _save_payload(cache_dir: Path, season: int, payload: dict) -> None:
    CacheStore(cache_dir).save(FetchedSeason(season, payload))


def _set_driver(
    payload: dict,
    index: int,
    *,
    given_name: str,
    family_name: str,
    nationality: str,
) -> None:
    driver = payload["MRData"]["StandingsTable"]["StandingsLists"][0][
        "DriverStandings"
    ][index]["Driver"]
    driver["givenName"] = given_name
    driver["familyName"] = family_name
    driver["nationality"] = nationality


def _build(cache_dir: Path, start: int, end: int, **kwargs):
    return build_identities_from_cache(
        cache_dir,
        start,
        end,
        config_path=IDENTITY_CONFIG,
        overrides_path=kwargs.pop("overrides_path", IDENTITY_OVERRIDES),
        assets_root=kwargs.pop("assets_root", PROJECT_ROOT),
        manifest_path=kwargs.pop("manifest_path", ASSET_MANIFEST),
        **kwargs,
    )


def test_builds_separate_reference_rows_with_historical_flags(tmp_path, make_payload):
    payload = make_payload(season=2025, total=3, driver_ids=("dutch", "east", "rhodesian"))
    _set_driver(payload, 0, given_name=" Max ", family_name="van  Test", nationality="Dutch")
    _set_driver(payload, 1, given_name="East", family_name="Driver", nationality="East German")
    _set_driver(payload, 2, given_name="Rhodesian", family_name="Driver", nationality="Rhodesian")
    _save_payload(tmp_path, 2025, payload)

    result = _build(tmp_path, 2025, 2025)
    rows = {row["driver_id"]: row for row in result.dataset["drivers"]}

    assert result.warnings == ()
    assert rows["dutch"] == {
        "driver_id": "dutch",
        "given_name": "Max",
        "family_name": "van Test",
        "display_name": "Max van Test",
        "nationality": "Dutch",
        "nationality_key": "dutch",
        "flag_key": "nl",
        "flag_path": "assets/flags/nl.svg",
        "bar_color": "#C45100",
    }
    assert rows["east"]["nationality_key"] == "east-germany"
    assert rows["east"]["flag_key"] == "de"
    assert rows["rhodesian"]["flag_key"] == "rhodesia"
    assert "rank" not in rows["dutch"]


def test_repeated_build_is_byte_equivalent(tmp_path, make_payload):
    payload = make_payload(season=2025, total=1, driver_ids=("one",))
    _set_driver(payload, 0, given_name="René", family_name="Test", nationality="French")
    _save_payload(tmp_path, 2025, payload)

    first = _build(tmp_path, 2025, 2025)
    second = _build(tmp_path, 2025, 2025)

    assert canonical_json_bytes(first.dataset) == canonical_json_bytes(second.dataset)


def test_conflicting_observations_require_scoped_override(tmp_path, make_payload):
    first = make_payload(season=2024, total=1, driver_ids=("same",))
    second = make_payload(season=2025, total=1, driver_ids=("same",))
    _set_driver(first, 0, given_name="First", family_name="Driver", nationality="British")
    _set_driver(second, 0, given_name="Second", family_name="Driver", nationality="British")
    _save_payload(tmp_path, 2024, first)
    _save_payload(tmp_path, 2025, second)

    with pytest.raises(IdentityValidationError, match="same: conflicting given_name"):
        _build(tmp_path, 2024, 2025)

    overrides = tmp_path / "overrides.toml"
    overrides.write_text('[drivers.same]\ngiven_name = "Preferred"\n', encoding="utf-8")
    result = _build(tmp_path, 2024, 2025, overrides_path=overrides)
    assert result.dataset["drivers"][0]["given_name"] == "Preferred"


def test_unknown_identity_uses_visible_fallback_and_warning(tmp_path, make_payload):
    payload = make_payload(season=2025, total=1, driver_ids=("mystery",))
    _set_driver(payload, 0, given_name="", family_name="", nationality="Unmapped")
    _save_payload(tmp_path, 2025, payload)

    result = _build(tmp_path, 2025, 2025)
    row = result.dataset["drivers"][0]

    assert row["display_name"] == "mystery"
    assert row["nationality_key"] == "unknown"
    assert row["flag_key"] == "unknown"
    assert result.warnings == (
        "mystery: missing name; using driver ID",
        "mystery: unmapped nationality 'Unmapped'; using fallback",
    )


def test_reports_all_missing_mapped_flags_before_publication(
    tmp_path, make_payload, capsys
):
    payload = make_payload(season=2025, total=2, driver_ids=("one", "two"))
    _set_driver(payload, 0, given_name="One", family_name="Driver", nationality="Dutch")
    _set_driver(payload, 1, given_name="Two", family_name="Driver", nationality="British")
    _save_payload(tmp_path / "cache", 2025, payload)
    output = tmp_path / "drivers.json"
    output.write_text("existing", encoding="utf-8")

    result = cli.main(
        [
            "build-identities",
            "--from",
            "2025",
            "--to",
            "2025",
            "--cache-dir",
            str(tmp_path / "cache"),
            "--output",
            str(output),
            "--identity-config",
            str(IDENTITY_CONFIG),
            "--identity-overrides",
            str(IDENTITY_OVERRIDES),
            "--assets-root",
            str(tmp_path),
            "--asset-manifest",
            str(ASSET_MANIFEST),
        ]
    )

    assert result == 1
    assert output.read_text(encoding="utf-8") == "existing"
    error = capsys.readouterr().err
    assert "missing mapped flags" in error
    assert "nl (Dutch)" in error
    assert "gb (British)" in error
    assert "unknown (fallback)" in error


def test_palette_contrast_and_dutch_orange():
    config = tomllib.loads(IDENTITY_CONFIG.read_text(encoding="utf-8"))
    background = config["background_color"]
    white = config["white_text_color"]

    for mapping in [config["fallback"], *config["nationalities"].values()]:
        color = mapping["bar_color"]
        assert contrast_ratio(color, white) >= 4.5
        assert contrast_ratio(color, background) >= 3.0

    assert config["nationalities"]["Dutch"]["bar_color"] == "#C45100"


def test_asset_manifest_hashes_every_referenced_file():
    manifest = json.loads(ASSET_MANIFEST.read_text(encoding="utf-8"))
    config = tomllib.loads(IDENTITY_CONFIG.read_text(encoding="utf-8"))
    flag_keys = {entry["flag_key"] for entry in config["nationalities"].values()}
    flag_keys.add(config["fallback"]["flag_key"])

    for flag_key in flag_keys:
        relative = f"assets/flags/{flag_key}.svg"
        assert relative in manifest["files"]
        assert (PROJECT_ROOT / relative).is_file()
    assert "assets/fonts/AtkinsonHyperlegibleNext-Variable.ttf" in manifest["files"]
