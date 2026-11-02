"""Atomic storage for season standings."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .acquisition import FetchedSeason


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON deterministically for storage and hashing."""

    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


@dataclass(frozen=True)
class CacheResult:
    path: Path
    sha256: str


class CacheStore:
    """Store seasons under a single inspectable cache directory."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def season_path(self, season: int) -> Path:
        return self.root / f"{season}.json"

    def has_season(self, season: int) -> bool:
        return self.season_path(season).is_file()

    def save(self, fetched: FetchedSeason) -> CacheResult:
        data = canonical_json_bytes(fetched.payload)
        self._write_bytes_atomic(self.season_path(fetched.season), data)
        return CacheResult(self.season_path(fetched.season), _sha256(data))

    def _write_bytes_atomic(self, path: Path, data: bytes) -> None:
        _write_bytes_atomic(path, data)


def _write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "wb") as temporary_file:
            temporary_file.write(data)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

