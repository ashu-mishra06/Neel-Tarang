"""Engine components (Appendix A) on tiny hand-made frames, plus real-data checks."""

import pandas as pd
import pytest

from scoring.config import load_rules, repo_path
from scoring.engine import (
    DRIVER_UNKNOWN,
    BlindSpot,
    Scores,
    baseline_components,
    confidence_for,
    critical_flag,
    driver_for,
    festival_triples,
    rank,
    risk_score,
    score_all,
    tier_for,
)
from scoring.limits import evaluate_frame, limit_text, limits_from_rules, worsen
from scoring.loader import MISSING, VALUE

RULES = load_rules()
LIMITS = limits_from_rules(RULES)
NO_DESIGNATED = pd.DataFrame(columns=["ghat_name", "data_site"])


def frame(rows: list[tuple], ghat: str = "G") -> pd.DataFrame:
    """rows: (festival, year, phase, parameter, value or None, flag)."""
    records = []
    for festival, year, phase, parameter, value, *flag in rows:
        records.append({
            "ghat": ghat, "water_body": "Lake", "festival": festival, "year": str(year),
            "phase": phase, "parameter": parameter, "flag": flag[0] if flag else "",
            "status": VALUE if value is not None else MISSING, "value_num": value,
            "source_page": "40", "site_match_confidence": "high",
        })
    return evaluate_frame(pd.DataFrame(records), LIMITS)


# ---------- worsen / limit text ----------


@pytest.mark.parametrize(
    "parameter, pre, later, expected",
    [
        ("Dissolved oxygen", 6.0, 4.0, 0.4),
        ("Dissolved oxygen", 4.0, 6.0, 0.0),  # improvement = 0
        ("Dissolved oxygen", 9.0, 0.0, 1.0),  # clipped
        ("BOD", 3.0, 4.5, 0.5),
        ("BOD", 6.0, 3.0, 0.0),
        ("pH", 8.0, 9.0, 0.5 / 1.5),  # 0 outside -> 0.5 outside
        ("pH", 7.0, 8.4, 0.0),  # still inside the range
    ],
)
def test_worsen(parameter: str, pre: float, later: float, expected: float) -> None:
    assert worsen(LIMITS[parameter], pre, later) == pytest.approx(expected)


def test_limit_text() -> None:
    assert limit_text(LIMITS["Dissolved oxygen"]) == "at least 5 mg/l"
    assert limit_text(LIMITS["BOD"]) == "at most 3 mg/l"
    assert limit_text(LIMITS["pH"]) == "6.5 to 8.5"


# ---------- baseline ----------


def test_baseline_formula() -> None:
    g = frame([("Durga", 2023, "pre", "Dissolved oxygen", 4.0),
               ("Ganesh", 2023, "pre", "Dissolved oxygen", 6.0),
               ("Ganesh", 2023, "during", "Dissolved oxygen", 1.0)])  # not pre: ignored
    b = baseline_components(g, RULES)
    assert b["breach_rate"] == 0.5
    assert b["mean_exceedance"] == pytest.approx(0.1)  # (0.2 + 0) / 2
    assert b["score"] == pytest.approx(0.3)
    assert b["n"] == 2


def test_baseline_ignores_missing_and_is_none_not_zero() -> None:
    g = frame([("Durga", 2023, "pre", "BOD", None, "not sampled")])
    assert baseline_components(g, RULES)["score"] is None


# ---------- festival ----------


def test_festival_triple_with_after() -> None:
    g = frame([("Durga", 2023, "pre", "Dissolved oxygen", 6.0),
               ("Durga", 2023, "during", "Dissolved oxygen", 4.0),
               ("Durga", 2023, "after", "Dissolved oxygen", 5.0)])
    (t,) = festival_triples(g, LIMITS, RULES)
    assert t["score"] == pytest.approx(0.7 * 0.4 + 0.3 * 0.2)


def test_festival_triple_after_missing_uses_during_only() -> None:
    g = frame([("Durga", 2023, "pre", "BOD", 3.0),
               ("Durga", 2023, "during", "BOD", 4.5),
               ("Durga", 2023, "after", "BOD", None, "*")])
    (t,) = festival_triples(g, LIMITS, RULES)
    assert t["score"] == pytest.approx(0.5) and t["worsen_after"] is None


