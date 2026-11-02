"""Command-line interface for acquiring Jolpica standings."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .acquisition import AcquisitionError, JolpicaClient
from .cache import CacheStore
from .config import AcquisitionSettings
from .source_models import SourceValidationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="f1-alltime")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch", help="Fetch and cache season standings")
    _add_common_options(fetch)
    fetch.add_argument("--from", dest="start_season", type=int, default=1950)
    fetch.add_argument("--to", dest="end_season", type=int, default=2026)
    fetch.add_argument("--refresh", action="store_true")
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
        settings = _settings(args)
        store = CacheStore(settings.cache_dir)
        return _fetch_seasons(args, settings, store)
    except (AcquisitionError, SourceValidationError, ValueError, OSError) as error:
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
