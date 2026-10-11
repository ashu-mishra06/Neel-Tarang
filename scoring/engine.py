"""Scoring engine (Appendix A).

Splits each ghat's risk into a BASELINE part (water already breaches class B
before immersion) and a FESTIVAL part (water gets worse during/after
immersion), adds a confidence rating, and ranks the ghats.

Run `python -m scoring.engine` to print the ranking and write
data/derived/ghat_scores.json. No Streamlit, no network, no LLM.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from scoring.config import load_rules, repo_path
from scoring.limits import Limit, evaluate_frame, limit_text, load_limits, worsen
from scoring.loader import VALUE, load_readings
from scoring.pairs import anchor_by_parameter, matched_pairs, unpaired_breaches, worsens
from scoring.persistence import persistence
from scoring.reasons import cite, reason_parts, reason_text, short_reason

PHASES = ("pre", "during", "after")
TIER_ORDER = {"High": 0, "Medium": 1, "Low": 2}
CONFIDENCE_ORDER = {"Low": 0, "Medium": 1, "High": 2}
CONFIDENCE_LEVELS = ["Low", "Medium", "High"]
DRIVER_UNKNOWN = "Not enough data to tell"
DRIVER_LOW = "Lower concern on available data"
DRIVER_ELEVATED = "Elevated on several measures; no single large change"


@dataclass
class ParameterDetail:
    """Per-parameter numbers behind a ghat's score."""

    parameter: str
    limit: str
    pre_valid: int
    pre_breaches: int
    baseline: float | None
    festival: float | None
    festival_triples: int
    matched_pairs: int
    paired_pre_mean: float | None  # mean over matched tables only
    paired_during_mean: float | None
    mean_worsening: float | None  # in the parameter's units, worse direction
    crossing: bool
    meets_anchor: bool


@dataclass
class Confidence:
    level: str
    coverage: float
    valid: int
    expected: int
    capped: bool  # any cap applied (see cap_reasons)
    downgraded_for_unpaired: bool = False
    cap_reasons: list[str] = field(default_factory=list)
    missing_items: list[str] = field(default_factory=list)


@dataclass
class CriticalFlag:
    count: int
    note: str
    readings: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class GhatScore:
    ghat: str
    water_body: str
    rank: int
    risk_score: float
    baseline: float | None
    festival: float | None
    breach_rate_pre: float | None
    mean_exceedance_pre: float | None
    pre_valid: int
    festival_triples: int
    tier: str
    tier_from_score: str
    driver: str
    driver_detail: dict[str, Any]
    site_match_uncertain: bool
    site_match_note: str
    worsens: bool | None
    worsens_because: list[str]
    near_boundary: bool
    nearest_line: dict[str, Any]
    confidence: Confidence
    critical: CriticalFlag | None
    reason: str
    reason_short: str
    on_2026_list: bool
    list_status: str  # designated | in_use | none
    labels: list[str] = field(default_factory=list)
    parameters: list[ParameterDetail] = field(default_factory=list)
    matched_pairs: list[dict[str, Any]] = field(default_factory=list)
    unpaired_breaches: list[dict[str, Any]] = field(default_factory=list)
    persistence: list[dict[str, Any]] = field(default_factory=list)  # 7A, display only


@dataclass
class BlindSpot:
    ghat: str
    why: str


@dataclass
class Scores:
    ranked: list[GhatScore]
    blind_spots: list[BlindSpot]
    settings: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _rounded(asdict(self))


# ---------- components ----------


def baseline_components(g: pd.DataFrame, rules: dict[str, Any]) -> dict[str, Any]:
    """Baseline = w1 * breach rate + w2 * mean exceedance over valid PRE readings."""
    pre = g[(g["phase"] == "pre") & (g["status"] == VALUE)]
    if pre.empty:
        return {"breach_rate": None, "mean_exceedance": None, "score": None, "n": 0}
    rate = float(pre["breach"].astype(float).mean())
    exc = float(pre["exceedance"].mean())
    w = rules["scoring"]["baseline_weights"]
    score = w["breach_rate"] * rate + w["mean_exceedance"] * exc
    return {"breach_rate": rate, "mean_exceedance": exc, "score": score, "n": len(pre)}


