"""Re-score with uploaded readings (same columns as bhopal_ghats_2023_2025.csv).

validate_upload() checks a CSV and lists every problem in plain words.
rescore() merges valid rows (tagged source="uploaded"), re-runs the engine and
reports what changed per ghat. No scoring logic here: the engine does that.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from scoring.engine import Scores, load_designated, score_all
from scoring.limits import Limit
from scoring.loader import BELOW_DETECTION, MISSING, VALUE, SchemaError, prepare_readings

PHASES = {"pre", "during", "after"}
FESTIVALS = {"Ganesh", "Durga"}
MAX_ERRORS = 20
# Physically impossible values are rejected (not judged against limits).
PLAUSIBLE = {"pH": (0.0, 14.0)}
KEY = ["ghat", "festival", "year", "phase", "parameter"]


@dataclass
class UploadResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    rows: pd.DataFrame | None = None
    notes: list[str] = field(default_factory=list)


def _read_csv(data: bytes) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return pd.read_csv(io.BytesIO(data), dtype=str, keep_default_na=False,
                               encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("The file is not readable text. Save it as CSV (UTF-8) and try again.")


def _line(idx: int) -> str:
    return f"Row {idx + 2}"  # +1 for the header line, +1 for 1-based numbering


def _row_problems(df: pd.DataFrame, known_ghats: set[str], known_params: set[str],
                  rules: dict[str, Any]) -> list[str]:
    flags = {f.casefold() for f in rules["flags"]["missing"] + rules["flags"]["below_detection"]}
    problems = []
    for idx, r in df.iterrows():
        where = _line(idx)
        if r["ghat"] not in known_ghats:
            problems.append(f"{where}: ghat '{r['ghat']}' is not a known ghat name.")
        if r["parameter"] not in known_params:
            problems.append(f"{where}: parameter '{r['parameter']}' is not recognised.")
        if r["phase"] not in PHASES:
            problems.append(f"{where}: phase '{r['phase']}' must be pre, during or after.")
        if r["festival"] not in FESTIVALS:
            problems.append(f"{where}: festival '{r['festival']}' must be Ganesh or Durga.")
        if not (r["year"].isdigit() and len(r["year"]) == 4):
            problems.append(f"{where}: year '{r['year']}' must be a 4-digit year.")
        problems += _value_problems(r, where, flags)
    return problems


def _value_problems(r: pd.Series, where: str, flags: set[str]) -> list[str]:
    value, flag = r["value"], r["flag"].casefold()
    number = pd.to_numeric(value, errors="coerce")
    if value and pd.isna(number) and value.casefold() not in flags:
        return [f"{where}: value '{value}' is not a number or a recognised flag "
                "(not sampled, *, **, BDL, ND)."]
    if flag and flag not in flags:
        return [f"{where}: flag '{r['flag']}' is not recognised "
                "(not sampled, *, **, BDL, ND)."]
    if not value and not flag:
        return [f"{where}: no value and no flag. Write the number, or 'not sampled'."]
    if pd.notna(number) and flag:
        return [f"{where}: has both a number ({value}) and a flag ({r['flag']}). Keep one."]
    if pd.notna(number):
        low, high = PLAUSIBLE.get(r["parameter"], (0.0, float("inf")))
        if not low <= number <= high:
            return [f"{where}: {r['parameter']} value {value} is outside the possible "
                    f"range {low:g}-{high:g}."]
    return []


def _conflicts(up: pd.DataFrame, base: pd.DataFrame) -> list[str]:
    """Uploads may fill missing report cells but never overwrite a report value."""
    problems = []
    dupes = up[up.duplicated(KEY, keep=False)]
    for idx in dupes.index:
        problems.append(f"{_line(idx)}: the same ghat/festival/year/phase/parameter "
                        "appears more than once in the upload.")
    keyed = base.set_index(KEY)
    for idx, r in up.iterrows():
        key = tuple(r[k] for k in KEY)
        if key in keyed.index:
            existing = keyed.loc[[key]].iloc[0]
            if existing["status"] != MISSING:
                problems.append(
                    f"{_line(idx)}: the report already has {r['parameter']} for {r['ghat']}, "
                    f"{r['festival']} {r['year']} {r['phase']} ({existing['value'] or 'BDL'}, "
                    f"p.{existing['source_page']}). Uploads cannot overwrite report values.")
    return problems


def validate_upload(data: bytes, base: pd.DataFrame, rules: dict[str, Any],
                    limits: dict[str, Limit],
                    designated: pd.DataFrame | None = None) -> UploadResult:
    """Check an uploaded CSV. Never raises for a bad file: problems come back as text."""
    designated = load_designated(rules) if designated is None else designated
    try:
        raw = _read_csv(data)
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return UploadResult(False, ["The file is empty or not a CSV table."])
    except ValueError as err:
        return UploadResult(False, [str(err)])
    if raw.empty:
        return UploadResult(False, ["The file has a header but no rows."])
    try:
        df = prepare_readings(raw, rules)
    except SchemaError as err:
        return UploadResult(False, [str(err)])
    known = set(base["ghat"]) | {g for g in designated["ghat_name"] if g}
    problems = _row_problems(df, known, set(base["parameter"]), rules)
    if not problems:
        problems += _conflicts(df, base)
    if problems:
        extra = len(problems) - MAX_ERRORS
        shown = problems[:MAX_ERRORS] + ([f"... and {extra} more."] if extra > 0 else [])
        return UploadResult(False, shown)
    df["source"] = "uploaded"
    df["source_page"] = ""
    for col in ("water_body", "site_match_confidence", "value_as_printed", "unit_assumed"):
        if col not in df:
            df[col] = ""
    df["value_as_printed"] = df["value_as_printed"].where(df["value_as_printed"] != "",
                                                          df["value"])
    n_bdl = int((df["status"] == BELOW_DETECTION).sum())
    notes = [f"{len(df)} rows accepted ({int((df['status'] == VALUE).sum())} values, "
             f"{int((df['status'] == MISSING).sum())} not sampled, {n_bdl} below detection)."]
    return UploadResult(True, [], df, notes)


def merge(base: pd.DataFrame, uploaded: pd.DataFrame) -> pd.DataFrame:
    """Base rows (source=report) plus uploaded rows. Report 'not sampled' cells that an
    upload fills are dropped so the uploaded reading takes their place."""
    base = base.assign(source=base["source"] if "source" in base else "report")
    filled = set(map(tuple, uploaded[KEY].to_numpy()))
    keep = [tuple(r) not in filled for r in base[KEY].to_numpy()]
    merged = pd.concat([base[keep], uploaded], ignore_index=True)
    merged.attrs["issues"] = base.attrs.get("issues", []) + uploaded.attrs.get("issues", [])
    return merged


def what_changed(before: Scores, after: Scores) -> list[dict[str, Any]]:
    """Per ghat: rank, tier, risk, driver and confidence before -> after."""
    old = {s.ghat: s for s in before.ranked}
    rows = []
    for s in after.ranked:
        o = old.get(s.ghat)
        row = {
            "ghat": s.ghat,
            "rank": f"{o.rank} → {s.rank}" if o else f"new → {s.rank}",
            "tier": f"{o.tier} → {s.tier}" if o else f"no baseline → {s.tier}",
            "risk": f"{o.risk_score:.1f} → {s.risk_score:.1f}" if o else f"— → {s.risk_score:.1f}",
            "driver": s.driver if not o or o.driver == s.driver else f"{o.driver} → {s.driver}",
            "confidence": f"{o.confidence.level} → {s.confidence.level}" if o
            else s.confidence.level,
        }
        row["changed"] = (not o or o.rank != s.rank or o.tier != s.tier
                          or round(o.risk_score, 6) != round(s.risk_score, 6)
                          or o.driver != s.driver
                          or o.confidence.level != s.confidence.level)
        rows.append(row)
    return rows


def rescore(base: pd.DataFrame, uploaded: pd.DataFrame, rules: dict[str, Any],
            limits: dict[str, Limit], designated: pd.DataFrame | None = None
            ) -> tuple[pd.DataFrame, Scores, Scores, list[dict[str, Any]]]:
    """Merged data, scores before and after, and the per-ghat changes."""
    designated = load_designated(rules) if designated is None else designated
    before = score_all(base, rules, limits, designated)
    merged = merge(base, uploaded)
    after = score_all(merged, rules, limits, designated)
    return merged, before, after, what_changed(before, after)
