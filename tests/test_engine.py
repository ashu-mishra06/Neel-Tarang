"""Engine components (Appendix A) on tiny hand-made frames, plus real-data checks."""

import pandas as pd
import pytest

from scoring.config import load_rules, repo_path
from scoring.engine import (
    DRIVER_ELEVATED,
    DRIVER_LOW,
    DRIVER_UNKNOWN,
    BlindSpot,
    Scores,
    baseline_components,
    confidence_for,
    critical_flag,
    driver_for,
    festival_score,
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
REAL = repo_path(RULES["data"]["readings_csv"]).exists()


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


def three_parameter_table(do_pre: float, do_during: float) -> list[tuple]:
    """One Durga 2023 table: DO moves as given, BOD and pH stay steady and within limits."""
    rows = []
    for phase, do in (("pre", do_pre), ("during", do_during), ("after", do_during)):
        rows += [("Durga", 2023, phase, "Dissolved oxygen", do),
                 ("Durga", 2023, phase, "BOD", 2.0),
                 ("Durga", 2023, phase, "pH", 7.5)]
    return rows


def test_festival_score_is_worst_parameter() -> None:
    g = frame(three_parameter_table(5.4, 4.0))
    triples = festival_triples(g, LIMITS, RULES)
    assert festival_score(triples, RULES) == pytest.approx(1.4 / 5)  # DO alone decides
    mean_rules = {**RULES, "scoring": {**RULES["scoring"],
                                       "festival_aggregation": "mean_of_triples"}}
    assert festival_score(triples, mean_rules) == pytest.approx(1.4 / 5 / 3)  # old rule dilutes


def test_festival_score_unknown_aggregation_raises() -> None:
    bad = {**RULES, "scoring": {**RULES["scoring"], "festival_aggregation": "median"}}
    with pytest.raises(ValueError):
        festival_score([{"parameter": "BOD", "score": 0.2}], bad)


def test_single_parameter_crossing_drives_worsens_label() -> None:
    """Malikhedi-shaped case: DO 5.4 -> 4.0 crosses the 5 mg/l limit; BOD and pH steady."""
    scores = score_all(frame(three_parameter_table(5.4, 4.0)), RULES, LIMITS, NO_DESIGNATED)
    (g,) = scores.ranked
    assert g.festival >= RULES["scoring"]["festival_tier_anchor"]  # 0.15 (review item)
    assert g.worsens is True  # DO drop 1.4 mg/l >= 1.0 and crosses 5 mg/l
    assert g.baseline < RULES["scoring"]["driver"]["baseline"]
    assert g.driver == "Worsens with immersion"
    do = next(p for p in g.parameters if p.parameter == "Dissolved oxygen")
    assert do.festival == pytest.approx(g.festival)  # per-parameter value kept for detail view


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
    "baseline, worse, tier, expected",
    [
        (0.5, False, "High", "Already poor before immersion"),
        (0.1, True, "High", "Worsens with immersion"),
        (0.5, True, "Medium", "Poor before and worse during"),
        (0.1, False, "Low", DRIVER_LOW),
        (0.1, False, "Medium", DRIVER_ELEVATED),
        (0.1, False, "High", DRIVER_ELEVATED),
        (None, True, "High", DRIVER_UNKNOWN),
        (0.5, None, "Low", DRIVER_UNKNOWN),  # no matched pairs: cannot tell
    ],
)
def test_driver(baseline, worse, tier: str, expected: str) -> None:
    assert driver_for(baseline, worse, tier, RULES) == expected


def _steady_ghat(bod_pre: float, bod_during: float, ghat: str = "G") -> pd.DataFrame:
    """Six tables, BOD small rise (< 1 mg/l anchor), DO and pH fine."""
    rows = []
    for y in (2023, 2024, 2025):
        for f in ("Ganesh", "Durga"):
            for phase, bod in (("pre", bod_pre), ("during", bod_during), ("after", bod_during)):
                rows += [(f, y, phase, "BOD", bod), (f, y, phase, "Dissolved oxygen", 7.0),
                         (f, y, phase, "pH", 7.5)]
    return frame(rows, ghat)


