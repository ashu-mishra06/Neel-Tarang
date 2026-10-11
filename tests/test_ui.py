"""UI: Appendix B contrast, labels never colour-only, and an app smoke test."""

import re

import pytest

from scoring.config import load_rules, repo_path
from ui import components as ui
from ui.theme import MISSING, TIER


def _luminance(hex_colour: str) -> float:
    rgb = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(fg: str, bg: str) -> float:
    hi, lo = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("name", list(TIER))
def test_tier_pairs_meet_4_5_contrast(name: str) -> None:
    assert contrast(TIER[name]["fg"], TIER[name]["bg"]) >= 4.5


def test_missing_style_contrast() -> None:
    assert contrast(MISSING["fg"], MISSING["bg"]) >= 4.5


@pytest.mark.parametrize("tier", ["High", "Medium", "Low", "NoData"])
def test_tier_badge_has_icon_and_text(tier: str) -> None:
    badge = ui.tier_badge(tier)
    assert TIER[tier]["icon"] in badge and TIER[tier]["label"] in badge


def test_near_boundary_text() -> None:
    assert ui.near_boundary_text({"line": "High", "value": 27.5, "distance": -0.84}) == \
        "0.8 points below the High line (27.5)"


@pytest.mark.skipif(not repo_path(load_rules()["data"]["readings_csv"]).exists(),
                    reason="organisers' CSV not present")
def test_app_runs_and_shows_core_content() -> None:
    """Opens in Hindi; switching to English shows the same content in English."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(repo_path("app.py")), default_timeout=120).run()
    assert not at.exception
    page = lambda: " ".join([m.value for m in at.markdown] + [c.value for c in at.caption]  # noqa: E731
                            + [h.value for h in at.subheader])
    hindi = page()
    for needle in ("दुर्गा विसर्जन: 20 अक्टूबर 2026", "कोई पिछला आँकड़ा नहीं", "Arch Bridge",
                   "श्रेणी रेखा के पास", "स्थान दो जगह हो सकता है", "सुरक्षा प्रमाणपत्र नहीं"):
        assert needle in hindi, needle
    assert len(at.tabs) >= 3
    assert len(at.get("arrow_vega_lite_chart")) >= 1  # overview chart + per-ghat charts
    at.sidebar.radio(key="lang").set_value("English").run()
    assert not at.exception
    english = page()
    for needle in ("Durga visarjan: 20 Oct 2026 | Standard: CPCB class B", "No baseline",
                   "Near tier line", "Site may be two places", "not sampled",
                   "not a safety certification"):
        assert needle in english, needle


def test_hindi_reasons_use_engine_numbers() -> None:
    from scoring.brief import fact_sentence, key_fact
    from scoring.engine import score_all
    from scoring.limits import load_limits

    rules = load_rules()
    limits = load_limits(rules=rules)
    for s in score_all(rules=rules, limits=limits).ranked:
        fact = key_fact(s, limits)
        nums = lambda x: sorted(re.findall(r"\d+(?:\.\d+)?", x))  # noqa: E731
        assert nums(fact_sentence(fact, "hi")) == nums(fact_sentence(fact, "en"))


@pytest.mark.skipif(not repo_path(load_rules()["data"]["readings_csv"]).exists(),
                    reason="organisers' CSV not present")
def test_brief_defaults_to_hindi() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(repo_path("app.py")), default_timeout=120).run()
    assert at.radio(key="brief_lang").value.startswith("हिन्दी")
    assert "घुलित ऑक्सीजन" in at.code[0].value


def test_rules_reload_when_file_changes(tmp_path) -> None:
    import os
    import time

    f = tmp_path / "r.yaml"
    f.write_text("a: 1\n", encoding="utf-8")
    assert load_rules(f)["a"] == 1
    f.write_text("a: 2\n", encoding="utf-8")
    later = time.time() + 5
    os.utime(f, (later, later))
    assert load_rules(f)["a"] == 2


def test_pairs_chart_arrow_follows_direction() -> None:
    from types import SimpleNamespace

    from scoring.limits import limits_from_rules
    from ui.charts import pairs_chart

    s = SimpleNamespace(matched_pairs=[
        {"parameter": "Dissolved oxygen", "festival": "Durga", "year": "2024", "pre": 4.2,
         "during": 2.2, "worsening": 2.0},
        {"parameter": "Dissolved oxygen", "festival": "Ganesh", "year": "2023", "pre": 5.0,
         "during": 6.0, "worsening": -1.0}], unpaired_breaches=[])
    spec = pairs_chart(s, "Dissolved oxygen", limits_from_rules(load_rules())["Dissolved oxygen"],
                       "unpaired")
    rows = spec["layer"][0]["data"]["values"]
    assert [(r["dir"], r["change"]) for r in rows] == [("down", "worse"),
                                                       ("up", "same or better")]
    assert spec["layer"][-1]["data"]["values"] == [{"limit": 5.0}]  # class B limit line
