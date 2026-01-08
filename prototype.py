import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(
    page_title="NBA Player Prop Dashboard",
    layout="wide"
)

st.title("NBA Player Prop Dashboard")
st.caption("Prototype — single-game decision support")

st.info("Data loaded successfully. UI scaffolding in progress.")

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

    pbs = pbs[["gameId", "teamTricode", "firstName", "familyName", "points"]]

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

def plot_player_scoring(player_id, prop_line, pbs, tbs, daily_ranks, teammate_ids=None):

    # =========================================================
    # 1) Prepare player plotting dataframe
    # =========================================================

    plot_df = pbs[pbs["personId"] == player_id]

    plot_df = (
        plot_df
        .sort_values(["game_date", "game_id"])
        .reset_index(drop=True)
    )

    plot_df["game_number"] = np.arange(1, len(plot_df) + 1)
    x = np.arange(len(plot_df))

    # =========================================================
    # 2) Build opponent lookup from TEAM box scores
    # =========================================================

    opp_lookup = (
        tbs[["GAME_ID", "TEAM_ABBREVIATION"]]
        .rename(columns={
            "GAME_ID": "game_id",
            "TEAM_ABBREVIATION": "team"
        })
    )

    opp_lookup = (
        opp_lookup
        .merge(
            opp_lookup,
            on="game_id",
            suffixes=("", "_opp")
        )
        .query("team != team_opp")
        [["game_id", "team", "team_opp"]]
        .drop_duplicates()
        .rename(columns={"team_opp": "OPP_TEAM"})
    )

    team = plot_df["teamTricode"][0]

    plot_df = plot_df.merge(
        opp_lookup[opp_lookup["team"] == team][["game_id", "OPP_TEAM"]],
        on="game_id",
        how="left",
        validate="one_to_one"
    )

    # =========================================================
    # 3) AS-OF MERGE opponent defensive rank
    # =========================================================

    daily_ranks = daily_ranks.copy()

    daily_ranks = daily_ranks.rename(
        columns={"TEAM_ABBREVIATION": "opp_team"}
    )

    plot_df = plot_df.sort_values("game_date")
    daily_ranks = daily_ranks.sort_values("as_of_date")

    plot_df = pd.merge_asof(
        plot_df,
        daily_ranks,
        left_on="game_date",
        right_on="as_of_date",
        by="opp_team",
        direction="backward"
    )

    plot_df = plot_df.rename(columns={"def_rank": "opp_def_rank"})

    # =========================================================
    # 4) Bar colors (prop logic)
    # =========================================================

    bar_colors = np.where(
        plot_df["points"] > prop_line,
        "tab:green",
        "tab:red"
    )

    # =========================================================
    # 5) Plot
    # =========================================================

    fig, ax = plt.subplots(figsize=(15, 6))

    ax.bar(
        x,
        plot_df["points"],
        color=bar_colors,
        alpha=0.75,
        label="Game Points"
    )

    ax.plot(
        x,
        plot_df["r10_avg_ppg"],
        linestyle=":",
        linewidth=3,
        label="Rolling 10 Avg PPG"
    )

    ax.plot(
        x,
        plot_df["szn_avg_ppg"],
        linestyle="--",
        linewidth=1.8,
        alpha=0.7,
        label="Season Avg PPG"
    )

    ax.axhline(
        prop_line,
        linestyle=":",
        linewidth=2,
        color="black",
        alpha=0.8,
        label=f"Prop Line ({prop_line})"
    )

    # =========================================================
    # 6) Low minutes marker (≤30)
    # =========================================================

    def minutes_to_float(min_str):
        if pd.isna(min_str):
            return np.nan
        m, s = min_str.split(":")
        return int(m) + int(s) / 60

    plot_df["minutes_float"] = plot_df["minutes"].apply(minutes_to_float)
    low_min_mask = plot_df["minutes_float"] <= 30

    ax.scatter(
        x[low_min_mask],
        plot_df.loc[low_min_mask, "points"] + 1,
        marker="x",
        color="black",
        s=60,
        linewidths=2,
        label="≤30 Minutes"
    )

    # =========================================================
    # 7) Teammate absence markers (0–2 teammates)
    # =========================================================

    pbs_check = pbs.copy()
    pbs_check["familyName"] = pbs_check["familyName"].str.lower()
    pbs_check["firstName"] = pbs_check["firstName"].str.lower()

    player_game_ids = set(plot_df["game_id"])

    # Visual config (cycled if 2 teammates)
    markers = ["^", "s"]
    colors = ["tab:blue", "tab:purple"]
    y_offsets = [2.0, 3.2]

    for i, teammate_id in enumerate(teammate_ids):
        teammate_games = set(
            pbs_check[
                (pbs_check["personId"] == teammate_id) &
                (pbs_check["game_id"].isin(player_game_ids))
            ]["game_id"]
        )

        out_col = f"teammate_{i}_out"
        plot_df[out_col] = ~plot_df["game_id"].isin(teammate_games)

        # Get teammate name once (for legend)
        name_row = (
            pbs_check[pbs_check["personId"] == teammate_id]
            [["firstName", "familyName"]]
            .drop_duplicates()
            .iloc[0]
        )
        teammate_name = f"{name_row['firstName'].title()} {name_row['familyName'].title()}"

        ax.scatter(
            x[plot_df[out_col]],
            plot_df.loc[plot_df[out_col], "points"] + y_offsets[i],
            marker=markers[i],
            color=colors[i],
            s=80 if i == 0 else 70,
            label=f"{teammate_name} OUT"
        )

    # =========================================================
    # 8) Opponent team + defensive rank labels (BOTTOM)
    # =========================================================

    for i, row in plot_df.iterrows():
        if not pd.isna(row["opp_def_rank"]):
            ax.text(
                i,
                10.2,
                f'{row["OPP_TEAM"]}',
                ha="center",
                va="bottom",
                fontsize=8,
                alpha=0.85
            )
            ax.text(
                i,
                11.2,
                f'#{int(row["opp_def_rank"])}',
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
                alpha=0.9
            )

    # =========================================================
    # 9) Formatting
    # =========================================================

    ax.set_ylim(10, plot_df["points"].max() + 5)
    ax.set_ylabel("Points")
    ax.set_xlabel("Game Number")
    ax.set_title("Luka Dončić — Scoring Outcomes vs Baselines")

    ax.set_xticks(x[::5])
    ax.set_xticklabels(plot_df["game_number"][::5])

    ax.grid(axis="y", alpha=0.25)
    ax.legend(
        fontsize=9,
        frameon=False,
        labelspacing=0.4,
        handlelength=1.5,
        handletextpad=0.6
    )

    plt.tight_layout()
    plt.show()