def festival_triples(
    g: pd.DataFrame, limits: dict[str, Limit], rules: dict[str, Any]
) -> list[dict[str, Any]]:
    """One record per (festival, year, parameter) with valid pre and during readings."""
    valid = g[g["status"] == VALUE]
    if valid.empty:
        return []
    wide = valid.pivot_table(
        index=["festival", "year", "parameter"], columns="phase",
        values="value_num", aggfunc="first",
    )
    w = rules["scoring"]["festival_weights"]
    out = []
    for (festival, year, parameter), row in wide.iterrows():
        pre, during, after = (row.get(p) for p in PHASES)
        if parameter not in limits or pd.isna(pre) or pd.isna(during):
            continue
        w_during = worsen(limits[parameter], pre, during)
        w_after = None if pd.isna(after) else worsen(limits[parameter], pre, after)
        score = w_during if w_after is None else w["during"] * w_during + w["after"] * w_after
        out.append({
            "festival": festival, "year": year, "parameter": parameter,
            "worsen_during": w_during, "worsen_after": w_after, "score": score,
        })
    return out


def mean_or_none(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def festival_by_parameter(triples: list[dict[str, Any]]) -> dict[str, float]:
    """Mean triple score per parameter (only parameters with at least one triple)."""
    names = dict.fromkeys(t["parameter"] for t in triples)
    return {n: mean_or_none([t["score"] for t in triples if t["parameter"] == n]) for n in names}


def festival_score(triples: list[dict[str, Any]], rules: dict[str, Any]) -> float | None:
    """Festival effect from per-parameter mean triple scores.

    Default "max": the WORST parameter decides. Class B compliance fails if
    any one parameter fails, so one parameter getting worse is not diluted by
    the others staying steady. "mean" (the original rule) is kept as an option.
    """
    per_parameter = festival_by_parameter(triples)
    if not per_parameter:
        return None
    how = rules["scoring"]["festival_aggregation"]
    if how == "max":
        return max(per_parameter.values())
    if how == "mean_of_triples":
        return mean_or_none([t["score"] for t in triples])
    raise ValueError(f"Unknown festival_aggregation {how!r}")


def risk_score(baseline: float | None, festival: float | None, rules: dict[str, Any]) -> float:
    """100 * weighted mean of the available parts (a missing part is never 0)."""
    w = rules["scoring"]["risk_weights"]
    parts = {k: v for k, v in (("baseline", baseline), ("festival", festival)) if v is not None}
    if not parts:
        raise ValueError("No baseline or festival component; ghat is a blind spot.")
    return 100 * sum(w[k] * v for k, v in parts.items()) / sum(w[k] for k in parts)


def tier_for(score: float, rules: dict[str, Any]) -> str:
    t = rules["scoring"]["tiers"]
    return "High" if score >= t["high"] else "Medium" if score >= t["medium"] else "Low"


def near_boundary(risk: float, rules: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Is the risk within near_boundary_points of a tier line? Also returns the nearest line."""
    lines = rules["scoring"]["tiers"]
    name, value = min(lines.items(), key=lambda kv: abs(risk - kv[1]))
    distance = risk - value
    near = abs(distance) <= rules["scoring"]["near_boundary_points"]
    return near, {"line": name.capitalize(), "value": value, "distance": distance}


def driver_for(baseline: float | None, worse: bool | None, tier: str,
               rules: dict[str, Any]) -> str:
    """Plain-words label for WHY a ghat is risky.

    `worse` is the physical matched-pair anchor (scoring.pairs), not the score.
    When neither driver triggers, "lower concern" is only said of a Low-tier
    ghat; a Medium/High ghat is "elevated on several measures".
    """
    if baseline is None or worse is None:
        return DRIVER_UNKNOWN
    poor = baseline >= rules["scoring"]["driver"]["baseline"]
    if poor and worse:
        return "Poor before and worse during"
    if poor:
        return "Already poor before immersion"
    if worse:
        return "Worsens with immersion"
    return DRIVER_LOW if tier == "Low" else DRIVER_ELEVATED


def driver_detail(label: str, baseline: float | None, festival: float | None,
                  worse: bool | None, because: list[str], tier: str,
                  rules: dict[str, Any]) -> dict[str, Any]:
    """The numbers behind the driver label, shown next to it in the output."""
    return {
        "label": label, "tier": tier,
        "baseline": baseline, "baseline_cutoff": rules["scoring"]["driver"]["baseline"],
        "poor_before": baseline is not None
        and baseline >= rules["scoring"]["driver"]["baseline"],
        "festival_score": festival, "worsens_anchor_met": worse, "worsens_because": because,
    }


def site_match(g: pd.DataFrame) -> tuple[bool, str]:
    """Is the ghat's name match to the report tables uncertain ("medium")?"""
    if "site_match_confidence" not in g or not (g["site_match_confidence"] == "medium").any():
        return False, ""
    return True, ("Report tables name this site differently between festivals "
                  "(site match confidence: medium); readings may come from two places.")


def critical_flag(g: pd.DataFrame, rules: dict[str, Any]) -> CriticalFlag | None:
    """Team's own flag: reported DO of exactly 0 mg/l (not a CPCB limit)."""
    c = rules["scoring"]["critical"]
    hits = g[(g["parameter"] == c["parameter"]) & (g["status"] == VALUE)
             & (g["value_num"] == c["value"])]
    if hits.empty:
        return None
    readings = [
        {"year": r.year, "festival": r.festival, "phase": r.phase, "source_page": r.source_page}
        for r in hits.sort_values(["year", "festival", "phase"]).itertuples()
    ]
    note = (f"Reported {c['value']:g} mg/l dissolved oxygen {len(readings)} time(s). "
            "This is the team's own flag, not a CPCB limit.")
    return CriticalFlag(len(readings), note, readings)


def _missing_cells(g: pd.DataFrame) -> list[str]:
    rows = g[g["status"] != VALUE].sort_values(["year", "festival", "phase", "parameter"])
    return [
        f"{r.parameter}, {r.festival} {r.year} {r.phase}: "
        f"{'below detection' if r.status != 'missing' else (r.flag or 'blank')}"
        for r in rows.itertuples()
    ]


def _unpaired_items(unpaired: list[dict[str, Any]]) -> list[str]:
    out = []
    for u in unpaired:
        unit = f" {u['unit']}" if u["unit"] else ""
        out.append(f"unpaired breach: {u['parameter']} {u['value']:g}{unit}, {u['festival']} "
                   f"{u['year']} {u['phase']} ({cite(u['year'], u['source_page'])}; {u['why']})")
    return out


def confidence_for(
    g: pd.DataFrame, expected_tables: list[tuple[str, str]], latest_durga: tuple[str, str] | None,
    n_parameters: int, rules: dict[str, Any], unpaired: list[dict[str, Any]] | None = None,
    site_uncertain: bool = False,
) -> Confidence:
    """Coverage of valid scored readings, with every missing item listed.

    Order: level from coverage -> caps (latest Durga missing; uncertain site
    match) -> one level off per `unpaired_breach_downgrade` if any unpaired breach.
    """
    in_expected = [(f, y) in set(expected_tables)
                   for f, y in zip(g["festival"], g["year"], strict=True)]
    valid = int(((g["status"] == VALUE) & pd.Series(in_expected, index=g.index)).sum())
    expected = len(expected_tables) * len(PHASES) * n_parameters
    coverage = valid / expected if expected else 0.0
    present = set(zip(g["festival"], g["year"], strict=True))
    missing = [f"no {f} {y} table" for f, y in expected_tables if (f, y) not in present]
    missing += _missing_cells(g)
    c = rules["scoring"]["confidence"]
    level = "High" if coverage >= c["high"] else "Medium" if coverage >= c["medium"] else "Low"
    caps = []
    latest_absent = latest_durga is not None and latest_durga not in present
    if latest_absent:
        caps.append((rules["scoring"]["latest_durga_missing_cap"],
                     f"no {latest_durga[0]} {latest_durga[1]} table"))
    if site_uncertain:
        caps.append((rules["scoring"]["site_match_medium_cap"], "site match uncertain"))
    reasons = []
    for cap, why in caps:
        if CONFIDENCE_ORDER[level] > CONFIDENCE_ORDER[cap]:
            level = cap
            reasons.append(f"capped at {cap}: {why}")
    downgraded = False
    if unpaired:
        steps = rules["scoring"]["unpaired_breach_downgrade"]
        new_level = CONFIDENCE_LEVELS[max(CONFIDENCE_ORDER[level] - steps, 0)]
        downgraded, level = new_level != level, new_level
        missing += _unpaired_items(unpaired)
    return Confidence(level, coverage, valid, expected, bool(reasons), downgraded,
                      reasons, missing)


def parameter_details(
    g: pd.DataFrame, triples: list[dict[str, Any]], anchor: dict[str, dict[str, Any]],
    limits: dict[str, Limit], rules: dict[str, Any],
) -> list[ParameterDetail]:
    out = []
    per_parameter = festival_by_parameter(triples)
    for name, limit in limits.items():
        pre = g[(g["parameter"] == name) & (g["status"] == VALUE) & (g["phase"] == "pre")]
        a = anchor.get(name, {})
        out.append(ParameterDetail(
            parameter=name, limit=limit_text(limit),
            pre_valid=len(pre), pre_breaches=int(pre["breach"].astype(bool).sum()),
            baseline=baseline_components(g[g["parameter"] == name], rules)["score"],
            festival=per_parameter.get(name),
            festival_triples=sum(t["parameter"] == name for t in triples),
            matched_pairs=a.get("pairs", 0), paired_pre_mean=a.get("paired_pre_mean"),
            paired_during_mean=a.get("paired_during_mean"),
            mean_worsening=a.get("mean_worsening"), crossing=a.get("crossing", False),
            meets_anchor=a.get("meets_anchor", False),
        ))
    return out


def _top_baseline(details: list[ParameterDetail]) -> str | None:
    """Parameter with the largest baseline component (None if no pre breaches)."""
    best = max(details, key=lambda d: d.baseline or 0)
    return best.parameter if (best.baseline or 0) > 0 else None


# ---------- whole-dataset scoring ----------


def load_designated(rules: dict[str, Any]) -> pd.DataFrame:
    path = repo_path(rules["designated_ghats_csv"])
    if not path.exists():
        return pd.DataFrame(columns=["ghat_name", "data_site", "list_type"])
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _list_type(row: Any) -> str:
    """'designated' (22 Sep list) or 'in_use' (reported in use, 24 Sep)."""
    return getattr(row, "list_type", "") or "designated"


IN_USE_LABEL = ("Used for Ganesh 2026 per FPJ 24 Sep (not on the 22 Sep designated list); "
                "Durga list - confirm with BMC")
NO_LIST_LABEL = "Not on any reported 2026 list - confirm with BMC"


def _labels(g: pd.DataFrame, list_status: str) -> list[str]:
    labels = {"none": [NO_LIST_LABEL], "in_use": [IN_USE_LABEL]}.get(list_status, [])
    if site_match(g)[0]:
        labels.append("Site name match is medium confidence - may cover two places")
    return labels


def score_ghat(g: pd.DataFrame, ctx: dict[str, Any]) -> GhatScore | BlindSpot:
    """Score one ghat, or return a BlindSpot if it has nothing to score."""
    rules, limits, name = ctx["rules"], ctx["limits"], g["ghat"].iloc[0]
    base = baseline_components(g, rules)
    triples = festival_triples(g, limits, rules)
    festival = festival_score(triples, rules)
    if base["score"] is None and festival is None:
        return BlindSpot(name, "No valid pre-immersion or comparable readings")
    risk = risk_score(base["score"], festival, rules)
    critical = critical_flag(g, rules)
    tier_score = tier_for(risk, rules)
    tier = tier_score
    floor = rules["scoring"]["critical"]["tier_floor"]
    if critical and TIER_ORDER[floor] < TIER_ORDER[tier]:
        tier = floor
    pairs = matched_pairs(g, limits)
    anchor = anchor_by_parameter(pairs, limits, rules)
    worse, because = worsens(anchor)
    unpaired = unpaired_breaches(g, limits)
    details = parameter_details(g, triples, anchor, limits, rules)
    near, nearest = near_boundary(risk, rules)
    status = ("designated" if name in ctx["designated_sites"] else
              "in_use" if name in ctx["in_use_sites"] else "none")
    on_list = status != "none"
    parts = reason_parts(g, _top_baseline(details), pairs, unpaired,
                         critical.readings if critical else [], limits)
    poor = base["score"] is not None and base["score"] >= rules["scoring"]["driver"]["baseline"]
    label = driver_for(base["score"], worse, tier, rules)
    uncertain, note = site_match(g)
    return GhatScore(
        ghat=name, water_body=str(g["water_body"].iloc[0]) if "water_body" in g else "",
        rank=0, risk_score=risk, baseline=base["score"], festival=festival,
        breach_rate_pre=base["breach_rate"], mean_exceedance_pre=base["mean_exceedance"],
        pre_valid=base["n"], festival_triples=len(triples), tier=tier,
        tier_from_score=tier_score, driver=label,
        driver_detail=driver_detail(label, base["score"], festival, worse, because, tier, rules),
        site_match_uncertain=uncertain, site_match_note=note, worsens=worse,
        worsens_because=because, near_boundary=near, nearest_line=nearest,
        confidence=confidence_for(g, ctx["expected_tables"], ctx["latest_durga"],
                                  len(limits), rules, unpaired, uncertain),
        critical=critical, reason=reason_text(parts),
        reason_short=short_reason(parts, worse, poor), on_2026_list=on_list, list_status=status,
        labels=_labels(g, status), parameters=details, matched_pairs=pairs,
        unpaired_breaches=unpaired, persistence=persistence(g, limits, rules),
    )


def rank(scores: list[GhatScore]) -> list[GhatScore]:
    """Tier, then risk (high first), then lower coverage first, then name."""
    ordered = sorted(scores, key=lambda s: (TIER_ORDER[s.tier], -round(s.risk_score, 6),
                                            s.confidence.coverage, s.ghat))
    for i, s in enumerate(ordered, start=1):
        s.rank = i
    return ordered


def _context(df: pd.DataFrame, limits: dict[str, Limit], rules: dict[str, Any],
             designated: pd.DataFrame) -> dict[str, Any]:
    # Expected tables come from the reports only. Uploaded readings in a new
    # festival-year (e.g. Durga 2026) are scored but do not raise the bar for
    # every other ghat; uploads that fill an existing report table do count.
    report = df[df["source"] != "uploaded"] if "source" in df else df
    tables = sorted(set(zip(report["festival"], report["year"], strict=True)),
                    key=lambda t: (t[1], t[0]))
    durga_years = sorted(y for f, y in tables if f == "Durga")
    return {
        "rules": rules, "limits": limits, "expected_tables": tables,
        "latest_durga": ("Durga", durga_years[-1]) if durga_years else None,
        "designated_sites": {r.data_site or r.ghat_name for r in designated.itertuples()
                             if _list_type(r) == "designated"},
        "in_use_sites": {r.data_site or r.ghat_name for r in designated.itertuples()
                         if _list_type(r) == "in_use"},
    }


def score_all(df: pd.DataFrame | None = None, rules: dict[str, Any] | None = None,
              limits: dict[str, Limit] | None = None,
              designated: pd.DataFrame | None = None) -> Scores:
    """Score every ghat in the readings; return ranked ghats and blind spots."""
    rules = rules or load_rules()
    limits = limits or load_limits(rules=rules)
    df = load_readings(rules=rules) if df is None else df
    designated = load_designated(rules) if designated is None else designated
    scored = evaluate_frame(df, limits)
    scored = scored[scored["parameter"].isin(limits)]
    ctx = _context(scored, limits, rules, designated)
    results = [score_ghat(g, ctx) for _, g in scored.groupby("ghat", sort=True)]
    blind = [r for r in results if isinstance(r, BlindSpot)]
    in_data = set(scored["ghat"])
    for row in designated.itertuples():
        if (row.data_site or row.ghat_name) not in in_data:
            blind.append(BlindSpot(row.ghat_name, "Designated for 2026 but no readings in "
                                   "MPPCB 2023-2025 data"))
    ranked = rank([r for r in results if isinstance(r, GhatScore)])
    return Scores(ranked, blind, rules["scoring"])


# ---------- output ----------


def _rounded(obj: Any) -> Any:
    if isinstance(obj, float):
        return round(obj, 4)
    if isinstance(obj, dict):
        return {k: _rounded(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_rounded(v) for v in obj]
    if hasattr(obj, "item"):  # numpy scalar
        return _rounded(obj.item())
    return obj


def write_json(scores: Scores, path: Path | None = None) -> Path:
    path = path or repo_path(load_rules()["scores_json"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(scores.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def distribution_report(scores: Scores, rules: dict[str, Any]) -> list[str]:
    """Score distribution, plus a threshold proposal if all ghats share one tier."""
    risks = sorted(s.risk_score for s in scores.ranked)
    by_tier = {t: sum(s.tier_from_score == t for s in scores.ranked) for t in TIER_ORDER}
    lines = [f"Risk scores (sorted): {', '.join(f'{r:.1f}' for r in risks)}",
             f"Tiers from score alone: {by_tier} (thresholds {rules['scoring']['tiers']})"]
    if max(by_tier.values()) == len(risks) and len(risks) >= 3:
        lo, hi = risks[len(risks) // 3], risks[2 * len(risks) // 3]
        lines.append(f"All ghats in one tier. Proposal (tertiles): medium={lo:.0f}, high={hi:.0f}."
                     " Not applied; edit rules.yaml after review.")
    return lines


def main() -> None:
    rules = load_rules()
    scores = score_all(rules=rules)
    header = f"{'#':>2}  {'Ghat':<38} {'Risk':>5} {'Base':>5} {'Fest':>5}  {'Tier':<6} " \
             f"{'Driver':<31} {'Conf':<6} {'Cov':>4}"
    print(header)
    print("-" * len(header))
    for s in scores.ranked:
        flag = " *0 DO" if s.critical else ""
        flag += f" ~near {s.nearest_line['line']}" if s.near_boundary else ""
        flag += f" unpaired:{len(s.unpaired_breaches)}" if s.unpaired_breaches else ""
        print(f"{s.rank:>2}  {s.ghat:<38} {s.risk_score:>5.1f} {s.baseline or 0:>5.2f} "
              f"{s.festival or 0:>5.2f}  {s.tier:<6} {s.driver:<31} {s.confidence.level:<6} "
              f"{s.confidence.coverage:>4.0%}{flag}")
    print("\nBlind spots (not ranked):")
    for b in scores.blind_spots:
        print(f"  - {b.ghat}: {b.why}")
    print()
    for line in distribution_report(scores, rules):
        print(line)
    print(f"\nWrote {write_json(scores)}")


if __name__ == "__main__":
    main()
