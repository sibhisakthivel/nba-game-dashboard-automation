import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Add a function to update CSVs with recent games

@st.cache_data
def load_process_pbs():
    # Load in player data
    pbs = pd.read_csv("player_boxscores_2025_26.csv")

    # Convert game_date to datetime type
    pbs["game_date"] = pd.to_datetime(pbs["game_date"])

    # Convert minutes to float 
    def minutes_to_float(min_str):
        if pd.isna(min_str):
            return None
        m, s = min_str.split(":")
        return int(m) + int(s) / 60

    pbs["minutes"] = pbs["minutes"].apply(minutes_to_float)

    # Sort for correct window behavior before calculating averages
    pbs = (
        pbs
        .sort_values(["personId", "game_date"])
        .reset_index(drop=True)
    )

    # Compute season and rolling 10-game point averages
    pbs["szn_avg_ppg"] = (
        pbs
        .groupby("personId")["points"]
        .transform(lambda s: s.shift(1).expanding().mean())
    )

    pbs["r10_avg_ppg"] = (
        pbs
        .groupby("personId")["points"]
        .transform(lambda s: s.shift(1).rolling(10, min_periods=1).mean())
    )

    # pbs = pbs[["gameId", "game_date", "teamTricode", "personId", "firstName", "familyName", "points", "szn_avg_ppg", "r10_avg_ppg"]]

    return pbs

@st.cache_data
def load_process_tbs():
    # Load in team data
    tbs = pd.read_csv("league_gamelog_2025_26.csv")

    tbs["GAME_DATE"] = pd.to_datetime(tbs["GAME_DATE"])

    opp = (
        tbs[["GAME_ID", "TEAM_ABBREVIATION", "PTS"]]
        .rename(columns={
            "TEAM_ABBREVIATION": "OPP_TEAM",
            "PTS": "OPP_PTS"
        })
    )

    merged = tbs.merge(
        opp,
        on="GAME_ID",
        how="left",
        validate="many_to_many"
    )

    merged = merged[merged["TEAM_ABBREVIATION"] != merged["OPP_TEAM"]]

    tbs = (
        merged
        .rename(columns={"OPP_PTS": "PTS_ALLOWED"})
    )

    tbs = tbs[["GAME_ID", "TEAM_ABBREVIATION", "GAME_DATE", "PTS", "MATCHUP", "OPP_TEAM", "PTS_ALLOWED", "WL"]]

    return tbs

@st.cache_data
def build_ranks(tbs):
    # Get all unique game dates in order
    season_start = tbs["GAME_DATE"].min()
    season_end = tbs["GAME_DATE"].max() + pd.Timedelta(days=1)

    game_dates = pd.date_range(
        start=season_start,
        end=season_end,
        freq="D"
    )

    daily_ranks = []

    for game_date in game_dates:
        prior_games = tbs[tbs["GAME_DATE"] < game_date]

        # Skip dates before anyone has played
        if prior_games.empty:
            continue

        ranks = (
            prior_games
            .groupby("TEAM_ABBREVIATION", as_index=False)
            .agg(
                games_played=("GAME_ID", "count"),
                avg_pts=("PTS", "mean"),
                avg_pts_allowed=("PTS_ALLOWED", "mean"),
            )
        )

        # Ranks (league context as of this date)
        ranks["off_rank"] = ranks["avg_pts"].rank(
            method="first", ascending=False
        )
        ranks["def_rank"] = ranks["avg_pts_allowed"].rank(
            method="first", ascending=True
        )

        ranks["game_date"] = game_date
        daily_ranks.append(ranks)

    daily_ranks = (
        pd.concat(daily_ranks, ignore_index=True)
        .sort_values(["game_date", "def_rank"])
    )

    return daily_ranks
