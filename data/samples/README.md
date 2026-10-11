# Sample upload (INVENTED VALUES)

`new_readings_sample.csv` is a **demonstration file with made-up numbers**.
It is not a real MPPCB reading and must not be quoted as one. It shows the
"week after" use: an officer uploads new Durga 2026 readings in the same
columns as `data/bhopal_ghats_2023_2025.csv`, and the ranking updates.

It contains Durga 2026 pre/during readings for Malikhedi kund and Arch Bridge
(which has no past readings), plus one "not sampled" and one value for
Bairagarh. Uploaded rows show as "user-supplied" in the evidence, with no
report page.

Required columns: `site, year, festival, phase, parameter, value` (and
`flag` when there is no value). The other columns may be left blank. Leave
`source_page` blank.