def test_festival_triple_skipped_without_during_or_pre() -> None:
    g = frame([("Durga", 2023, "pre", "BOD", 3.0),
               ("Durga", 2023, "during", "BOD", None, "not sampled"),
               ("Durga", 2023, "after", "BOD", 9.0),
               ("Ganesh", 2023, "pre", "BOD", None, "not sampled"),
               ("Ganesh", 2023, "during", "BOD", 9.0)])
    assert festival_triples(g, LIMITS, RULES) == []


# ---------- risk / tier / driver / critical ----------


def test_risk_score_weights_and_missing_part() -> None:
    assert risk_score(0.4, 0.2, RULES) == pytest.approx(30.0)
    assert risk_score(0.4, None, RULES) == pytest.approx(40.0)  # renormalised, not 0
    with pytest.raises(ValueError):
        risk_score(None, None, RULES)


def test_tier_thresholds() -> None:
    t = RULES["scoring"]["tiers"]
    assert tier_for(t["high"], RULES) == "High"
    assert tier_for(t["high"] - 0.01, RULES) == "Medium"
    assert tier_for(t["medium"], RULES) == "Medium"
    assert tier_for(t["medium"] - 0.01, RULES) == "Low"


@pytest.mark.parametrize(
    "baseline, festival, expected",
    [
        (0.5, 0.05, "Already poor before immersion"),
        (0.1, 0.3, "Worsens with immersion"),
        (0.5, 0.3, "Poor before and worse during"),
        (0.1, 0.05, "Lower concern on available data"),
        (None, 0.3, DRIVER_UNKNOWN),
    ],
)
def test_driver(baseline, festival, expected: str) -> None:
    assert driver_for(baseline, festival, RULES) == expected


def test_critical_flag_counts_only_valid_zero_do() -> None:
    g = frame([("Durga", 2023, "pre", "Dissolved oxygen", 0.0),
               ("Durga", 2023, "during", "Dissolved oxygen", 0.0),
               ("Durga", 2023, "after", "Dissolved oxygen", None, "not sampled"),
               ("Ganesh", 2023, "pre", "BOD", 0.0)])
    flag = critical_flag(g, RULES)
    assert flag.count == 2 and "not a CPCB limit" in flag.note


def test_critical_flag_lifts_tier_to_high() -> None:
    rows = [(f, 2023, p, "Dissolved oxygen", 9.0) for f in ("Durga", "Ganesh")
            for p in ("pre", "during", "after")]
    rows[1] = ("Durga", 2023, "during", "Dissolved oxygen", 0.0)
    scores = score_all(frame(rows), RULES, LIMITS, NO_DESIGNATED)
    (g,) = scores.ranked
    assert g.tier_from_score == "Low" and g.tier == "High"


# ---------- confidence ----------

TABLES = [(f, str(y)) for y in (2023, 2024, 2025) for f in ("Ganesh", "Durga")]


def full_rows(skip: set[tuple[str, int]] = frozenset()) -> list[tuple]:
    return [(f, y, p, prm, 7.0) for y in (2023, 2024, 2025) for f in ("Ganesh", "Durga")
            if (f, y) not in skip for p in ("pre", "during", "after")
            for prm in ("pH", "Dissolved oxygen", "BOD")]


def test_confidence_full_coverage_is_high() -> None:
    c = confidence_for(frame(full_rows()), TABLES, ("Durga", "2025"), 3, RULES)
    assert (c.level, c.valid, c.expected, c.missing_items) == ("High", 54, 54, [])


def test_confidence_lists_missing_table_and_cells() -> None:
    rows = full_rows({("Durga", 2025)})
    rows[0] = ("Ganesh", 2023, "pre", "pH", None, "not sampled")
    c = confidence_for(frame(rows), TABLES, ("Durga", "2025"), 3, RULES)
    assert "no Durga 2025 table" in c.missing_items
    assert "pH, Ganesh 2023 pre: not sampled" in c.missing_items
    assert c.valid == 44 and c.level == "Medium"


def test_confidence_capped_when_latest_durga_missing() -> None:
    years = range(2015, 2026)
    tables = [(f, str(y)) for y in years for f in ("Ganesh", "Durga")]
    rows = [(f, y, p, prm, 7.0) for y in years for f in ("Ganesh", "Durga")
            if (f, y) != ("Durga", 2025) for p in ("pre", "during", "after")
            for prm in ("pH", "Dissolved oxygen", "BOD")]
    c = confidence_for(frame(rows), tables, ("Durga", "2025"), 3, RULES)
    assert c.coverage >= RULES["scoring"]["confidence"]["high"]
    assert c.level == "Medium" and c.capped


