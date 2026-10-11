"""Re-score with uploaded readings (gate G6, test T9)."""

import pytest

from scoring.config import load_rules, repo_path
from scoring.evidence import USER_SUPPLIED, evidence_for_frame
from scoring.limits import evaluate_frame, load_limits
from scoring.loader import load_readings
from scoring.reasons import cite
from scoring.rescore import merge, rescore, validate_upload

RULES = load_rules()
pytestmark = pytest.mark.skipif(not repo_path(RULES["data"]["readings_csv"]).exists(),
                                reason="organisers' CSV not present")
HEADER = "year,festival,site,phase,parameter,value,flag,source_page\n"


@pytest.fixture(scope="module")
def ctx():
    limits = load_limits(rules=RULES)
    return {"base": load_readings(rules=RULES), "limits": limits}


def check(ctx, text: str):
    return validate_upload(text.encode("utf-8"), ctx["base"], RULES, ctx["limits"])


def sample_bytes() -> bytes:
    return repo_path("data/samples/new_readings_sample.csv").read_bytes()


# ---------- G6: the sample changes scores and is tagged user-supplied ----------


def test_sample_upload_changes_at_least_one_score(ctx) -> None:
    res = validate_upload(sample_bytes(), ctx["base"], RULES, ctx["limits"])
    assert res.ok, res.errors
    merged, before, after, changes = rescore(ctx["base"], res.rows, RULES, ctx["limits"])
    old = {s.ghat: s.risk_score for s in before.ranked}
    new = {s.ghat: s.risk_score for s in after.ranked}
    assert any(abs(new[g] - old[g]) > 1e-9 for g in old)
    assert new["Malikhedi kund"] > old["Malikhedi kund"]
    assert any(c["changed"] for c in changes)


def test_uploaded_designated_ghat_leaves_blind_spots(ctx) -> None:
    res = validate_upload(sample_bytes(), ctx["base"], RULES, ctx["limits"])
    _, before, after, changes = rescore(ctx["base"], res.rows, RULES, ctx["limits"])
    assert "Arch Bridge" in {b.ghat for b in before.blind_spots}
    assert "Arch Bridge" not in {b.ghat for b in after.blind_spots}
    arch = next(s for s in after.ranked if s.ghat == "Arch Bridge")
    assert arch.confidence.level == "Low" and arch.on_2026_list
    assert next(c for c in changes if c["ghat"] == "Arch Bridge")["rank"].startswith("new")


def test_uploaded_rows_are_user_supplied_in_evidence(ctx) -> None:
    """T9."""
    res = validate_upload(sample_bytes(), ctx["base"], RULES, ctx["limits"])
    merged = merge(ctx["base"], res.rows)
    rows = evidence_for_frame(evaluate_frame(merged, ctx["limits"]), ctx["limits"], RULES)
    uploaded = [r for r in rows if r.year == "2026"]
    assert len(uploaded) == 14
    assert all(r.source == USER_SUPPLIED and r.report_url_with_page == "" for r in uploaded)
    assert all(r.source == "report" for r in rows if r.year != "2026")


def test_new_table_does_not_lower_other_ghats_confidence(ctx) -> None:
    res = validate_upload(sample_bytes(), ctx["base"], RULES, ctx["limits"])
    _, before, after, _ = rescore(ctx["base"], res.rows, RULES, ctx["limits"])
    old = {s.ghat: s.confidence for s in before.ranked}
    for s in after.ranked:
        if s.ghat in ("Shahpura lake ghat", "Hathaikheda dam / kund", "Prempura ghat"):
            assert s.confidence.level == old[s.ghat].level
            assert s.confidence.coverage == pytest.approx(old[s.ghat].coverage)


