"""Brief: numbers match the engine (T7), EN == HI numbers, no health wording (T8)."""

import json
import re
from collections import Counter

import pytest

from scoring.brief import build_briefs, render_html
from scoring.config import load_rules, repo_path
from scoring.engine import Scores, score_all

RULES = load_rules()
pytestmark = pytest.mark.skipif(not repo_path(RULES["data"]["readings_csv"]).exists(),
                                reason="organisers' CSV not present")
NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w])")
DENYLIST = ["disease", "illness", "unsafe to drink", "causes", "health risk"]


@pytest.fixture(scope="module")
def scores() -> Scores:
    return score_all(rules=RULES)


@pytest.fixture(scope="module")
def briefs(scores: Scores) -> dict:
    return build_briefs(scores)


def numbers(text: str) -> Counter:
    return Counter(NUMBER.findall(text))


def test_en_and_hi_numbers_identical(briefs) -> None:
    """T7."""
    assert numbers(briefs["en"]["text"]) == numbers(briefs["hi"]["text"])


def test_every_brief_number_comes_from_engine_or_rules(briefs, scores: Scores) -> None:
    engine_json = json.dumps(scores.to_dict())
    allowed = set(NUMBER.findall(engine_json))
    allowed |= {f"{v:g}" for v in RULES["scoring"]["tiers"].values()}
    allowed |= set(NUMBER.findall(RULES["brief"]["date_en"])) | {"2023", "2025", "2026", "4"}
    allowed |= {str(len(scores.ranked)), "0", "1", "2", "3"}  # list numbering, ghat count
    extra = set(numbers(briefs["en"]["text"])) - allowed
    assert not extra, extra


def test_top_ghats_and_key_numbers(briefs, scores: Scores) -> None:
    text = briefs["en"]["text"]
    for s in scores.ranked[:3]:
        assert s.ghat in text and f"{s.tier} tier" in text
    assert "Dissolved oxygen reported at 0 mg/l 4 times" in text  # Bairagarh critical flag
    assert "BOD rose from 6.8 to 11.4 mg/l during immersion (Durga 2025, Report 2025 p.65)" \
        in text


def test_blind_spots_and_missing_tables_listed(briefs) -> None:
    """T4 (brief part): missing Durga 2025 tables and Arch Bridge appear."""
    for lang in ("en", "hi"):
        text = briefs[lang]["text"]
        assert "Arch Bridge" in text
        assert "Bairagarh (Sant Hirdaram) kund" in text and "Malikhedi kund" in text
    assert "no Durga 2025 table" in briefs["en"]["text"]
    assert "दुर्गा 2025 की तालिका नहीं" in briefs["hi"]["text"]


def test_english_brief_under_250_words(briefs) -> None:
    assert len(briefs["en"]["text"].split()) <= 250


def test_hindi_marked_as_draft_until_reviewed(briefs) -> None:
    status = repo_path("briefs/hi_review_status.md").read_text(encoding="utf-8")
    if "Status: reviewed" not in status:
        assert "needs human review" in briefs["hi"]["text"]


@pytest.mark.parametrize("name", ["en.j2", "hi.j2"])
def test_no_health_wording_in_templates(name: str) -> None:
    """T8."""
    text = repo_path("briefs", ).joinpath(name).read_text(encoding="utf-8").lower()
    assert not [w for w in DENYLIST if w in text]


def test_html_sets_language_and_escapes(briefs) -> None:
    assert '<html lang="hi">' in briefs["hi"]["html"]
    assert '<html lang="en">' in briefs["en"]["html"]
    assert "<script" not in render_html("en", {**_ctx_with_name("<script>x</script>")})


def _ctx_with_name(name: str) -> dict:
    from scoring.brief import brief_context
    from scoring.limits import load_limits

    limits = load_limits(rules=RULES)
    ctx = brief_context(score_all(rules=RULES, limits=limits), RULES, limits)
    ctx["top"][0]["name"] = name
    return ctx
