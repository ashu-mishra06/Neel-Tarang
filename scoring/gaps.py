"""Gap register: everything the data does not cover, in one structured list.

Run `python -m scoring.gaps` to print it and write data/derived/gap_register.json.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from scoring.config import load_rules, repo_path
from scoring.engine import Scores, load_designated, score_all
from scoring.limits import evaluate_frame, load_limits
from scoring.loader import BELOW_DETECTION, MISSING, VALUE, load_readings
from scoring.reasons import cite

METALS = ["Chromium", "Lead", "Zinc", "Copper"]


@dataclass
class Gap:
    id: str
    category: str  # "missing data" | "coverage" | "site" | "caveat"
    title: str
    detail: str
    ghats: list[str] = field(default_factory=list)
    items: list[str] = field(default_factory=list)


def missing_tables(df: pd.DataFrame) -> Gap | None:
    """Festival-year tables that exist for some ghats but not for others."""
    tables = sorted(set(zip(df["festival"], df["year"], strict=True)), key=lambda t: (t[1], t[0]))
    items, ghats = [], []
    for ghat, g in df.groupby("ghat", sort=True):
        present = set(zip(g["festival"], g["year"], strict=True))
        absent = [f"{f} {y}" for f, y in tables if (f, y) not in present]
        if absent:
            ghats.append(ghat)
            items += [f"{ghat}: no {t} table" for t in absent]
    if not items:
        return None
    return Gap("missing_tables", "missing data", "Missing festival-year tables",
               "The report has no table for these ghat-festival-years. Nothing is assumed "
               "for them; confidence is lowered.", ghats, items)


def not_sampled_cells(df: pd.DataFrame, scored: set[str]) -> Gap | None:
    """'not sampled', '*', '**' and blank cells, counted per ghat."""
    miss = df[df["status"] == MISSING]
    if miss.empty:
        return None
    items = []
    for ghat, g in miss.groupby("ghat", sort=True):
        total = len(df[df["ghat"] == ghat])
        core = g[g["parameter"].isin(scored)]
        cells = "; ".join(f"{r.parameter} {r.festival} {r.year} {r.phase} ({r.flag or 'blank'})"
                          for r in core.sort_values(["year", "festival", "phase"]).itertuples())
        items.append(f"{ghat}: {len(g)} of {total} cells not sampled"
                     + (f"; scored parameters: {cells}" if cells else ""))
    return Gap("not_sampled", "missing data", "Cells marked not sampled",
               "Shown as 'not sampled' everywhere, never as clean and never as 0.",
               sorted(miss["ghat"].unique()), items)


def during_only_tables(df: pd.DataFrame) -> Gap | None:
    """Tables with numbers in one column only; the organisers' parser assigned the phase."""
    counts = df[df["status"] == VALUE].groupby(["ghat", "festival", "year"])["phase"].unique()
    hits = [(k, list(v)) for k, v in counts.items() if len(v) == 1]
    if not hits:
        return None
    items = [f"{g}: {f} {y} has values only under '{phases[0]}'" for (g, f, y), phases in hits]
    return Gap("single_column_tables", "caveat", "Tables with one column of numbers",
               "These tables print numbers in one phase column only; the other columns are "
               "blank (the pH row shows * and **: not sampled at that stage). Checked "
               "against the page image. Their breaches cannot be compared with a pre "
               "reading and are listed as unpaired breaches.",
               sorted({g for (g, _, _), _ in hits}), items)


def unpaired(scores: Scores) -> Gap | None:
    items, ghats = [], []
    for s in scores.ranked:
        for u in s.unpaired_breaches:
            unit = f" {u['unit']}" if u["unit"] else ""
            items.append(f"{s.ghat}: {u['parameter']} {u['value']:g}{unit}, {u['festival']} "
                         f"{u['year']} {u['phase']}, {cite(u['year'], u['source_page'])} "
                         f"({u['why']})")
            ghats.append(s.ghat)
    if not items:
        return None
    return Gap("unpaired_breaches", "missing data", "Breaches that cannot be compared",
               "These readings breach the limit but have no matching earlier reading in the "
               "same table. They do not change the score; they lower confidence by one level.",
               sorted(set(ghats)), items)


def blind_spots(scores: Scores, designated: pd.DataFrame, df: pd.DataFrame) -> list[Gap]:
    gaps = []
    in_data = set(df["ghat"])
    no_data = [b for b in scores.blind_spots if b.ghat in in_data]
    if no_data:
        gaps.append(Gap("ghats_no_valid_data", "coverage", "Ghats with no valid readings",
                        "In the data but with nothing that can be scored; not ranked.",
                        [b.ghat for b in no_data], [f"{b.ghat}: {b.why}" for b in no_data]))
    missing = [b for b in scores.blind_spots if b.ghat not in in_data]
    if missing:
        gaps.append(Gap("designated_not_in_data", "coverage",
                        "Designated 2026 ghats with no past readings",
                        "Reported as a 2026 immersion ghat but absent from the MPPCB 2023-2025 "
                        "reports. Not ranked, never given a risk score; any test there is new "
                        "information.", [b.ghat for b in missing],
                        [f"{b.ghat}: {b.why}" for b in missing]))
    listed = set(designated["data_site"]) - {""}
    off_list = sorted(g for g in in_data if g not in listed)
    if off_list and len(listed):
        gaps.append(Gap("not_on_2026_list", "coverage", "Ghats not on the reported 2026 list",
                        "Have past readings but were not on the reported Ganesh 2026 list. "
                        "Kept in the ranking; confirm with BMC whether they are used for Durga.",
                        off_list, [f"{g}: confirm with BMC" for g in off_list]))
    return gaps


