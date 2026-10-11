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

PHASES = ("pre", "during", "after")
TIER_ORDER = {"High": 0, "Medium": 1, "Low": 2}
CONFIDENCE_ORDER = {"Low": 0, "Medium": 1, "High": 2}
DRIVER_UNKNOWN = "Not enough data to tell"


@dataclass
class ParameterDetail:
    """Per-parameter numbers behind a ghat's score."""

    parameter: str
    limit: str
    pre_mean: float | None
    during_mean: float | None
    pre_valid: int
    pre_breaches: int
    baseline: float | None
    festival: float | None
    festival_triples: int


@dataclass
class Confidence:
    level: str
    coverage: float
    valid: int
    expected: int
    capped: bool
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
    confidence: Confidence
    critical: CriticalFlag | None
    reason: str
    on_2026_list: bool
    labels: list[str] = field(default_factory=list)
    parameters: list[ParameterDetail] = field(default_factory=list)


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
        if pd.isna(pre) or pd.isna(during):
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


def driver_for(baseline: float | None, festival: float | None, rules: dict[str, Any]) -> str:
    """Plain-words label for WHY a ghat is risky."""
    if baseline is None or festival is None:
        return DRIVER_UNKNOWN
    d = rules["scoring"]["driver"]
    poor, worse = baseline >= d["baseline"], festival >= d["festival"]
    if poor and worse:
        return "Poor before and worse during"
    if poor:
        return "Already poor before immersion"
    if worse:
        return "Worsens with immersion"
    return "Lower concern on available data"


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


def confidence_for(
    g: pd.DataFrame, expected_tables: list[tuple[str, str]], latest_durga: tuple[str, str] | None,
    n_parameters: int, rules: dict[str, Any],
) -> Confidence:
    """Coverage of valid scored readings, with every missing item listed."""
    valid = int((g["status"] == VALUE).sum())
    expected = len(expected_tables) * len(PHASES) * n_parameters
    coverage = valid / expected if expected else 0.0
    present = set(zip(g["festival"], g["year"], strict=True))
    missing = [f"no {f} {y} table" for f, y in expected_tables if (f, y) not in present]
    missing += _missing_cells(g)
    c = rules["scoring"]["confidence"]
    level = "High" if coverage >= c["high"] else "Medium" if coverage >= c["medium"] else "Low"
    capped = False
    cap = rules["scoring"]["latest_durga_missing_cap"]
    latest_absent = latest_durga is not None and latest_durga not in present
    if latest_absent and CONFIDENCE_ORDER[level] > CONFIDENCE_ORDER[cap]:
        level, capped = cap, True
    return Confidence(level, coverage, valid, expected, capped, missing)


def parameter_details(
    g: pd.DataFrame, triples: list[dict[str, Any]], limits: dict[str, Limit],
    rules: dict[str, Any],
) -> list[ParameterDetail]:
    out = []
    for name, limit in limits.items():
        p = g[(g["parameter"] == name) & (g["status"] == VALUE)]
        pre, during = p[p["phase"] == "pre"], p[p["phase"] == "during"]
        base = baseline_components(g[g["parameter"] == name], rules)["score"]
        fest = [t["score"] for t in triples if t["parameter"] == name]
        out.append(ParameterDetail(
            parameter=name, limit=limit_text(limit),
            pre_mean=float(pre["value_num"].mean()) if len(pre) else None,
            during_mean=float(during["value_num"].mean()) if len(during) else None,
            pre_valid=len(pre), pre_breaches=int(pre["breach"].astype(bool).sum()),
            baseline=base, festival=mean_or_none(fest), festival_triples=len(fest),
        ))
    return out


# ---------- reason text (templates filled from numbers only) ----------


def _top(details: list[ParameterDetail], part: str) -> ParameterDetail | None:
    """Parameter with the largest baseline or festival component (None if all 0/absent)."""
    best = max(details, key=lambda d: getattr(d, part) or 0)
    return best if (getattr(best, part) or 0) > 0 else None


def _sentence(d: ParameterDetail, unit: str) -> str:
    if d.pre_mean is None:
        return f"{d.parameter}: no valid readings before immersion."
    text = f"{d.parameter} averaged {d.pre_mean:.1f}{unit} before immersion (limit: {d.limit})"
    if d.during_mean is None:
        return text + "; no valid readings during immersion."
    return text + f" and {d.during_mean:.1f} during."


