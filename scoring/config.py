"""Load rules.yaml, the single place for limits, thresholds and weights."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "rules.yaml"


@lru_cache(maxsize=8)
def _load_cached(path: str, mtime_ns: int) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_rules(path: Path | str | None = None) -> dict[str, Any]:
    """Return the parsed rules.yaml.

    Cached per path AND file modification time, so an edited rules.yaml is
    picked up by a running app without a restart.
    """
    target = Path(path or RULES_PATH)
    return _load_cached(str(target), target.stat().st_mtime_ns)


def repo_path(*parts: str) -> Path:
    """Resolve a path from rules.yaml relative to the repo root."""
    return ROOT.joinpath(*parts)
