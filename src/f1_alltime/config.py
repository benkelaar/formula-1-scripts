"""Acquisition configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AcquisitionSettings:
    """Settings shared by Jolpica acquisition commands."""

    base_url: str = "https://api.jolpi.ca/ergast/f1"
    cache_dir: Path = Path("data/raw/jolpica")
    page_size: int = 100
    timeout_seconds: float = 20.0
    max_attempts: int = 4
    request_interval_seconds: float = 0.3
    backoff_base_seconds: float = 0.5
    backoff_max_seconds: float = 8.0

    def __post_init__(self) -> None:
        if not 1 <= self.page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.request_interval_seconds < 0:
            raise ValueError("request_interval_seconds cannot be negative")
        if self.backoff_base_seconds < 0 or self.backoff_max_seconds < 0:
            raise ValueError("backoff settings cannot be negative")

