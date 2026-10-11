"""Evidence: every reading with its limit, result and a link to the report page.

Run `python -m scoring.evidence` to write data/derived/evidence.csv.
No Streamlit, no network (links are only built, never fetched).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from scoring.config import load_rules, repo_path
from scoring.limits import Limit, evaluate_frame, limit_text, load_limits
from scoring.loader import BELOW_DETECTION, MISSING, load_readings
from scoring.pairs import unpaired_breaches

RESULT_BREACH = "breach"
RESULT_OK = "within limit"
RESULT_MISSING = "not sampled"
RESULT_BDL = "BDL - very low, not zero"
RESULT_NO_LIMIT = "no class B limit"
USER_SUPPLIED = "user-supplied"
PHASE_ORDER = {"pre": 0, "during": 1, "after": 2}


@dataclass
class EvidenceRow:
    ghat: str
    parameter: str
    scored: bool
    value: float | None
    value_as_printed: str
    unit: str
    limit: str
    result: str
    breach: bool | None
    status: str
    flag: str
    year: str
    festival: str
    phase: str
    source_page: str
    source: str  # "report" or "user-supplied"
    report_name: str
    report_url_with_page: str
    unpaired_breach: bool


def report_info(year: str, rules: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Report metadata for a year, or None if the year has no known report."""
    return (rules or load_rules())["reports"].get(str(year))


def report_url(year: str, page: str | int, rules: dict[str, Any] | None = None) -> str:
    """Public report URL opened at the page, e.g. ...report-2025.pdf#page=28."""
    info = report_info(year, rules)
    return f"{info['url']}#page={int(page)}" if info and str(page).strip() else ""


def result_label(status: str, scored: bool, breach: Any) -> str:
    """Plain-words result. Missing is never shown as clean; BDL is never zero."""
    if status == MISSING:
        return RESULT_MISSING
    if status == BELOW_DETECTION:
        return RESULT_BDL
    if not scored:
        return RESULT_NO_LIMIT
    return RESULT_BREACH if bool(breach) else RESULT_OK


def _is_user_supplied(row: Any) -> bool:
    return getattr(row, "source", "") == "uploaded" or not str(row.source_page).strip()


def _unit(row: Any, limits: dict[str, Limit]) -> str:
    if row.parameter in limits:
        return limits[row.parameter].unit
    return str(getattr(row, "unit_assumed", "") or "")


def _row(r: Any, limits: dict[str, Limit], unpaired: set[tuple], rules: dict[str, Any]
         ) -> EvidenceRow:
    scored = r.parameter in limits
    user = _is_user_supplied(r)
    info = None if user else report_info(r.year, rules)
    breach = None if pd.isna(r.breach) else bool(r.breach)
    return EvidenceRow(
        ghat=r.ghat, parameter=r.parameter, scored=scored,
        value=None if pd.isna(r.value_num) else float(r.value_num),
        value_as_printed=str(getattr(r, "value_as_printed", "") or r.value),
        unit=_unit(r, limits), limit=limit_text(limits[r.parameter]) if scored else RESULT_NO_LIMIT,
        result=result_label(r.status, scored, breach), breach=breach, status=r.status,
        flag=str(r.flag or ""), year=str(r.year), festival=r.festival, phase=r.phase,
        source_page=USER_SUPPLIED if user else str(r.source_page),
        source=USER_SUPPLIED if user else "report",
        report_name=info["name"] if info else "",
        report_url_with_page="" if user else report_url(r.year, r.source_page, rules),
        unpaired_breach=(r.parameter, r.festival, str(r.year), r.phase) in unpaired,
    )


def _sort_key(e: EvidenceRow, order: dict[str, int]) -> tuple:
    return (not e.scored, order.get(e.parameter, 99), e.parameter, e.year, e.festival,
            PHASE_ORDER.get(e.phase, 9))


def evidence_for_frame(scored: pd.DataFrame, limits: dict[str, Limit],
                       rules: dict[str, Any]) -> list[EvidenceRow]:
    """Evidence rows for every reading in an evaluated frame (any number of ghats)."""
    rows: list[EvidenceRow] = []
    order = {name: i for i, name in enumerate(limits)}
    for _, g in scored.groupby("ghat", sort=True):
        unpaired = {(u["parameter"], u["festival"], str(u["year"]), u["phase"])
                    for u in unpaired_breaches(g, limits)}
        ghat_rows = [_row(r, limits, unpaired, rules) for r in g.itertuples()]
        rows += sorted(ghat_rows, key=lambda e: _sort_key(e, order))
    return rows


def build_evidence(ghat: str, df: pd.DataFrame | None = None,
                   rules: dict[str, Any] | None = None,
                   limits: dict[str, Limit] | None = None) -> list[EvidenceRow]:
    """All readings for one ghat: scored parameters first, then context parameters."""
    rules = rules or load_rules()
    limits = limits or load_limits(rules=rules)
    df = load_readings(rules=rules) if df is None else df
    g = df[df["ghat"] == ghat]
    if g.empty:
        return []
    return evidence_for_frame(evaluate_frame(g, limits), limits, rules)


# ---------- page images ----------


def render_page_image(year: str, page: str | int, rules: dict[str, Any] | None = None,
                      zoom: float = 1.5) -> Path:
    """Render one report page (1-based PDF page) to PNG, cached in data/derived/pages/."""
    import fitz  # PyMuPDF; imported here so the engine does not need it

    rules = rules or load_rules()
    info = report_info(year, rules)
    if info is None:
        raise ValueError(f"No report configured for year {year}")
    out = repo_path(rules["pages_cache_dir"]) / f"{year}_p{int(page):03d}.png"
    if out.exists():
        return out
    pdf = repo_path(info["file"])
    if not pdf.exists():
        raise FileNotFoundError(f"Report PDF not found: {pdf}")
    with fitz.open(pdf) as doc:
        if not 1 <= int(page) <= doc.page_count:
            raise ValueError(f"Page {page} outside 1..{doc.page_count} in {pdf.name}")
        out.parent.mkdir(parents=True, exist_ok=True)
        doc[int(page) - 1].get_pixmap(matrix=fitz.Matrix(zoom, zoom)).save(out)
    return out


def page_text(year: str, page: str | int, rules: dict[str, Any] | None = None) -> str:
    """Plain text of one report page (used to verify evidence against the PDF)."""
    import fitz

    info = report_info(year, rules or load_rules())
    with fitz.open(repo_path(info["file"])) as doc:
        return doc[int(page) - 1].get_text()


# ---------- export ----------


def export_evidence(path: Path | None = None) -> Path:
    rules = load_rules()
    limits = load_limits(rules=rules)
    scored = evaluate_frame(load_readings(rules=rules), limits)
    rows = evidence_for_frame(scored, limits, rules)
    path = path or repo_path(rules["evidence_csv"])
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([asdict(r) for r in rows]).to_csv(path, index=False, encoding="utf-8")
    return path


if __name__ == "__main__":
    print(f"Wrote {export_evidence()}")