def test_reason_cites_user_supplied(ctx) -> None:
    res = validate_upload(sample_bytes(), ctx["base"], RULES, ctx["limits"])
    _, _, after, _ = rescore(ctx["base"], res.rows, RULES, ctx["limits"])
    arch = next(s for s in after.ranked if s.ghat == "Arch Bridge")
    assert "user-supplied reading" in arch.reason and "p." not in arch.reason
    assert cite("2025", "61", "") == "Report 2025 p.61 + user-supplied"
    assert cite("2026", "") == "user-supplied reading"


def test_upload_can_fill_a_not_sampled_report_cell(ctx) -> None:
    text = HEADER + "2023,Durga,Prempura ghat,pre,BOD,4.1,,\n"
    res = check(ctx, text)
    assert res.ok, res.errors
    _, before, after, _ = rescore(ctx["base"], res.rows, RULES, ctx["limits"])
    b = next(s for s in before.ranked if s.ghat == "Prempura ghat").confidence
    a = next(s for s in after.ranked if s.ghat == "Prempura ghat").confidence
    assert a.valid == b.valid + 1


# ---------- malformed uploads: friendly errors, never a stack trace ----------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("", "empty or not a CSV"),
        ("year,festival\n2026,Durga\n", "Missing required column"),
        (HEADER, "no rows"),
        (HEADER + "2026,Durga,Malikhedi kund,midway,BOD,4,,\n", "must be pre, during or after"),
        (HEADER + "2026,Durga,Malikhedi kund,pre,BOD,four,,\n", "not a number"),
        (HEADER + "2026,Durga,Malikhedi kund,pre,BOD,,,\n", "no value and no flag"),
        (HEADER + "2026,Durga,Malikhedi kund,pre,BOD,4,not sampled,\n", "both a number"),
        (HEADER + "2026,Durga,Malikhedi kund,pre,pH,15,,\n", "outside the possible range"),
        (HEADER + "2026,Durga,Malikhedi kund,pre,BOD,-1,,\n", "outside the possible range"),
        (HEADER + "2026,Durga,Malikhedi kund,pre,Mercury,0.1,,\n", "not recognised"),
        (HEADER + "2026,Diwali,Malikhedi kund,pre,BOD,4,,\n", "must be Ganesh or Durga"),
        (HEADER + "26,Durga,Malikhedi kund,pre,BOD,4,,\n", "4-digit year"),
        (HEADER + "2026,Durga,Malikedi,pre,BOD,4,,\n", "not a known ghat"),
        (HEADER + "2026,Durga,Malikhedi kund,pre,BOD,4,,\n2026,Durga,Malikhedi kund,pre,BOD,5,,\n",
         "more than once"),
        (HEADER + "2024,Ganesh,Malikhedi kund,pre,BOD,9,,\n", "cannot overwrite report values"),
    ],
)
def test_malformed_upload_gives_friendly_error(ctx, text: str, expected: str) -> None:
    res = check(ctx, text)
    assert not res.ok and res.rows is None
    assert any(expected in e for e in res.errors), res.errors


def test_binary_garbage_is_a_friendly_error(ctx) -> None:
    res = validate_upload(b"\x89PNG\r\n\x1a\n\x00\x00\xff\xfe", ctx["base"], RULES, ctx["limits"])
    assert not res.ok and res.errors


def test_errors_are_capped_and_counted(ctx) -> None:
    text = HEADER + "".join(f"2026,Durga,Nowhere {i},pre,BOD,4,,\n" for i in range(30))
    res = check(ctx, text)
    assert len(res.errors) == 21 and res.errors[-1] == "... and 10 more."


def test_bdl_and_flags_accepted(ctx) -> None:
    text = (HEADER + "2026,Durga,Malikhedi kund,pre,Lead,,BDL,\n"
            "2026,Durga,Malikhedi kund,pre,BOD,,not sampled,\n"
            "2026,Durga,Malikhedi kund,during,Zinc,ND,,\n")
    res = check(ctx, text)
    assert res.ok, res.errors
    assert list(res.rows["status"]) == ["below_detection", "missing", "below_detection"]