def _worst_source(g: pd.DataFrame, parameter: str) -> str | None:
    p = g[(g["parameter"] == parameter) & (g["status"] == VALUE)]
    if p.empty:
        return None
    worst = p.sort_values(["exceedance", "year"], ascending=False).iloc[0]
    return f"Report {worst['year']} p.{worst['source_page']}"


def reason_text(g: pd.DataFrame, details: list[ParameterDetail], limits: dict[str, Limit],
                critical: CriticalFlag | None, rules: dict[str, Any]) -> str:
    """Plain-words reason: the biggest pre-immersion problem and, if different,
    the parameter that worsened most. No health wording; numbers from data only.
    """
    base, fest = _top(details, "baseline"), _top(details, "festival")
    picks = [d for d in (base, fest) if d is not None]
    picks = list(dict.fromkeys(p.parameter for p in picks)) or [details[0].parameter]
    by_name = {d.parameter: d for d in details}
    unit = {n: f" {limits[n].unit}" if limits[n].unit else "" for n in picks}
    text = " ".join(_sentence(by_name[n], unit[n]) for n in picks)
    if critical:
        text += f" Reported 0 mg/l dissolved oxygen {critical.count} time(s) (team's own flag)."
    source = _worst_source(g, picks[0])
    return f"{text} Source: {source}." if source else text


# ---------- whole-dataset scoring ----------


def load_designated(rules: dict[str, Any]) -> pd.DataFrame:
    path = repo_path(rules["designated_ghats_csv"])
    if not path.exists():
        return pd.DataFrame(columns=["ghat_name", "data_site"])
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _labels(g: pd.DataFrame, on_list: bool) -> list[str]:
    labels = [] if on_list else ["Not on reported 2026 list - confirm with BMC"]
    if "site_match_confidence" in g and (g["site_match_confidence"] == "medium").any():
        labels.append("Site name match is medium confidence - may cover two places")
    return labels


def score_ghat(g: pd.DataFrame, ctx: dict[str, Any]) -> GhatScore | BlindSpot:
    """Score one ghat, or return a BlindSpot if it has nothing to score."""
    rules, limits, name = ctx["rules"], ctx["limits"], g["ghat"].iloc[0]
    base = baseline_components(g, rules)
    triples = festival_triples(g, limits, rules)
    festival = mean_or_none([t["score"] for t in triples])
    if base["score"] is None and festival is None:
        return BlindSpot(name, "No valid pre-immersion or comparable readings")
    risk = risk_score(base["score"], festival, rules)
    critical = critical_flag(g, rules)
    tier_score = tier_for(risk, rules)
    tier = tier_score
    floor = rules["scoring"]["critical"]["tier_floor"]
    if critical and TIER_ORDER[floor] < TIER_ORDER[tier]:
        tier = floor
    details = parameter_details(g, triples, limits, rules)
    on_list = name in ctx["designated_sites"]
    return GhatScore(
        ghat=name, water_body=str(g["water_body"].iloc[0]) if "water_body" in g else "",
        rank=0, risk_score=risk, baseline=base["score"], festival=festival,
        breach_rate_pre=base["breach_rate"], mean_exceedance_pre=base["mean_exceedance"],
        pre_valid=base["n"], festival_triples=len(triples), tier=tier,
        tier_from_score=tier_score, driver=driver_for(base["score"], festival, rules),
        confidence=confidence_for(g, ctx["expected_tables"], ctx["latest_durga"],
                                  len(limits), rules),
        critical=critical, reason=reason_text(g, details, limits, critical, rules),
        on_2026_list=on_list, labels=_labels(g, on_list), parameters=details,
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
    tables = sorted(set(zip(df["festival"], df["year"], strict=True)),
                    key=lambda t: (t[1], t[0]))
    durga_years = sorted(y for f, y in tables if f == "Durga")
    return {
        "rules": rules, "limits": limits, "expected_tables": tables,
        "latest_durga": ("Durga", durga_years[-1]) if durga_years else None,
        "designated_sites": set(designated["data_site"]) - {""},
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
        if not row.data_site or row.data_site not in in_data:
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
