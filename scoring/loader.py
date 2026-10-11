"""Load ghat readings and label each one as value, missing or below_detection.

Rule: missing data is shown as missing, never as clean; BDL/ND is never zero.
"""

import warnings
from pathlib import Path
from typing import Any

import pandas as pd

from scoring.config import load_rules, repo_path

VALUE = "value"
MISSING = "missing"
BELOW_DETECTION = "below_detection"
REQUIRED = ["ghat", "parameter", "value", "year", "festival", "phase"]


class SchemaError(ValueError):
    """The CSV does not have the columns the engine needs."""


def resolve_columns(found: list[str], candidates: dict[str, list[str]]) -> dict[str, str]:
    """Map canonical column names to the actual names present in the CSV."""
    lookup = {c.strip().casefold(): c for c in found}
    mapping = {}
    for canonical, names in candidates.items():
        match = next((lookup[n.casefold()] for n in names if n.casefold() in lookup), None)
        if match is not None:
            mapping[canonical] = match
    return mapping


def _norm(text: Any) -> str:
    return "" if pd.isna(text) else str(text).strip().casefold()


def classify(raw_value: Any, flag: Any, rules: dict[str, Any]) -> str:
    """Return the status of one reading. Flags win over numbers."""
    missing = {f.casefold() for f in rules["flags"]["missing"]}
    bdl = {f.casefold() for f in rules["flags"]["below_detection"]}
    tokens = {_norm(flag), _norm(raw_value)}
    if tokens & bdl:
        return BELOW_DETECTION
    if tokens & missing:
        return MISSING
    return VALUE if pd.notna(pd.to_numeric(_norm(raw_value), errors="coerce")) else MISSING


def _rename(df: pd.DataFrame, rules: dict[str, Any]) -> pd.DataFrame:
    if "status" in df.columns:
        df = df.rename(columns={"status": "status_source"})
    mapping = resolve_columns(list(df.columns), rules["readings_columns"])
    absent = [c for c in REQUIRED if c not in mapping]
    if absent:
        raise SchemaError(
            f"Missing required column(s): {', '.join(absent)}. "
            f"Found: {', '.join(df.columns)}. Add the real names in rules.yaml readings_columns."
        )
    df = df.rename(columns={actual: canon for canon, actual in mapping.items()})
    if "flag" not in df.columns:
        df["flag"] = ""
    return df


def _scored_bdl_issues(df: pd.DataFrame, rules: dict[str, Any]) -> list[dict[str, Any]]:
    """BDL/ND on a scored parameter is unexpected: report it for the gap register."""
    scored = set(rules["scored_parameters"])
    hits = df[(df["status"] == BELOW_DETECTION) & df["parameter"].isin(scored)]
    issues = [
        {"type": "bdl_on_scored_parameter", "ghat": r.ghat, "parameter": r.parameter,
         "year": r.year, "festival": r.festival, "phase": r.phase}
        for r in hits.itertuples()
    ]
    if issues:
        warnings.warn(f"{len(issues)} BDL/ND reading(s) on scored parameters", stacklevel=3)
    return issues


def load_readings(
    path: Path | str | None = None, rules: dict[str, Any] | None = None
) -> pd.DataFrame:
    """Read the readings CSV and add `status` and numeric `value_num` columns.

    `value_num` is set only where status is "value"; it is NaN otherwise, so
    missing and below-detection readings can never be averaged as numbers.
    Load issues are attached as `df.attrs["issues"]`.
    """
    rules = rules or load_rules()
    path = path or repo_path(rules["data"]["readings_csv"])
    raw = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df = _rename(raw, rules)
    df["parameter"] = df["parameter"].str.strip()
    df["phase"] = df["phase"].str.strip().str.lower()
    df["status"] = [classify(v, f, rules) for v, f in zip(df["value"], df["flag"], strict=True)]
    numeric = pd.to_numeric(df["value"].str.strip(), errors="coerce")
    df["value_num"] = numeric.where(df["status"] == VALUE)
    df.attrs["issues"] = _scored_bdl_issues(df, rules)
    return df
