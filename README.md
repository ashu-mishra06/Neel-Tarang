# Visarjan Ghat Watch

Shows which Bhopal immersion ghats need attention before Durga visarjan
(20 Oct 2026), and **why**: was the water already poor before immersion, or
did it get worse during immersion? Every number links back to the MPPCB report
page it came from.

- **Track:** 2. Claude Impact Lab x Cerebras Cafe Compute, Bhopal, 11 Oct 2026
- **Team:** _TODO: team name_
- **Members:** _TODO_
- **The one user:** a Bhopal Municipal Corporation (BMC) officer planning Durga
  visarjan.

> Honesty note: the persona and needs come from the problem statement, not from
> interviews.

## How to run (5 steps)

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

No API key and no network needed.

## What works / what doesn't

_TODO (Level 8)._

## Data

- `data/`: the organisers' files, unchanged.
- `data/context/designated_ghats_2026.csv`: the 2026 Ganesh designated ghats as
  reported by Free Press Journal on 22 Sep 2026 (_TODO: add article URL_).
- Statewide file: used only as a less-checked context benchmark. It never
  affects the ranking.

## Not included

_TODO (Level 7/8)._

## Licence

MIT. See `LICENSE`.
