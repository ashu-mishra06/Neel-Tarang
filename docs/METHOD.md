# Method note

## Reading status (Level 1)

Each reading gets one status:

| Status | When | How it is used |
|---|---|---|
| `value` | a number, with no missing/BDL flag | scored |
| `missing` | flag `not sampled`, `*`, `**`; or blank; or unreadable text | excluded from rates, lowers confidence, never counted as clean |
| `below_detection` | flag `BDL` or `ND` | not a breach, never zero, not missing |

Flags take priority over numbers, so a `0` marked `BDL` is never read as 0.
BDL/ND on a scored parameter (pH, DO, BOD) is unexpected; the loader warns
and records it for the gap register.

## Limits (CPCB class B)

| Parameter | Breach if | Exceedance (0..1) |
|---|---|---|
| pH | outside 6.5-8.5 | distance outside / 1.5 |
| Dissolved oxygen | below 5 mg/l | (5 - v) / 5 |
| BOD | above 3 mg/l | (v - 3) / 3 |

Values live in `rules.yaml` and are checked against the class B rows of
`data/cpcb_water_quality_criteria.csv` on every load; the engine stops if
they differ.

## Data provenance

The organisers' files come from the archive
`bhopal-impact-lab-2026-problem-statements-main.zip`, folder
`track-2-visarjan-ghat-watch/`. They were copied unchanged: `data/*.csv` and
`data/DATA_DICTIONARY.md` into `data/`, report PDFs into `resources/`.

## Verification

Level 1, 11 Oct 2026. The counts below were made twice, once by plain pandas
outside the engine and once through `scoring.loader`. Both agree with the
brief.

| Check | Result |
|---|---|
| Rows / ghats / years | 1,524 / 7 / 2023-2025 |
| Cells per scored parameter | 120 each (pH, DO, BOD) |
| DO valid / below 5 mg/l | 116 / 42 |
| BOD valid / above 3 mg/l | 112 / 100 |
| pH valid / outside 6.5-8.5 | 115 / 6 |
| Missing on scored parameters | BOD 8 not sampled; DO 4; pH 1 not sampled + 2 `*` + 2 `**` |
| BDL | 174, all on metals (Cr 65, Pb 52, Cu 36, Zn 21); none on scored parameters |
| Reported DO = 0 mg/l | 4 |
| Status totals | value 1,289 / missing 61 / below_detection 174 |

## Scoring (Level 2)

Implements core.txt Appendix A. All weights and cut-offs are in `rules.yaml`
under `scoring:`. Run `python -m scoring.engine` to print the ranking and
write `data/derived/ghat_scores.json` with every component visible.

- **Baseline** (pre-immersion only): 0.5 x breach rate + 0.5 x mean
  exceedance over valid pH, DO and BOD readings.
- **Festival effect**: for each festival-year-parameter with valid pre and
  during readings, 0.7 x worsening (pre to during) + 0.3 x worsening (pre to
  after); during only if after is missing. Improvement counts as 0.
- **Risk** = 100 x (0.5 x baseline + 0.5 x festival). If one part cannot be
  computed, risk uses the other part alone (re-weighted) and the driver says
  "Not enough data to tell". A missing part is never treated as 0.
- **Confidence** = valid scored readings / expected (festival-years in the
  data x 3 phases x 3 parameters = 54). Every missing table and cell is
  listed. If the most recent Durga table is absent, confidence is at most
  Medium.
- **Ranking**: tier, then risk score, then lower confidence first, then name.
- **Blind spots**: ghats with no valid readings, and 2026 designated ghats
  with no data (Arch Bridge), are listed but never ranked or scored.
- **Reason text**: filled from numbers by a template. It names the parameter
  with the largest baseline part and, if different, the parameter that
  worsened most, plus the source page of the worst reading.

### Decisions (core.txt Section 8)

- **D1 tier cut-offs.** With the placeholder cut-offs (High 60, Medium 35)
  all 7 ghats scored Low (observed range 13.9-33.6), so the tiers said
  nothing. The final cut-offs are tied to the driver cut-offs, not fitted to
  the seven scores:
  - High >= 27.5 = 100 x (0.5 x 0.40 + 0.5 x 0.15): a ghat at both the
    "poor before" and "worsens" levels.
  - Medium >= 20 = 100 x (0.5 x 0.40): a ghat at the "poor before" level
    alone.

  Result: High 3, Medium 3, Low 1. The rejected alternative was tertiles of
  the observed scores (Medium 24, High 30), which put Shahpura (30.8) and
  Hathaikheda (29.7) in different tiers over a 1.1-point gap. Weights stay at
  0.5 / 0.5. Tiers never change the order within the ranking except through
  the critical flag below.
- **D2 critical flag.** Any reported DO of exactly 0 mg/l lifts the tier to
  at least High. It is labelled as the team's own flag, not a CPCB limit.
  Bairagarh has 4 such readings (2023 Durga pre and during p.60, 2023 Ganesh
  after p.26, 2025 Ganesh during p.28) and is High on its score anyway.
- **D3 Rani Kamlapati / Kamla Park.** Kept as one ghat with the label "Site
  name match is medium confidence - may cover two places".
- **D4 not on the reported 2026 list.** Shahpura and Rani Kamlapati stay in
  the ranking with the label "Not on reported 2026 list - confirm with BMC".
  The link from designated names to data names is the explicit `data_site`
  column in `data/context/designated_ghats_2026.csv`.

### Things to know when reading the scores

- BOD breaches its limit in most pre-immersion readings at every ghat, so
  BOD drives most baselines. That is why the baseline and festival parts are
  kept apart.
- The festival effect averages over all three parameters. A ghat where only
  DO drops (Malikhedi: 5.4 to 4.0 mg/l on average) gets a modest festival
  score (0.10), though the reason text names the drop.