def plot_opp_def(team_id, tbs, daily_ranks):

    # =========================================================
    # 1) Prep team box scores
    # =========================================================

    tbs_plot = tbs.copy()

    team_games = (
        tbs_plot[tbs_plot["TEAM_ID"] == team_id]
        .sort_values("GAME_DATE")
        .reset_index(drop=True)
    )

    # =========================================================
    # 2) Season-to-date avg points allowed (NO leakage)
    # =========================================================

    team_games["szn_avg_pts_allowed"] = (
        team_games["PTS_ALLOWED"]
        .shift(1)                    # only prior games
        .expanding()
        .mean()
    )

    # Rolling 10-game avg points allowed (prior games only)
    team_games["r10_avg_pts_allowed"] = (
        team_games["PTS_ALLOWED"]
        .shift(1)
        .rolling(10, min_periods=1)
        .mean()
    )

    # League-wide avg points allowed
    league_avg_pts_allowed = (
        tbs[tbs["GAME_DATE"] <= team_games["GAME_DATE"].max()]
        ["PTS_ALLOWED"]
        .mean()
    )
    
    # =========================================================
    # 3) Attach opponent OFFENSIVE rank (as of game date)
    # =========================================================

    daily_ranks_plot = daily_ranks.copy()

    team_games = team_games.sort_values("GAME_DATE")
    daily_ranks_plot = daily_ranks_plot.sort_values("game_date")

    team_games = pd.merge_asof(
        team_games,
        daily_ranks_plot,
        left_on="GAME_DATE",
        right_on="game_date_dt",
        left_by="OPP_TEAM",
        right_by="TEAM_ABBREVIATION",
        direction="backward"
    )

    # =========================================================
    # 4) Plot
    # =========================================================

    x = np.arange(len(team_games))

    fig, ax = plt.subplots(figsize=(15, 6))

    # -----------------------------
    # Bars: points allowed
    # -----------------------------
    ax.bar(
        x,
        team_games["PTS_ALLOWED"],
        width=0.7,
        color="blue",
        alpha=0.45,
        label="Points Allowed"
    )


    # -----------------------------
    # Season avg line
    # -----------------------------
    ax.plot(
        x,
        team_games["szn_avg_pts_allowed"],
        linestyle="--",
        linewidth=2.5,
        color="red",
        alpha=0.85,
        label="Season Avg Pts Allowed"
    )


    # Rolling 10 avg line
    ax.plot(
        x,
        team_games["r10_avg_pts_allowed"],
        linestyle="--",
        linewidth=2.5,
        color="tab:green",
        alpha=0.9,
        label="Rolling 10 Avg Pts Allowed"
    )

    # League-wide avg line
    ax.axhline(
        league_avg_pts_allowed,
        linestyle="--",
        linewidth=2.5,
        color="black",
        alpha=0.8,
        label="League Avg Pts Allowed"
    )

    # -----------------------------
    # Bottom labels: opponent + off rank
    # -----------------------------
    for i, row in team_games.iterrows():
        if pd.notna(row["off_rank"]):
            ax.text(
                i,
                97,
                f'{row["OPP_TEAM"]}\n#{int(row["off_rank"])}',
                ha="center",
                va="bottom",
                fontsize=8,
                color="black",
                alpha=0.85
            )

    # =========================================================
    # 5) Formatting
    # =========================================================
    ax.set_title("NOP — Points Allowed by Game (Opponent Offensive Rank)")
    ax.set_ylabel("Points Allowed")
    ax.set_xlabel("Game Number")

    # ax.set_ylim(80, nop_games["PTS_ALLOWED"].max() + 5)
    ax.set_ylim(95, 145)

    # ax.set_xticks(x[::5])
    # ax.set_xticklabels(x[::5] + 1)

    ax.grid(axis="y", alpha=0.25)
    ax.legend(
        loc="upper left",
        frameon=False,
        fontsize=10
    )

    plt.tight_layout()
    plt.show()