def site_ambiguity(scores: Scores) -> Gap | None:
    hits = [s for s in scores.ranked if s.site_match_uncertain]
    if not hits:
        return None
    return Gap("site_match_uncertain", "site", "Site name may cover two places",
               "Ganesh tables say 'Kamla Park kund'; Durga tables say 'Lower Lake ghat'. Kept "
               "as one ghat, not split; confidence capped at Medium.",
               [s.ghat for s in hits], [f"{s.ghat}: {s.site_match_note}" for s in hits])


def metals(df: pd.DataFrame) -> Gap:
    m = df[df["parameter"].isin(METALS)]
    items = []
    for name in METALS:
        p = m[m["parameter"] == name]
        items.append(f"{name}: {int((p['status'] == VALUE).sum())} quantified, "
                     f"{int((p['status'] == BELOW_DETECTION).sum())} BDL, "
                     f"{int((p['status'] == MISSING).sum())} not sampled")
    return Gap("only_four_metals", "caveat", "Only four metals tested; none has a class B limit",
               "Chromium, lead, zinc and copper are shown as context only and are not scored. "
               "BDL means very low, not zero.", [], items)


def fixed_caveats(rules: dict[str, Any]) -> list[Gap]:
    return [
        Gap("units_assumed", "caveat", "Units are assumed",
            "The reports print no units. The organisers assumed the standard unit for each "
            "test (mg/l for DO and BOD; none for pH).", [], []),
        Gap("standard_choice", "caveat", f"Standard used: {rules['standard']}",
            "Class B (outdoor bathing) is the yardstick chosen for this tool. Readings are "
            "compared with its limits only; no health conclusions are drawn.", [], []),
        Gap("lake_vs_kund", "caveat", "Past readings are from lake-side ghats",
            "2026 immersion is meant to use tanks/kunds; NGT directions bar immersion in Upper "
            "and Lower Lake. 2023-2025 readings may not describe the new set-ups.", [], []),
        Gap("designated_list_source", "caveat", "2026 list is from a press report",
            "The designated list is the Ganesh 2026 list reported by Free Press Journal "
            "(22 Sep 2026; URL in data/context/designated_ghats_2026.csv). The Durga 2026 list may differ - "
            "verify with BMC.", [], []),
    ]


def build_gap_register(scores: Scores | None = None, df: pd.DataFrame | None = None,
                       rules: dict[str, Any] | None = None,
                       designated: pd.DataFrame | None = None) -> list[Gap]:
    """Structured list of every known gap and caveat, most data-specific first."""
    rules = rules or load_rules()
    limits = load_limits(rules=rules)
    df = load_readings(rules=rules) if df is None else df
    designated = load_designated(rules) if designated is None else designated
    scores = scores or score_all(df, rules, limits, designated)
    scored_df = evaluate_frame(df, limits)
    core = scored_df[scored_df["parameter"].isin(limits)]
    gaps: list[Gap | None] = [missing_tables(core), not_sampled_cells(df, set(limits)),
                              during_only_tables(core), unpaired(scores)]
    gaps += blind_spots(scores, designated, df)
    gaps += [site_ambiguity(scores), metals(df)]
    issues = df.attrs.get("issues", [])
    if issues:
        gaps.append(Gap("bdl_on_scored", "missing data", "BDL on a scored parameter",
                        "Unexpected: below-detection on pH, DO or BOD.",
                        sorted({i["ghat"] for i in issues}),
                        [f"{i['ghat']}: {i['parameter']} {i['festival']} {i['year']} "
                         f"{i['phase']}" for i in issues]))
    gaps += fixed_caveats(rules)
    return [g for g in gaps if g is not None]


def write_gap_register(gaps: list[Gap], path: Path | None = None) -> Path:
    path = path or repo_path(load_rules()["gap_register_json"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(g) for g in gaps], indent=2, ensure_ascii=False),
                    encoding="utf-8")
    return path


def main() -> None:
    gaps = build_gap_register()
    for g in gaps:
        print(f"[{g.category}] {g.title}")
        print(f"    {g.detail}")
        for item in g.items:
            print(f"    - {item}")
    print(f"\nWrote {write_gap_register(gaps)}")


if __name__ == "__main__":
    main()
