"""
DIMER // TERMINAL — FastAPI backend
Wraps existing db_queries logic, exposes REST endpoints, serves frontend.
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# ---------------------------------------------------------------------------
# Secrets (read from .streamlit/secrets.toml or env)
# ---------------------------------------------------------------------------

def _load_secrets() -> dict[str, str]:
    path = Path(__file__).parent / ".streamlit" / "secrets.toml"
    secrets: dict[str, str] = {}

    # Local dev: load .streamlit/secrets.toml if it exists.
    # Render/prod: this file won't exist, so skip it and use env vars below.
    if path.exists():
        try:
            import tomllib  # py311+
            with open(path, "rb") as f:
                secrets = tomllib.load(f)
        except ModuleNotFoundError:
            # Minimal TOML key = "value" parser for older Python
            for line in path.read_text().splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    secrets[k.strip()] = v.strip().strip('"').strip("'")

    # Env-var overrides / production secrets
    for key in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"):
        if os.getenv(key):
            secrets[key] = os.environ[key]

    return secrets


SECRETS = _load_secrets()

# ---------------------------------------------------------------------------
# DB engine
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_engine():
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=SECRETS["DB_USER"],
        password=SECRETS["DB_PASSWORD"],
        host=SECRETS["DB_HOST"],
        port=int(SECRETS.get("DB_PORT", 5432)),
        database=SECRETS.get("DB_NAME", "postgres"),
    )
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args={"sslmode": "require"},
    )


# ---------------------------------------------------------------------------
# Team metadata (conference / division)
# ---------------------------------------------------------------------------

TEAM_META: dict[str, dict] = {
    "BOS": {"city": "Boston",          "name": "Celtics",       "conf": "East", "div": "Atlantic"},
    "BKN": {"city": "Brooklyn",        "name": "Nets",          "conf": "East", "div": "Atlantic"},
    "NYK": {"city": "New York",        "name": "Knicks",        "conf": "East", "div": "Atlantic"},
    "PHI": {"city": "Philadelphia",    "name": "76ers",         "conf": "East", "div": "Atlantic"},
    "TOR": {"city": "Toronto",         "name": "Raptors",       "conf": "East", "div": "Atlantic"},
    "CHI": {"city": "Chicago",         "name": "Bulls",         "conf": "East", "div": "Central"},
    "CLE": {"city": "Cleveland",       "name": "Cavaliers",     "conf": "East", "div": "Central"},
    "DET": {"city": "Detroit",         "name": "Pistons",       "conf": "East", "div": "Central"},
    "IND": {"city": "Indiana",         "name": "Pacers",        "conf": "East", "div": "Central"},
    "MIL": {"city": "Milwaukee",       "name": "Bucks",         "conf": "East", "div": "Central"},
    "ATL": {"city": "Atlanta",         "name": "Hawks",         "conf": "East", "div": "Southeast"},
    "CHA": {"city": "Charlotte",       "name": "Hornets",       "conf": "East", "div": "Southeast"},
    "MIA": {"city": "Miami",           "name": "Heat",          "conf": "East", "div": "Southeast"},
    "ORL": {"city": "Orlando",         "name": "Magic",         "conf": "East", "div": "Southeast"},
    "WAS": {"city": "Washington",      "name": "Wizards",       "conf": "East", "div": "Southeast"},
    "DEN": {"city": "Denver",          "name": "Nuggets",       "conf": "West", "div": "Northwest"},
    "MIN": {"city": "Minnesota",       "name": "Timberwolves",  "conf": "West", "div": "Northwest"},
    "OKC": {"city": "Oklahoma City",   "name": "Thunder",       "conf": "West", "div": "Northwest"},
    "POR": {"city": "Portland",        "name": "Trail Blazers", "conf": "West", "div": "Northwest"},
    "UTA": {"city": "Utah",            "name": "Jazz",          "conf": "West", "div": "Northwest"},
    "GSW": {"city": "Golden State",    "name": "Warriors",      "conf": "West", "div": "Pacific"},
    "LAC": {"city": "LA",              "name": "Clippers",      "conf": "West", "div": "Pacific"},
    "LAL": {"city": "Los Angeles",     "name": "Lakers",        "conf": "West", "div": "Pacific"},
    "PHX": {"city": "Phoenix",         "name": "Suns",          "conf": "West", "div": "Pacific"},
    "SAC": {"city": "Sacramento",      "name": "Kings",         "conf": "West", "div": "Pacific"},
    "DAL": {"city": "Dallas",          "name": "Mavericks",     "conf": "West", "div": "Southwest"},
    "HOU": {"city": "Houston",         "name": "Rockets",       "conf": "West", "div": "Southwest"},
    "MEM": {"city": "Memphis",         "name": "Grizzlies",     "conf": "West", "div": "Southwest"},
    "NOP": {"city": "New Orleans",     "name": "Pelicans",      "conf": "West", "div": "Southwest"},
    "SAS": {"city": "San Antonio",     "name": "Spurs",         "conf": "West", "div": "Southwest"},
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(v, default: float = 0.0) -> float:
    try:
        return float(v) if v is not None and str(v) != "nan" else default
    except (TypeError, ValueError):
        return default


def _minutes_to_float(min_str) -> float:
    if pd.isna(min_str) or min_str is None or str(min_str) == "":
        return 0.0
    try:
        parts = str(min_str).split(":")
        return int(parts[0]) + int(parts[1]) / 60
    except Exception:
        return 0.0


def _parse_matchup(matchup: str, team: str) -> tuple[str, str]:
    """Return (opponent_tricode, 'vs' | '@')."""
    if not matchup or pd.isna(matchup):
        return "???", "vs"
    matchup = str(matchup).strip()
    if " vs. " in matchup:
        parts = matchup.split(" vs. ")
        if parts[0].strip() == team:
            opp = parts[1].strip()[:3]
        else:
            opp = parts[0].strip()[:3]
        return opp, "vs"
    elif " @ " in matchup:
        parts = matchup.split(" @ ")
        if parts[0].strip() == team:
            opp = parts[1].strip()[:3]
        else:
            opp = parts[0].strip()[:3]
        return opp, "@"
    return matchup[-3:], "vs"


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="DIMER // TERMINAL API", version="0.5")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/teams")
def list_teams() -> list[dict]:
    """All teams that have data in the DB, enriched with conf/div metadata."""
    engine = get_engine()
    q = text("""
        SELECT DISTINCT team_abbreviation
        FROM raw.league_game_log
        WHERE team_abbreviation IS NOT NULL
        ORDER BY team_abbreviation
    """)
    df = pd.read_sql(q, engine)
    active_tris = set(df["team_abbreviation"].tolist())

    teams = []
    for tri, meta in TEAM_META.items():
        teams.append({
            "tri": tri,
            "city": meta["city"],
            "name": meta["name"],
            "conf": meta["conf"],
            "div": meta["div"],
            "hasData": tri in active_tris,
        })
    return teams


@app.get("/api/teams/{abbrev}/players")
def team_players(abbrev: str) -> list[dict]:
    """Roster for a team, ordered by season-average PPG descending."""
    engine = get_engine()
    q = text("""
        SELECT
            person_id,
            first_name,
            family_name,
            AVG(points)             AS avg_pts,
            AVG(assists)            AS avg_ast,
            AVG(rebounds_total)     AS avg_reb,
            AVG(three_pointers_made)AS avg_tpm,
            AVG(steals)             AS avg_stl,
            AVG(blocks)             AS avg_blk,
            AVG(turnovers)          AS avg_tov,
            AVG(rebounds_offensive) AS avg_oreb,
            AVG(rebounds_defensive) AS avg_dreb,
            COUNT(*)                AS games_played
        FROM raw.box_score_traditional_v3
        WHERE team_tricode = :abbrev
          AND person_id IS NOT NULL
          AND points IS NOT NULL
        GROUP BY person_id, first_name, family_name
        ORDER BY avg_pts DESC
    """)
    df = pd.read_sql(q, engine, params={"abbrev": abbrev.upper()})
    if df.empty:
        return []

    # Compute minutes separately (stored as MM:SS)
    mq = text("""
        SELECT
            person_id,
            AVG(
                CASE
                    WHEN minutes ~ '^[0-9]+:[0-9]+$'
                    THEN SPLIT_PART(minutes, ':', 1)::float
                       + SPLIT_PART(minutes, ':', 2)::float / 60
                    ELSE NULL
                END
            ) AS avg_min
        FROM raw.box_score_traditional_v3
        WHERE team_tricode = :abbrev
          AND person_id IS NOT NULL
          AND minutes IS NOT NULL
        GROUP BY person_id
    """)
    mdf = pd.read_sql(mq, engine, params={"abbrev": abbrev.upper()})
    min_map: dict[int, float] = {}
    for _, row in mdf.iterrows():
        if pd.notna(row["avg_min"]):
            min_map[int(row["person_id"])] = round(_safe_float(row["avg_min"]), 1)

    players = []
    for _, row in df.iterrows():
        pid = int(row["person_id"])
        first = str(row["first_name"] or "")
        last  = str(row["family_name"] or "")
        initials = (first[0].upper() if first else "") + (last[0].upper() if last else "")
        pts  = round(_safe_float(row["avg_pts"]),  1)
        ast  = round(_safe_float(row["avg_ast"]),  1)
        reb  = round(_safe_float(row["avg_reb"]),  1)
        tpm  = round(_safe_float(row["avg_tpm"]),  1)
        stl  = round(_safe_float(row["avg_stl"]),  1)
        blk  = round(_safe_float(row["avg_blk"]),  1)
        tov  = round(_safe_float(row["avg_tov"]),  1)
        oreb = round(_safe_float(row["avg_oreb"]), 1)
        dreb = round(_safe_float(row["avg_dreb"]), 1)
        avg_min = min_map.get(pid, 0.0)
        players.append({
            "id":        str(pid),
            "person_id": pid,
            "first":     first,
            "last":      last,
            "initials":  initials,
            "team":      abbrev.upper(),
            "pos":       "—",
            "number":    "—",
            "height":    "—",
            "weight":    0,
            "age":       0,
            "games":     int(row["games_played"]),
            "stats": {
                "pts":  pts,
                "ast":  ast,
                "reb":  reb,
                "tpm":  tpm,
                "stl":  stl,
                "blk":  blk,
                "tov":  tov,
                "oreb": oreb,
                "dreb": dreb,
                "pa":   round(pts + ast, 1),
                "pr":   round(pts + reb, 1),
                "ra":   round(reb + ast, 1),
                "pra":  round(pts + reb + ast, 1),
                "min":  avg_min,
            },
        })
    return players


@app.get("/api/players/{person_id}/games")
def player_games(person_id: int) -> list[dict]:
    """Full game log for a player, newest first."""
    engine = get_engine()
    q = text("""
        SELECT DISTINCT ON (bs.game_id)
            bs.game_id,
            bs.team_tricode,
            bs.minutes,
            bs.points,
            bs.rebounds_offensive,
            bs.rebounds_defensive,
            bs.rebounds_total,
            bs.assists,
            bs.three_pointers_made,
            bs.steals,
            bs.blocks,
            bs.turnovers,
            lgl.game_date,
            lgl.matchup,
            lgl.wl
        FROM raw.box_score_traditional_v3 bs
        INNER JOIN raw.league_game_log lgl
            ON bs.game_id = lgl.game_id
           AND bs.team_tricode = lgl.team_abbreviation
        WHERE bs.person_id = :pid
          AND bs.person_id IS NOT NULL
        ORDER BY bs.game_id, lgl.game_date DESC
    """)
    df = pd.read_sql(q, engine, params={"pid": person_id})
    if df.empty:
        return []

    df["game_date"] = pd.to_datetime(df["game_date"])
    df = df.sort_values("game_date", ascending=False).reset_index(drop=True)

    games: list[dict] = []
    for _, row in df.iterrows():
        pts  = round(_safe_float(row["points"]))
        ast  = round(_safe_float(row["assists"]))
        reb  = round(_safe_float(row["rebounds_total"]))
        oreb = round(_safe_float(row["rebounds_offensive"]))
        dreb = round(_safe_float(row["rebounds_defensive"]))
        tpm  = round(_safe_float(row["three_pointers_made"]))
        stl  = round(_safe_float(row["steals"]))
        blk  = round(_safe_float(row["blocks"]))
        tov  = round(_safe_float(row["turnovers"]))
        mins = round(_minutes_to_float(row["minutes"]))

        team  = str(row["team_tricode"] or "")
        opp, ha = _parse_matchup(row["matchup"], team)
        won  = str(row["wl"]).upper() == "W" if pd.notna(row["wl"]) else False

        gd = row["game_date"]
        date_str = f"{gd.month}/{str(gd.day).zfill(2)}"

        games.append({
            "game_id": str(row["game_id"]),
            "date":    date_str,
            "opp":     opp,
            "ha":      ha,
            "won":     won,
            "result":  "W" if won else "L",
            "pts":     pts,
            "ast":     ast,
            "reb":     reb,
            "oreb":    oreb,
            "dreb":    dreb,
            "tpm":     tpm,
            "stl":     stl,
            "blk":     blk,
            "tov":     tov,
            "min":     mins,
            "q1pts":   0,
            "pa":      pts + ast,
            "pr":      pts + reb,
            "ra":      reb + ast,
            "pra":     pts + reb + ast,
        })
    return games


# ---------------------------------------------------------------------------
# Serve frontend (must come LAST so API routes take priority)
# ---------------------------------------------------------------------------

_frontend_dir = Path(__file__).parent / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
