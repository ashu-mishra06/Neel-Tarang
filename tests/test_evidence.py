"""Evidence rows, source links (T6), page images and the gap register (gate G3)."""

import re

import pandas as pd
import pytest

from scoring.config import load_rules, repo_path
from scoring.evidence import (
    RESULT_BDL,
    RESULT_BREACH,
    RESULT_MISSING,
    RESULT_NO_LIMIT,
    RESULT_OK,
    USER_SUPPLIED,
    build_evidence,
    evidence_for_frame,
    page_text,
    render_page_image,
    report_url,
    result_label,
)
from scoring.gaps import build_gap_register
from scoring.limits import evaluate_frame, limits_from_rules
from scoring.loader import BELOW_DETECTION, MISSING, VALUE, load_readings

RULES = load_rules()
LIMITS = limits_from_rules(RULES)
REAL = repo_path(RULES["data"]["readings_csv"]).exists()
PDFS = all(repo_path(r["file"]).exists() for r in RULES["reports"].values())
needs_real = pytest.mark.skipif(not REAL, reason="organisers' CSV not present")
needs_pdfs = pytest.mark.skipif(not (REAL and PDFS), reason="report PDFs not present")


@pytest.fixture(scope="module")
def all_evidence():
    df = load_readings(rules=RULES)
    return evidence_for_frame(evaluate_frame(df, LIMITS), LIMITS, RULES)


# ---------- labels and links (no data needed) ----------


@pytest.mark.parametrize(
    "status, scored, breach, expected",
    [
        (VALUE, True, True, RESULT_BREACH),
        (VALUE, True, False, RESULT_OK),
        (MISSING, True, None, RESULT_MISSING),
        (BELOW_DETECTION, False, None, RESULT_BDL),
        (VALUE, False, None, RESULT_NO_LIMIT),
    ],
)
def test_result_label(status: str, scored: bool, breach, expected: str) -> None:
    assert result_label(status, scored, breach) == expected


def test_report_url_appends_page() -> None:
    assert report_url("2025", "28", RULES) == (
        "https://www.mppcb.mp.gov.in/proc/mon/Ganesh_and_Durga_visarjan_report-2025.pdf#page=28")
    assert report_url("2023", 60, RULES).endswith("Idol_immer._Report_23_CPCB.pdf#page=60")
    assert report_url("2019", 5, RULES) == ""  # unknown year: no made-up link


def _tiny(rows: list[dict]) -> pd.DataFrame:
    base = {"ghat": "G", "festival": "Durga", "year": "2024", "flag": "", "value": "",
            "source_page": "30", "value_as_printed": ""}
    return evaluate_frame(pd.DataFrame([{**base, **r} for r in rows]), LIMITS)


def test_missing_and_bdl_never_look_clean_or_zero() -> None:
    df = _tiny([
        {"parameter": "BOD", "phase": "pre", "status": MISSING, "value_num": None,
         "flag": "not sampled"},
        {"parameter": "Lead", "phase": "pre", "status": BELOW_DETECTION, "value_num": None,
         "flag": "BDL", "value_as_printed": "BDL"},
    ])
    bod, lead = evidence_for_frame(df, LIMITS, RULES)
    assert (bod.result, bod.breach, bod.value) == (RESULT_MISSING, None, None)
    assert (lead.result, lead.value, lead.limit) == (RESULT_BDL, None, RESULT_NO_LIMIT)


def test_user_supplied_rows_have_no_report_link() -> None:
    df = _tiny([
        {"parameter": "BOD", "phase": "pre", "status": VALUE, "value_num": 4.0, "value": "4",
         "source_page": ""},
        {"parameter": "BOD", "phase": "during", "status": VALUE, "value_num": 5.0, "value": "5",
         "source": "uploaded"},
    ])
    for e in evidence_for_frame(df, LIMITS, RULES):
        assert e.source == USER_SUPPLIED and e.source_page == USER_SUPPLIED
        assert e.report_url_with_page == "" and e.report_name == ""


def test_unknown_ghat_has_no_evidence() -> None:
    other = _tiny([{"parameter": "BOD", "phase": "pre", "status": VALUE, "value_num": 4.0}])
    assert build_evidence("Nowhere ghat", other, RULES, LIMITS) == []


# ---------- real data (gate G3) ----------


