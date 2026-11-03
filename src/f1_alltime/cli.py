"""Command-line interface for acquiring Jolpica standings."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .acquisition import AcquisitionError, JolpicaClient
from .cache import CacheStore
from .config import AcquisitionSettings
from .identity import (
    IdentityValidationError,
    build_identities_from_cache,
    write_identities,
)
from .source_models import SourceValidationError
from .scoring import build_rankings_from_cache, write_rankings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="f1-alltime")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch", help="Fetch and cache season standings")
    _add_common_options(fetch)
    fetch.add_argument("--from", dest="start_season", type=int, default=1950)
    fetch.add_argument("--to", dest="end_season", type=int, default=2026)
    fetch.add_argument("--refresh", action="store_true")

    rankings = subparsers.add_parser(
        "build-rankings", help="Build cumulative fictional rankings from cached seasons"
    )
    rankings.add_argument("--cache-dir", type=Path, default=Path("data/raw/jolpica"))
    rankings.add_argument("--output", type=Path, default=Path("data/derived/rankings.json"))
    rankings.add_argument("--from", dest="start_season", type=int, default=1950)
    rankings.add_argument("--to", dest="end_season", type=int, default=2026)

    identities = subparsers.add_parser(
        "build-identities", help="Build the separate driver visual reference dataset"
    )
    identities.add_argument("--cache-dir", type=Path, default=Path("data/raw/jolpica"))
    identities.add_argument(
        "--output", type=Path, default=Path("data/normalized/drivers.json")
    )
    identities.add_argument("--from", dest="start_season", type=int, default=1950)
    identities.add_argument("--to", dest="end_season", type=int, default=2026)
    identities.add_argument(
        "--identity-config", type=Path, default=Path("config/identity.toml")
    )
    identities.add_argument(
        "--identity-overrides",
        type=Path,
        default=Path("config/identity-overrides.toml"),
    )
    identities.add_argument("--assets-root", type=Path, default=Path("."))
    identities.add_argument(
        "--asset-manifest", type=Path, default=Path("assets/manifest.json")
    )
    return parser


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cache-dir", type=Path, default=Path("data/raw/jolpica"))
    parser.add_argument("--base-url", default="https://api.jolpi.ca/ergast/f1")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--max-attempts", type=int, default=4)
    parser.add_argument("--request-interval", type=float, default=0.3)


def _settings(args: argparse.Namespace) -> AcquisitionSettings:
    return AcquisitionSettings(
        base_url=args.base_url,
        cache_dir=args.cache_dir,
        timeout_seconds=args.timeout,
        max_attempts=args.max_attempts,
        request_interval_seconds=args.request_interval,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "build-rankings":
            rankings = build_rankings_from_cache(
                args.cache_dir, args.start_season, args.end_season
            )
            sha256 = write_rankings(args.output, rankings)
            print(f"saved {args.output} sha256={sha256}")
            return 0
        if args.command == "build-identities":
            result = build_identities_from_cache(
                args.cache_dir,
                args.start_season,
                args.end_season,
                config_path=args.identity_config,
                overrides_path=args.identity_overrides,
                assets_root=args.assets_root,
                manifest_path=args.asset_manifest,
            )
            for warning in result.warnings:
                print(f"warning: {warning}", file=sys.stderr)
            sha256 = write_identities(args.output, result.dataset)
            print(
                f"saved {args.output} drivers={len(result.dataset['drivers'])} "
                f"warnings={len(result.warnings)} sha256={sha256}"
            )
            return 0
        settings = _settings(args)
        store = CacheStore(settings.cache_dir)
        return _fetch_seasons(args, settings, store)
    except (
        AcquisitionError,
        IdentityValidationError,
        SourceValidationError,
        ValueError,
        OSError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


def _fetch_seasons(
    args: argparse.Namespace, settings: AcquisitionSettings, store: CacheStore
) -> int:
    if args.end_season < args.start_season:
        raise ValueError("--to must be greater than or equal to --from")
    failures: list[tuple[int, str]] = []
    with JolpicaClient(settings) as client:
        for season in range(args.start_season, args.end_season + 1):
            if store.has_season(season) and not args.refresh:
                print(f"{season}: cached ({store.season_path(season)})")
                continue
            try:
                fetched = client.fetch_season(season)
                result = store.save(fetched)
                print(f"{season}: saved {result.path} sha256={result.sha256}")
            except (AcquisitionError, SourceValidationError, OSError) as error:
                failures.append((season, str(error)))
                print(f"{season}: failed: {error}", file=sys.stderr)
    if failures:
        print(f"error: {len(failures)} season(s) failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