@pytest.mark.parametrize(
    "bod_pre, bod_during, tier, label",
    [
        (2.0, 2.5, "Low", DRIVER_LOW),          # nothing breaches: risk ~0
        (3.6, 4.5, "Medium", DRIVER_ELEVATED),  # BOD always over 3, rise 0.9 < 1 mg/l
    ],
)
def test_fallback_label_follows_tier(bod_pre, bod_during, tier: str, label: str) -> None:
    (g,) = score_all(_steady_ghat(bod_pre, bod_during), RULES, LIMITS, NO_DESIGNATED).ranked
    assert g.worsens is False and g.baseline < RULES["scoring"]["driver"]["baseline"]
    assert (g.tier, g.driver) == (tier, label)


def test_lower_concern_never_on_medium_or_high_real() -> None:
    if not REAL:
        pytest.skip("organisers' CSV not present")
    for s in score_all(rules=RULES).ranked:
        if s.tier != "Low":
            assert s.driver != DRIVER_LOW, s.ghat


def test_driver_detail_shows_numbers() -> None:
    (g,) = score_all(_steady_ghat(3.6, 4.5), RULES, LIMITS, NO_DESIGNATED).ranked
    d = g.driver_detail
    assert d["label"] == g.driver and d["tier"] == g.tier
    assert d["baseline"] == pytest.approx(g.baseline) and d["baseline_cutoff"] == 0.40
    assert d["festival_score"] == pytest.approx(g.festival)
    assert d["worsens_anchor_met"] is False and d["poor_before"] is False


def test_medium_site_match_caps_confidence_and_flags() -> None:
    df = _steady_ghat(2.0, 2.5)
    certain = score_all(df, RULES, LIMITS, NO_DESIGNATED).ranked[0]
    assert certain.confidence.level == "High" and not certain.site_match_uncertain
    df = df.assign(site_match_confidence="medium")
    (g,) = score_all(df, RULES, LIMITS, NO_DESIGNATED).ranked
    assert g.site_match_uncertain and "two places" in g.site_match_note
    assert g.confidence.level == "Medium"
    assert g.confidence.cap_reasons == ["capped at Medium: site match uncertain"]
    assert g.risk_score == pytest.approx(certain.risk_score)  # score unchanged


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


def test_critical_flag_floor_never_lowers_a_tier() -> None:
    rows = [("Durga", 2023, p, "BOD", 12.0) for p in ("pre", "during", "after")]
    rows += [("Durga", 2023, "pre", "Dissolved oxygen", 0.0)]
    (g,) = score_all(frame(rows), RULES, LIMITS, NO_DESIGNATED).ranked
    assert g.critical is not None and g.tier == "High"


def test_no_critical_flag_keeps_score_tier() -> None:
    rows = [(f, 2023, p, "Dissolved oxygen", 9.0) for f in ("Durga", "Ganesh")
            for p in ("pre", "during", "after")]
    (g,) = score_all(frame(rows), RULES, LIMITS, NO_DESIGNATED).ranked
    assert g.critical is None and g.tier == g.tier_from_score == "Low"


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


def test_real_rani_kamlapati_site_match_cap(real: Scores) -> None:
    by = {s.ghat: s for s in real.ranked}
    rk = by["Rani Kamlapati ghat / Kamla Park kund"]
    assert rk.site_match_uncertain and rk.confidence.level == "Medium"
    others = [s for s in real.ranked if s.ghat != rk.ghat]
    assert not any(s.site_match_uncertain for s in others)


def test_real_json_round_trip(real: Scores, tmp_path) -> None:
    import json

    from scoring.engine import write_json

    data = json.loads(write_json(real, tmp_path / "s.json").read_text(encoding="utf-8"))
    assert {"ranked", "blind_spots", "settings"} <= set(data)
    first = data["ranked"][0]
    for key in ("risk_score", "baseline", "festival", "tier", "driver", "confidence", "reason"):
        assert key in first
