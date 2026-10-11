# Neel Tarang (नील तरंग)

A tool for Track 2, Visarjan Ghat Watch. It shows which Bhopal immersion ghats need attention before **Durga visarjan
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
git clone https://github.com/ashu-mishra06/Neel-Tarang.git
cd Neel-Tarang
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

No API key, no network and no setup screen are needed. Tested on Python 3.14
(Windows); `requirements.txt` is pinned.

Run the tests with `pytest` (252 tests). Print the ranking in a terminal with
`python -m scoring.engine`.

## What the officer sees

The app opens in **Hindi**; the **English** toggle sits top-right. A top
navigation bar splits it into five sections: **Ghats** (landing page) · **Test
planner** · **Brief** · **Add readings** · **Gaps & method**. The Ghats page
starts with summary cards and a chart of *why* each ghat ranks where it does
(before immersion vs worse during immersion).

1. **Ranked ghats:** rank, tier (icon + text + colour), driver ("why"),
   confidence, and a one-line reason with its report page. Flags on the row:
   near a tier line, site name may be two places, reported 0 mg/l dissolved
   oxygen, breaches that cannot be compared, not on the reported 2026 list.
   Open a row for the detail view: baseline vs festival numbers, per-parameter
   values, matched before/during pairs, every reading with the report page
   image, missing items and the gaps for that ghat.
   Each row carries a persistence badge, e.g. "BOD above limit during
   immersion in 6 of 6 tables". The detail view has before/during charts per
   parameter against the CPCB limit.
2. **Test planner:** "I can test N ghats before 20 Oct" gives an ordered list
   (high risk and thin data first), with reasons and what the data suggests
   testing. Arch Bridge is listed separately as "No baseline".
3. **No baseline:** Arch Bridge (on the reported 2026 list, no past readings).
   No score and no tier.
4. **Brief (हिन्दी / EN):** a one-page brief with copy and download (text or
   print-ready HTML). The Hindi brief has been reviewed by the team.
5. **Re-score (week after, Add readings):** upload new readings in the same CSV columns
   (sample with invented values in `data/samples/`). The ranking updates, a
   "what changed" table shows rank/tier/score before -> after, and uploaded
   rows are marked "user-supplied". Bad files get a plain list of problems.
6. **Gaps & method:** the gap register, the method note (`docs/METHOD.md`) and
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
- Re-score with uploaded readings, with validation and a "what changed" table.
- The English brief and Hindi draft are generated from the same engine
  numbers. A test checks that the numbers are identical.
- Numbers come only from `scoring/`. No LLM is used at run time.

**Doesn't / not yet**
- The Hindi *interface* text is a draft. The Hindi brief is reviewed; the brief's new
  persistence line needs a quick re-check (`briefs/hi_review_status.md`).
- The human spot-check of 10 evidence rows (N2) is pending; see
  `docs/METHOD.md`.
- The usability test with a non-technical teammate has not been run.
- The driver label "Already poor before immersion" uses the uncalibrated
  0.40 baseline cut-off from the brief; no ghat currently gets it.
- Report links point to the public MPPCB PDFs. They were checked against the
  local copies in `resources/`, not opened online.
- The 2026 ghat lists come from press reports (FPJ 22 and 24 Sep 2026), both
  for Ganesh. The Durga list may differ (confirm with BMC).

## Data

- `data/`: the organisers' files, **unchanged** (byte-for-byte; see
  `.gitattributes`). Source PDFs are in `resources/`. Links are in
  `data/DATA_DICTIONARY.md`.
- `data/context/designated_ghats_2026.csv`: the Ganesh 2026 designated ghats
  as reported by Free Press Journal on 22 Sep 2026: [BMC Deploys 174 Divers At Bhopal Ghats For Ganesh Idol Immersion](https://www.freepressjournal.in/bhopal/bmc-deploys-174-divers-at-bhopal-ghats-for-ganesh-idol-immersion).
  A second report (FPJ 24 Sep 2026,
  [Nearly 30 Ganpati Collection Stalls Set Up...](https://www.freepressjournal.in/bhopal/bhopal-ganesh-visarjan-2026-nearly-30-ganpati-collection-stalls-set-up-180-divers-deployed-khatlapura-ghat-prempura-ghat-ready-ahead-of-anant-chaturdashi))
  lists Shahpura and Rani Kamlapati as in use. Context only: used for the
  "No baseline" section and the 2026-list labels.
- `data/mp_immersion_sites_2023_2025.csv` (statewide): **not used**. It was
  planned as a less-checked context benchmark only (Level 7D, cut).
- Derived output is in `data/derived/`: `ghat_scores.json`, `evidence.csv`,
  `gap_register.json`; page images are cached in `pages/` and not committed.

## Not included

- **Level 7 enhancements cut for time:** 7C share card (text + image) and 7D
  statewide benchmark. 7A persistence badge and 7B test planner are included.
- **Level 9 stretch:** lake cross-check, map view, "ask the data" box.
- **PDF export of the brief:** the brief is print-ready HTML and plain text.
- **Embedded Noto Sans Devanagari font:** the Hindi HTML uses system fonts
  (Noto Sans Devanagari / Nirmala UI / Mangal if installed).

## Deploy (Streamlit Community Cloud)

1. The repo is public: https://github.com/ashu-mishra06/Neel-Tarang
2. On share.streamlit.io: New app -> pick the repo, branch, and `app.py`.
3. Advanced settings: Python 3.12. No secrets are needed.
4. Open the link on a phone and check that the ranked list loads.

The app needs nothing beyond `requirements.txt`. Page images are rendered from
the PDFs in `resources/` on first view.

## Licence

MIT. See `LICENSE`. Offered to the Government of Madhya Pradesh through MPSeDC.