@needs_real
def test_every_row_has_page_within_report_range(all_evidence) -> None:
    """T6."""
    assert len(all_evidence) == 1524
    for e in all_evidence:
        low, high = RULES["reports"][e.year]["page_range"]
        assert low <= int(e.source_page) <= high, (e.ghat, e.year, e.source_page)
        assert e.report_url_with_page.endswith(f"#page={int(e.source_page)}")


@needs_real
def test_scored_parameters_listed_first(all_evidence) -> None:
    rows = build_evidence("Malikhedi kund", rules=RULES, limits=LIMITS)
    scored_flags = [e.scored for e in rows]
    assert scored_flags == sorted(scored_flags, reverse=True)
    assert {e.parameter for e in rows if e.scored} == set(LIMITS)


@needs_real
def test_unpaired_breach_marked_in_evidence() -> None:
    rows = build_evidence("Malikhedi kund", rules=RULES, limits=LIMITS)
    hit = [e for e in rows if e.unpaired_breach]
    assert {(e.parameter, e.value, e.year, e.phase, e.source_page) for e in hit} == {
        ("Dissolved oxygen", 0.6, "2025", "during", "29"), ("BOD", 5.8, "2025", "during", "29")}


@needs_real
def test_missing_cells_say_not_sampled(all_evidence) -> None:
    missing = [e for e in all_evidence if e.status == MISSING]
    assert missing and all(e.result == RESULT_MISSING and e.breach is None for e in missing)


@needs_pdfs
def test_every_printed_value_appears_on_cited_page() -> None:
    """Every value_as_printed is found on its cited PDF page (spaces ignored for * marks)."""
    df = load_readings(rules=RULES)
    cache: dict[tuple[str, str], set[str]] = {}
    misses = []
    for r in df[df["value_as_printed"] != ""].itertuples():
        key = (r.year, r.source_page)
        if key not in cache:
            lines = page_text(r.year, r.source_page, RULES).splitlines()
            cache[key] = {t for line in lines for t in (*line.split(), line.replace(" ", ""))}
        if r.value_as_printed not in cache[key]:
            misses.append((r.ghat, r.year, r.source_page, r.parameter, r.value_as_printed))
    assert misses == []


@needs_pdfs
def test_every_site_name_appears_on_cited_page() -> None:
    df = load_readings(rules=RULES)
    skip = {"bhopal", "visarjan", "ghat", "kund"}
    for (year, page, site), _ in df.groupby(["year", "source_page", "site_as_printed"]):
        text = page_text(year, page, RULES).lower()
        words = [w for w in re.findall(r"[a-z]{4,}", site.lower()) if w not in skip]
        assert any(w in text for w in words), (year, page, site)


@needs_pdfs
def test_render_page_image_and_cache(tmp_path) -> None:
    rules = {**RULES, "pages_cache_dir": str(tmp_path / "pages")}
    first = render_page_image("2025", 29, rules)
    assert first.exists() and first.stat().st_size > 10_000
    mtime = first.stat().st_mtime_ns
    assert render_page_image("2025", "29", rules).stat().st_mtime_ns == mtime  # cached
    with pytest.raises(ValueError):
        render_page_image("2025", 999, rules)
    with pytest.raises(ValueError):
        render_page_image("2019", 1, rules)


# ---------- gap register ----------


@needs_real
def test_gap_register_contents() -> None:
    gaps = {g.id: g for g in build_gap_register(rules=RULES)}
    tables = gaps["missing_tables"].items
    assert "Bairagarh (Sant Hirdaram) kund: no Durga 2025 table" in tables
    assert "Malikhedi kund: no Durga 2025 table" in tables
    assert gaps["designated_not_in_data"].ghats == ["Arch Bridge"]
    assert set(gaps["in_use_not_designated"].ghats) == {
        "Shahpura lake ghat", "Rani Kamlapati ghat / Kamla Park kund"}
    assert "not_on_2026_list" not in gaps  # every ranked ghat is on a reported 2026 list
    assert gaps["site_match_uncertain"].ghats == ["Rani Kamlapati ghat / Kamla Park kund"]
    for required in ("not_sampled", "units_assumed", "only_four_metals", "lake_vs_kund",
                     "unpaired_breaches", "single_column_tables"):
        assert required in gaps, required


@needs_real
def test_gap_register_metal_counts_add_up() -> None:
    gaps = {g.id: g for g in build_gap_register(rules=RULES)}
    for item in gaps["only_four_metals"].items:
        q, b, m = map(int, re.findall(r"(\d+) ", item))
        assert q + b + m == 120, item
    assert "Chromium: 50 quantified, 65 BDL, 5 not sampled" in gaps["only_four_metals"].items
