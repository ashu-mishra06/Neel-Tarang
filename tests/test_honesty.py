"""Appendix C honesty checks across the whole product (T4, T8, T10)."""

import re

import pytest

from scoring.config import load_rules, repo_path

ROOT = repo_path()
DENYLIST = ["disease", "illness", "unsafe to drink", "causes", "health risk"]
USER_FACING = [ROOT / "app.py", *sorted((ROOT / "scoring").glob("*.py")),
               *sorted((ROOT / "ui").glob("*.py")), *sorted((ROOT / "briefs").glob("*.j2"))]
NETWORK = re.compile(r"^\s*(import|from)\s+(requests|urllib|http|socket|httpx|aiohttp)\b", re.M)


@pytest.mark.parametrize("path", USER_FACING, ids=lambda p: p.name)
def test_no_health_effect_wording(path) -> None:
    """T8: denylist over every file that produces user-facing text."""
    text = path.read_text(encoding="utf-8").lower()
    assert not [w for w in DENYLIST if w in text]


@pytest.mark.parametrize("path", USER_FACING, ids=lambda p: p.name)
def test_no_network_libraries(path) -> None:
    """T10: the product works with no network; nothing imports a network client."""
    assert not NETWORK.search(path.read_text(encoding="utf-8"))


def test_no_llm_or_api_key_needed() -> None:
    """T10: no LLM client and no API key read anywhere in the product code."""
    for path in USER_FACING:
        text = path.read_text(encoding="utf-8")
        assert "anthropic" not in text.lower() and "API_KEY" not in text, path.name


@pytest.mark.skipif(not repo_path(load_rules()["data"]["readings_csv"]).exists(),
                    reason="organisers' CSV not present")
def test_missing_durga_2025_listed_in_ui() -> None:
    """T4 (UI part): the missing tables appear on screen, not only in the data."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(repo_path("app.py")), default_timeout=120).run()
    text = " ".join(m.value for m in at.markdown)
    assert "Bairagarh (Sant Hirdaram) kund: no Durga 2025 table" in text
    assert "Malikhedi kund: no Durga 2025 table" in text
