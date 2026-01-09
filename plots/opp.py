import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def plot_team_points_allowed(team_abbreviation, tbs, daily_ranks):
    """
    Plot a team's points allowed per game with season averages and opponent offensive ranks.
    
    Parameters:
    -----------
    team_abbreviation : str
        Team abbreviation (e.g., "NOP", "LAL")
    tbs : pd.DataFrame
        Team box scores dataframe
    daily_ranks : pd.DataFrame
        Daily team rankings dataframe with offensive ranks
    """
    
    # =========================================================
    # 1) Prep team box scores
    # =========================================================
    
    tbs_plot = tbs.copy()
    tbs_plot["GAME_DATE_DT"] = pd.to_datetime(tbs_plot["GAME_DATE"])
    
    team_games = (
        tbs_plot[tbs_plot["TEAM_ABBREVIATION"] == team_abbreviation]
        .sort_values("GAME_DATE_DT")
        .reset_index(drop=True)
    )
    
    # Opponent abbreviation
    team_games["OPP_TEAM"] = team_games["MATCHUP"].str[-3:]
    
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
    daily_ranks_plot["game_date_dt"] = pd.to_datetime(daily_ranks_plot["game_date"])
    
    team_games = team_games.sort_values("GAME_DATE_DT")
    daily_ranks_plot = daily_ranks_plot.sort_values("game_date_dt")
    
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
    
    # -----------------------------
    # Formatting
    # -----------------------------
    ax.set_title(f"{team_abbreviation} — Points Allowed by Game (Opponent Offensive Rank)")
    ax.set_ylabel("Points Allowed")
    ax.set_xlabel("Game Number")
    
    # ax.set_ylim(80, team_games["PTS_ALLOWED"].max() + 5)
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
    
    return fig, ax

