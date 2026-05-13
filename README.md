# Dimer Viz

A personal NBA analytics and prop research platform for sharp and casual sports bettors, and NBA fans who want to go deeper than box scores.

## What it does

Dimer Viz lets you select a player, opponent, and a prop line, then surfaces historical performance data and contextual breakdowns to inform your research. The current version focuses on points props with hit-rate analysis across multiple filtering dimensions.

**Current features:**
- Per-game scoring chart with prop line overlay and teammate absence markers
- Hit-rate summary table sliced by home/away, win/loss, defensive tier, and team scoring thresholds
- Team matchup comparison charts (points scored vs. points allowed by condition)
- Teammate injury filtering — isolate games where selected teammates were absent
- Supabase PostgreSQL backend with SQLAlchemy data access layer

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Database | Supabase (PostgreSQL) |
| Data access | SQLAlchemy + psycopg2 |
| Visualization | Matplotlib |
| Language | Python 3.11 |

## Project structure

```
dimer-viz/
├── app.py                  # Streamlit entrypoint
├── config.py               # Shared constants (team names, thresholds, defaults)
├── db_queries.py           # Database queries and data processing
├── tables.py               # Hit-rate table computation
├── export.py               # CSV export utility
├── plots/
│   ├── player.py           # Player scoring visualizations
│   └── team.py             # Team matchup visualizations
└── _archive/               # Archived pre-consolidation files
```

## Setup

1. Clone the repo
2. Create and activate a virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Add your Supabase credentials to `.streamlit/secrets.toml`:
```toml
DB_HOST = "your-host"
DB_PORT = "6543"
DB_NAME = "postgres"
DB_USER = "your-user"
DB_PASSWORD = "your-password"
```
5. Run: `streamlit run app.py`

> `.streamlit/secrets.toml` is gitignored. Never commit credentials.

## Status

Active development. See the [PRD](./PRD.md) for planned features and roadmap.