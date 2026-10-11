"""Bilingual forwardable brief, filled from engine numbers by Jinja2 templates.

No LLM: every number comes from the engine's Scores. EN and HI use the same
pre-formatted number strings, so their numbers are identical (test T7).
"""

from __future__ import annotations

from html import escape
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from scoring.config import load_rules, repo_path
from scoring.engine import Scores, score_all
from scoring.limits import Limit, load_limits
from scoring.reasons import num, worst_pair

HI = {
    "tier": {"High": "उच्च", "Medium": "मध्यम", "Low": "निम्न"},
    "confidence": {"High": "उच्च", "Medium": "मध्यम", "Low": "निम्न"},
    "driver": {
        "Poor before and worse during": "विसर्जन से पहले ही खराब, और विसर्जन के दौरान और खराब",
        "Already poor before immersion": "विसर्जन से पहले ही खराब",
        "Worsens with immersion": "विसर्जन के दौरान बिगड़ता है",
        "Elevated on several measures; no single large change":
            "कई मापों पर ऊँचा; कोई एक बड़ा बदलाव नहीं",
        "Lower concern on available data": "उपलब्ध आँकड़ों पर कम चिंता",
        "Not enough data to tell": "निष्कर्ष के लिए पर्याप्त आँकड़े नहीं",
    },
    "parameter": {"Dissolved oxygen": "घुलित ऑक्सीजन (DO)",
                  "BOD": "BOD", "pH": "pH"},
    "festival": {"Ganesh": "गणेश", "Durga": "दुर्गा"},
    "direction": {"rose": "बढ़कर", "fell": "घटकर"},
}


def _pages(readings: list[dict[str, Any]]) -> list[dict[str, str]]:
    by_year: dict[str, list[str]] = {}
    for r in readings:
        pages = by_year.setdefault(str(r["year"]), [])
        if str(r["source_page"]) not in pages:
            pages.append(str(r["source_page"]))
    return [{"year": y, "pages": "/".join(p)} for y, p in sorted(by_year.items())]


def key_fact(s: Any, limits: dict[str, Limit]) -> dict[str, Any]:
    """One key number per ghat, as pre-formatted strings shared by EN and HI."""
    if s.critical:
        return {"kind": "critical", "count": str(s.critical.count),
                "sources": _pages(s.critical.readings)}
    pair = worst_pair(s.matched_pairs, limits)
    if pair:
        return {"kind": "pair", "parameter": pair["parameter"],
                "pre": num(pair["pre"]), "during": num(pair["during"]),
                "unit": limits[pair["parameter"]].unit, "festival": pair["festival"],
                "year": str(pair["year"]), "page": str(pair["during_page"]),
                "direction": "fell" if limits[pair["parameter"]].rule == "min" else "rose"}
    top = max(s.parameters, key=lambda p: p.baseline or 0)
    return {"kind": "baseline", "parameter": top.parameter,
            "breaches": str(top.pre_breaches), "valid": str(top.pre_valid)}


def brief_context(scores: Scores, rules: dict[str, Any], limits: dict[str, Limit]
                  ) -> dict[str, Any]:
    """Everything the templates need. Numbers are strings formatted once, here."""
    top = scores.ranked[: rules["brief"]["top_n"]]
    missing_tables = sorted({
        (item.removeprefix("no ").removesuffix(" table"), s.ghat)
        for s in scores.ranked for item in s.confidence.missing_items
        if item.startswith("no ") and item.endswith(" table")})
    return {
        "date_en": rules["brief"]["date_en"], "date_hi": rules["brief"]["date_hi"],
        "n_ghats": str(len(scores.ranked)),
        "tiers": {k: f"{v:g}" for k, v in rules["scoring"]["tiers"].items()},
        "top": [{"name": s.ghat, "tier": s.tier, "driver": s.driver,
                 "confidence": s.confidence.level, "fact": key_fact(s, limits)} for s in top],
        "no_baseline": [b.ghat for b in scores.blind_spots],
        "missing_tables": [{"table": t, "ghat": g} for t, g in missing_tables],
        "hi": HI,
    }


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(str(repo_path("briefs"))),
                       undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True,
                       autoescape=False, keep_trailing_newline=True)


def render_text(lang: str, ctx: dict[str, Any]) -> str:
    """Plain text for pasting into a message. lang: "en" or "hi"."""
    return _env().get_template(f"{lang}.j2").render(**ctx).strip() + "\n"


def render_html(lang: str, ctx: dict[str, Any]) -> str:
    """Print-ready one-page HTML with the language attribute set."""
    body = escape(render_text(lang, ctx))
    fonts = ('"Noto Sans Devanagari", "Nirmala UI", "Mangal", sans-serif' if lang == "hi"
             else 'system-ui, "Segoe UI", Arial, sans-serif')
    title = "Visarjan Ghat Watch - brief" if lang == "en" else "विसर्जन घाट वॉच - सारांश"
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
            f"<title>{title}</title><style>@page {{ size: A4; margin: 18mm; }} "
            f"body {{ font-family: {fonts}; font-size: 12pt; line-height: 1.45; "
            "color: #1B1F24; max-width: 170mm; margin: auto; } "
            "pre { white-space: pre-wrap; font-family: inherit; }</style></head>"
            f"<body><pre>{body}</pre></body></html>")


def build_briefs(scores: Scores | None = None) -> dict[str, dict[str, str]]:
    rules = load_rules()
    limits = load_limits(rules=rules)
    ctx = brief_context(scores or score_all(rules=rules, limits=limits), rules, limits)
    return {lang: {"text": render_text(lang, ctx), "html": render_html(lang, ctx)}
            for lang in ("en", "hi")}


if __name__ == "__main__":
    for lang, out in build_briefs().items():
        print(f"===== {lang} ({len(out['text'].split())} words) =====\n{out['text']}")
