"""CPCB class B limits and per-reading breach / exceedance (Appendix A)."""

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

import pandas as pd

from scoring.config import load_rules, repo_path
from scoring.loader import VALUE


@dataclass(frozen=True)
class Limit:
    """One scored parameter's class B limit."""

    parameter: str
    rule: str  # "min", "max" or "range"
    low: float | None
    high: float | None
    scale: float
    unit: str

    def distance_outside(self, value: float) -> float:
        """How far the value is past the limit (0 if within)."""
        below = self.low - value if self.low is not None else 0.0
        above = value - self.high if self.high is not None else 0.0
        return max(below, above, 0.0)


class Evaluation(TypedDict):
    breach: bool
    exceedance: float


def limits_from_rules(rules: dict[str, Any] | None = None) -> dict[str, Limit]:
    """Build Limit objects from rules.yaml scored_parameters."""
    rules = rules or load_rules()
    return {
        name: Limit(name, spec["rule"], spec.get("low"), spec.get("high"),
                    float(spec["scale"]), spec.get("unit", ""))
        for name, spec in rules["scored_parameters"].items()
    }


def parse_criteria_limit(limit_type: str, limit: str) -> tuple[float | None, float | None]:
    """Turn a criteria row into (low, high), e.g. ("range", "6.5-8.5") -> (6.5, 8.5)."""
    kind = limit_type.strip().lower()
    if kind == "range":
        low, high = limit.split("-")
        return float(low), float(high)
    if kind == "min":
        return float(limit), None
    if kind == "max":
        return None, float(limit)
    raise ValueError(f"Unknown limit_type {limit_type!r}")


def read_criteria_csv(path: Path | str, class_name: str) -> dict[str, tuple]:
    """Map parameter name -> (limit_type, low, high) for one CPCB class."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    rows = df[df["class"].str.strip().str.upper() == class_name.upper()]
    out = {}
    for r in rows.itertuples():
        low, high = parse_criteria_limit(r.limit_type, r.limit)
        out[r.parameter.strip()] = (r.limit_type.strip().lower(), low, high)
    return out


def load_limits(path: Path | str | None = None, rules: dict[str, Any] | None = None
                ) -> dict[str, Limit]:
    """Load class B limits for the scored parameters, checked against CPCB.

    Raises ValueError if a scored parameter is absent from the criteria CSV's
    class B rows or its limit differs from rules.yaml. If the CSV itself is
    absent, the rules.yaml limits are used.
    """
    rules = rules or load_rules()
    limits = limits_from_rules(rules)
    path = Path(path) if path else repo_path(rules["data"]["limits_csv"])
    if not path.exists():
        return limits
    criteria = read_criteria_csv(path, str(rules["limits_csv"]["class_name"]))
    for name, spec in rules["scored_parameters"].items():
        official = criteria.get(spec["criteria_name"])
        mine = (limits[name].rule, limits[name].low, limits[name].high)
        if official != mine:
            raise ValueError(f"{name}: rules.yaml {mine} != CPCB criteria CSV {official}")
    return limits


def evaluate(parameter: str, value: float, limits: dict[str, Limit] | None = None) -> Evaluation:
    """Breach flag and exceedance (0..1) for one valid reading.

    Raises ValueError for a missing value: missing must never be scored as clean.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        raise ValueError("Cannot evaluate a missing reading; it is not clean.")
    limit = (limits or limits_from_rules())[parameter]
    distance = limit.distance_outside(float(value))
    return {"breach": distance > 0, "exceedance": min(distance / limit.scale, 1.0)}


def worsen(limit: Limit, pre: float, later: float) -> float:
    """How much a reading got worse from pre to a later phase, clipped to 0..1.

    DO: (pre - later) / 5.  BOD: (later - pre) / 3.
    pH: (distance outside range later - distance outside range pre) / 1.5.
    Improvement scores 0.
    """
    if limit.rule == "min":
        change = pre - later
    elif limit.rule == "max":
        change = later - pre
    else:
        change = limit.distance_outside(later) - limit.distance_outside(pre)
    return min(max(change / limit.scale, 0.0), 1.0)


def limit_text(limit: Limit) -> str:
    """Plain-words limit, e.g. "at least 5 mg/l" or "6.5 to 8.5"."""
    unit = f" {limit.unit}" if limit.unit else ""
    if limit.rule == "min":
        return f"at least {limit.low:g}{unit}"
    if limit.rule == "max":
        return f"at most {limit.high:g}{unit}"
    return f"{limit.low:g} to {limit.high:g}{unit}"


def evaluate_frame(df: pd.DataFrame, limits: dict[str, Limit] | None = None) -> pd.DataFrame:
    """Add `breach` (True/False/NA) and `exceedance` columns for scored rows.

    Non-scored parameters and non-value rows get NA: never False.
    """
    limits = limits or limits_from_rules()
    out = df.copy()
    breach: list[bool | None] = []
    exceedance: list[float] = []
    for param, status, value in zip(out["parameter"], out["status"], out["value_num"], strict=True):
        if status == VALUE and param in limits:
            result = evaluate(param, value, limits)
            breach.append(result["breach"])
            exceedance.append(result["exceedance"])
        else:
            breach.append(None)
            exceedance.append(float("nan"))
    out["breach"] = pd.array(breach, dtype="boolean")
    out["exceedance"] = exceedance
    return out
