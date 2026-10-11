# Visarjan Ghat Watch

Shows which Bhopal immersion ghats need attention before **Durga visarjan
(20 Oct 2026)**, and **why**: was the water already poor before immersion, or
did it get worse during immersion? Every number links back to the MPPCB report
page it came from. Missing data is shown as missing, never as clean.

- **Track:** 2 (Visarjan Ghat Watch). Claude Impact Lab x Cerebras Cafe Compute, Bhopal, 11 Oct 2026
- **Team:** : Secretos
- **Members:** : Ashutosh Mishra
- **The one user:** a Bhopal Municipal Corporation (BMC) officer planning Durga
  visarjan, deciding where to send extra cleaning, aeration and water testing.

> **Honesty note:** the persona and needs are inferred from the problem
> statement, not from interviews.

## How to run (5 steps)

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

No API key, no network and no setup screen are needed. Tested on Python 3.14
(Windows); `requirements.txt` is pinned.

Run the tests with `pytest` (153 tests). Print the ranking in a terminal with
`python -m scoring.engine`.

## What the officer sees

1. **Ranked ghats:** rank, tier (icon + text + colour), driver ("why"),
   confidence, and a one-line reason with its report page. Flags on the row:
   near a tier line, site name may be two places, reported 0 mg/l dissolved
   oxygen, breaches that cannot be compared, not on the reported 2026 list.
   Open a row for the detail view: baseline vs festival numbers, per-parameter
   values, matched before/during pairs, every reading with the report page
   image, missing items and the gaps for that ghat.
2. **No baseline:** Arch Bridge (on the reported 2026 list, no past readings).
   No score and no tier.
3. **Brief (EN / हिन्दी):** a one-page brief with copy and download (text or
   print-ready HTML). The Hindi version is a draft, marked "needs human
   review".
4. **Gaps & method:** the gap register, the method note (`docs/METHOD.md`) and
   downloads of the derived data (scores JSON, gap register, evidence CSV).

## What works and what doesn't

**Works**
- Scoring engine (`scoring/`) with baseline vs festival split, confidence,
  matched-pair driver labels and blind spots. All settings are in
  `rules.yaml`.
- The golden counts reproduce: DO 116 valid / 42 below 5 mg/l; BOD 112 valid
  / 100 above 3 mg/l.
- Every printed value (1,476) was found on its cited PDF page (automated
  check). Five page images were checked by eye.
- The English brief and Hindi draft are generated from the same engine
  numbers. A test checks that the numbers are identical.
- Numbers come only from `scoring/`. No LLM is used at run time.

**Doesn't / not yet**
- Hindi text is **not reviewed** by a fluent speaker (`briefs/hi_review_status.md`).
- The human spot-check of 10 evidence rows (N2) is pending; see
  `docs/METHOD.md`.
- The usability test with a non-technical teammate has not been run.
- The driver label "Already poor before immersion" uses the uncalibrated
  0.40 baseline cut-off from the brief; no ghat currently gets it.
- Report links point to the public MPPCB PDFs. They were checked against the
  local copies in `resources/`, not opened online.
- The 2026 designated-ghat list comes from a press report. The article URL
  is still to be added, and the Durga list may differ (confirm with BMC).

## Data

- `data/`: the organisers' files, **unchanged** (byte-for-byte; see
  `.gitattributes`). Source PDFs are in `resources/`. Links are in
  `data/DATA_DICTIONARY.md`.
- `data/context/designated_ghats_2026.csv`: the Ganesh 2026 designated ghats
  as reported by Free Press Journal on 22 Sep 2026 (_TODO: add article URL_).
  Context only. It is used for the "No baseline" section and the "not on the
  2026 list" label.
- `data/mp_immersion_sites_2023_2025.csv` (statewide): **not used**. It was
  planned as a less-checked context benchmark only (Level 7D, cut).
- Derived output is in `data/derived/`: `ghat_scores.json`, `evidence.csv`,
  `gap_register.json`; page images are cached in `pages/` and not committed.

## Not included

- **Level 6, re-score with uploaded readings:** not built yet; planned
  next.
- **Level 7 enhancements, cut for time:** 7A persistence badge, 7B test
  planner, 7C share card (text + image), 7D statewide benchmark.
- **Level 9 stretch:** lake cross-check, map view, "ask the data" box.
- **PDF export of the brief:** the brief is print-ready HTML and plain text.
- **Embedded Noto Sans Devanagari font:** the Hindi HTML uses system fonts
  (Noto Sans Devanagari / Nirmala UI / Mangal if installed).

## Deploy (Streamlit Community Cloud)

1. Push this repo to a **public** GitHub repo.
2. On share.streamlit.io: New app -> pick the repo, branch, and `app.py`.
3. Advanced settings: Python 3.12. No secrets are needed.
4. Open the link on a phone and check that the ranked list loads.

The app needs nothing beyond `requirements.txt`. Page images are rendered from
the PDFs in `resources/` on first view.

## Licence

MIT. See `LICENSE`. Offered to the Government of Madhya Pradesh through MPSeDC.
