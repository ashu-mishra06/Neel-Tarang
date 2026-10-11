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
