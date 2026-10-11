"""Load rules.yaml, the single place for limits, thresholds and weights."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "rules.yaml"


@lru_cache(maxsize=4)
def _load_cached(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_rules(path: Path | str | None = None) -> dict[str, Any]:
    """Return the parsed rules.yaml (cached per path)."""
    return _load_cached(str(path or RULES_PATH))


def repo_path(relative: str) -> Path:
    """Resolve a path from rules.yaml relative to the repo root."""
    return ROOT / relative