# ---------- ranking and blind spots ----------


def test_ghat_with_no_valid_readings_is_blind_spot() -> None:
    df = pd.concat([
        frame(full_rows(), ghat="A"),
        frame([("Durga", 2023, "pre", "BOD", None, "not sampled")], ghat="B"),
    ])
    designated = pd.DataFrame({"ghat_name": ["A", "Arch Bridge"], "data_site": ["A", ""]})
    scores = score_all(df, RULES, LIMITS, designated)
    assert [s.ghat for s in scores.ranked] == ["A"]
    assert {b.ghat for b in scores.blind_spots} == {"B", "Arch Bridge"}
    assert all(isinstance(b, BlindSpot) for b in scores.blind_spots)


def test_rank_ties_put_lower_confidence_first() -> None:
    complete = frame(full_rows(), ghat="Complete")
    gappy_rows = full_rows()
    gappy_rows[6] = ("Ganesh", 2023, "after", "pH", None, "not sampled")  # no effect on score
    gappy = frame(gappy_rows, ghat="Gappy")
    scores = score_all(pd.concat([complete, gappy]), RULES, LIMITS, NO_DESIGNATED)
    assert scores.ranked[0].risk_score == pytest.approx(scores.ranked[1].risk_score)
    assert [s.ghat for s in scores.ranked] == ["Gappy", "Complete"]
    assert [s.rank for s in scores.ranked] == [1, 2]


def test_rank_orders_by_tier_before_score() -> None:
    a = frame([("Durga", 2023, "pre", "BOD", 6.0), ("Durga", 2023, "during", "BOD", 6.0)], "A")
    b_rows = [("Durga", 2023, "pre", "Dissolved oxygen", 9.0),
              ("Durga", 2023, "during", "Dissolved oxygen", 0.0)]
    b = frame(b_rows, "B")
    scores = score_all(pd.concat([a, b]), RULES, LIMITS, NO_DESIGNATED)
    assert scores.ranked[0].tier == "High"
    assert rank(list(reversed(scores.ranked)))[0].ghat == scores.ranked[0].ghat


def test_reason_has_no_health_wording() -> None:
    scores = score_all(frame(full_rows()), RULES, LIMITS, NO_DESIGNATED)
    banned = ["disease", "illness", "unsafe to drink", "causes", "health risk"]
    assert not any(w in scores.ranked[0].reason.lower() for w in banned)


# ---------- real data (gate G2) ----------

REAL = repo_path(RULES["data"]["readings_csv"]).exists()


@pytest.fixture(scope="module")
def real() -> Scores:
    if not REAL:
        pytest.skip("organisers' CSV not present")
    return score_all(rules=RULES)


def test_real_ranks_seven_ghats(real: Scores) -> None:
    assert len(real.ranked) == 7
    assert [s.rank for s in real.ranked] == list(range(1, 8))


def test_real_arch_bridge_is_blind_spot(real: Scores) -> None:
    assert "Arch Bridge" in {b.ghat for b in real.blind_spots}


def test_real_missing_durga_2025_lowers_confidence(real: Scores) -> None:
    """T4 (engine part)."""
    by = {s.ghat: s for s in real.ranked}
    for name in ("Bairagarh (Sant Hirdaram) kund", "Malikhedi kund"):
        assert by[name].confidence.level != "High"
        assert "no Durga 2025 table" in by[name].confidence.missing_items


def test_real_bairagarh_zero_do_flag(real: Scores) -> None:
    by = {s.ghat: s for s in real.ranked}
    flag = by["Bairagarh (Sant Hirdaram) kund"].critical
    assert flag.count == 4 and by["Bairagarh (Sant Hirdaram) kund"].tier == "High"


def test_real_labels(real: Scores) -> None:
    by = {s.ghat: s for s in real.ranked}
    assert not by["Shahpura lake ghat"].on_2026_list
    assert any("medium confidence" in x for x in by["Rani Kamlapati ghat / Kamla Park kund"].labels)


def test_real_json_round_trip(real: Scores, tmp_path) -> None:
    import json

    from scoring.engine import write_json

    data = json.loads(write_json(real, tmp_path / "s.json").read_text(encoding="utf-8"))
    assert {"ranked", "blind_spots", "settings"} <= set(data)
    first = data["ranked"][0]
    for key in ("risk_score", "baseline", "festival", "tier", "driver", "confidence", "reason"):
        assert key in first