def plot_team_off(team_id, tbs, daily_ranks):

    # =========================================================
    # 1) Prep team box scores
    # =========================================================

    tbs_plot = tbs.copy()

    team_games = (
        tbs_plot[tbs_plot["TEAM_ID"] == team_id]
        .sort_values("GAME_DATE")
        .reset_index(drop=True)
    )

    # =========================================================
    # 2) Season-to-date avg points scored (NO leakage)
    # =========================================================

    team_games["szn_avg_pts_scored"] = (
        team_games["PTS"]
        .shift(1)
        .expanding()
        .mean()
    )

    # Rolling 10-game avg points scored (prior games only)
    team_games["r10_avg_pts_scored"] = (
        team_games["PTS"]
        .shift(1)
        .rolling(10, min_periods=1)
        .mean()
    )

    # League-wide avg team points scored (as-of cutoff)
    league_avg_pts_scored = (
        tbs[tbs["GAME_DATE"] <= team_games["GAME_DATE"].max()]
        ["PTS"]
        .mean()
    )

    # =========================================================
    # 3) Attach opponent DEFENSIVE rank (as of game date)
    # =========================================================

    daily_ranks_plot = daily_ranks.copy()

    team_games = team_games.sort_values("GAME_DATE")
    daily_ranks_plot = daily_ranks_plot.sort_values("game_date")

    team_games = pd.merge_asof(
        team_games,
        daily_ranks_plot,
        left_on="GAME_DATE_DT",
        right_on="game_date_dt",
        left_by="OPP_TEAM",
        right_by="TEAM_ABBREVIATION",
        direction="backward"
    )

    # =========================================================
    # 4) Plot
    # =========================================================

    x = np.arange(len(team_games))

    fig, ax = plt.subplots(figsize=(15, 6))

    # -----------------------------
    # Bars: points scored
    # -----------------------------
    ax.bar(
        x,
        team_games["PTS"],
        width=0.7,
        color="tab:green",
        alpha=0.45,
        label="Points Scored"
    )

    # -----------------------------
    # Season avg line
    # -----------------------------
    ax.plot(
        x,
        team_games["szn_avg_pts_scored"],
        linestyle="--",
        linewidth=2.5,
        color="red",
        alpha=0.85,
        label="Season Avg Pts Scored"
    )

    # Rolling 10 avg line
    ax.plot(
        x,
        team_games["r10_avg_pts_scored"],
        linestyle="--",
        linewidth=2.5,
        color="tab:blue",
        alpha=0.9,
        label="Rolling 10 Avg Pts Scored"
    )

    # League-wide avg line
    ax.axhline(
        league_avg_pts_scored,
        linestyle="--",
        linewidth=2.5,
        color="black",
        alpha=0.8,
        label="League Avg Pts Scored"
    )

    # -----------------------------
    # Bottom labels: opponent + DEF rank
    # -----------------------------
    for i, row in team_games.iterrows():
        if pd.notna(row["def_rank"]):
            ax.text(
                i,
                team_games["PTS"].min() - 6,
                f'{row["OPP_TEAM"]}\n#{int(row["def_rank"])}',
                ha="center",
                va="bottom",
                fontsize=8,
                color="black",
                alpha=0.85
            )

    # =========================================================
    # 5) Formatting
    # =========================================================
    ax.set_title("LAL — Points Scored by Game (Opponent Defensive Rank)")
    ax.set_ylabel("Points Scored")
    ax.set_xlabel("Game Number")

    ax.set_ylim(
        team_games["PTS"].min() - 10,
        team_games["PTS"].max() + 5
    )

    ax.grid(axis="y", alpha=0.25)
    ax.legend(
        loc="upper left",
        frameon=False,
        fontsize=10
    )

    plt.tight_layout()
    plt.show()

