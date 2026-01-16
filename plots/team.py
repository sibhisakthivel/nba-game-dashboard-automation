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

def plot_team_points_scored(team_abbreviation, tbs, daily_ranks):
    
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
    # 2) Season-to-date avg points (NO leakage)
    # =========================================================
    
    team_games["szn_avg_ppg"] = (
        team_games["PTS"]
        .shift(1)                    # only prior games
        .expanding()
        .mean()
    )
    
    # Rolling 10-game avg points (prior games only)
    team_games["r10_avg_ppg"] = (
        team_games["PTS"]
        .shift(1)
        .rolling(10, min_periods=1)
        .mean()
    )
    
    # League-wide avg points 
    league_avg_ppg = (
        tbs[tbs["GAME_DATE"] <= team_games["GAME_DATE"].max()]
        ["PTS"]
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
        team_games["PTS"],
        width=0.7,
        color="green",
        alpha=0.45,
        label="Points"
    )
    
    
    # -----------------------------
    # Season avg line
    # -----------------------------
    ax.plot(
        x,
        team_games["szn_avg_ppg"],
        linestyle="--",
        linewidth=2.5,
        color="red",
        alpha=0.85,
        label="Season Avg PPG"
    )
    
    
    # Rolling 10 avg line
    ax.plot(
        x,
        team_games["r10_avg_ppg"],
        linestyle="--",
        linewidth=2.5,
        color="tab:blue",
        alpha=0.9,
        label="Rolling 10 Avg PPG"
    )
    
    # League-wide avg line
    ax.axhline(
        league_avg_ppg,
        linestyle="--",
        linewidth=2.5,
        color="black",
        alpha=0.8,
        label="League Avg PPG"
    )
    
    # -----------------------------
    # Bottom labels: opponent + off rank
    # -----------------------------
    for i, row in team_games.iterrows():
        if pd.notna(row["def_rank"]):
            ax.text(
                i,
                97,
                f'{row["OPP_TEAM"]}\n#{int(row["def_rank"])}',
                ha="center",
                va="bottom",
                fontsize=8,
                color="black",
                alpha=0.85
            )
    
    # -----------------------------
    # Formatting
    # -----------------------------
    ax.set_title(f"{team_abbreviation} — Points Scored by Game (Opponent Defensive Rank)")
    ax.set_ylabel("Points")
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
    plt.show()
    
    return fig, ax

def build_team_matchup_stats(off_team: str, def_team: str, home_team: str, away_team: str, tbs: pd.DataFrame, daily_ranks: pd.DataFrame) -> pd.DataFrame:
    """
    Build a dataframe with team points scored and opponent points allowed across various conditions.
    
    Parameters:
    -----------
    off_team : str
        Offensive team abbreviation (e.g., "LAL")
    def_team : str
        Defensive team abbreviation (e.g., "NOP")
    home_team : str
        Home team abbreviation (e.g., "NOP")
    away_team : str
        Away team abbreviation (e.g., "LAL")
    tbs : pd.DataFrame
        Team box scores dataframe with columns: GAME_ID, TEAM_ABBREVIATION, GAME_DATE, PTS, PTS_ALLOWED, OPP_TEAM, WL, MATCHUP
    daily_ranks : pd.DataFrame
        Daily team rankings dataframe with columns: game_date, TEAM_ABBREVIATION, def_rank, off_rank, avg_pts_allowed
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with columns: condition, off_team_pts_scored, def_team_pts_allowed
    """
    # Helper function to determine defensive bucket
    def def_bucket(rank):
        """Determine defensive bucket from rank."""
        if pd.isna(rank):
            return None
        if rank <= 10:
            return "Top 10 Defense"
        elif rank <= 20:
            return "Middle 10 Defense"
        else:
            return "Bottom 10 Defense"
    
    # Helper function to determine offensive bucket
    def off_bucket(rank):
        """Determine offensive bucket from rank."""
        if pd.isna(rank):
            return None
        if rank <= 10:
            return "Top 10 Offense"
        elif rank <= 20:
            return "Middle 10 Offense"
        else:
            return "Bottom 10 Offense"
    
    # Get most recent defensive and offensive ranks for both teams
    latest_ranks = daily_ranks.sort_values("game_date").groupby("TEAM_ABBREVIATION").tail(1)
    off_def_rank = latest_ranks[latest_ranks["TEAM_ABBREVIATION"] == off_team]["def_rank"].iloc[0] if len(latest_ranks[latest_ranks["TEAM_ABBREVIATION"] == off_team]) > 0 else None
    off_off_rank = latest_ranks[latest_ranks["TEAM_ABBREVIATION"] == off_team]["off_rank"].iloc[0] if len(latest_ranks[latest_ranks["TEAM_ABBREVIATION"] == off_team]) > 0 else None
    def_def_rank = latest_ranks[latest_ranks["TEAM_ABBREVIATION"] == def_team]["def_rank"].iloc[0] if len(latest_ranks[latest_ranks["TEAM_ABBREVIATION"] == def_team]) > 0 else None
    
    off_def_bucket = def_bucket(off_def_rank) if off_def_rank is not None else None
    off_off_bucket = off_bucket(off_off_rank) if off_off_rank is not None else None
    def_def_bucket = def_bucket(def_def_rank) if def_def_rank is not None else None
    
    # Prepare data
    tbs_copy = tbs.copy()
    tbs_copy["GAME_DATE"] = pd.to_datetime(tbs_copy["GAME_DATE"])
    
    # Get offensive team games
    off_games = tbs_copy[tbs_copy["TEAM_ABBREVIATION"] == off_team].copy()
    off_games["HOME_AWAY"] = off_games["MATCHUP"].apply(lambda x: "HOME" if "vs" in x else "AWAY")
    
    # Get defensive team games
    def_games = tbs_copy[tbs_copy["TEAM_ABBREVIATION"] == def_team].copy()
    def_games["HOME_AWAY"] = def_games["MATCHUP"].apply(lambda x: "HOME" if "vs" in x else "AWAY")
    
    # =========================================================
    # Build conditions dataframe
    # =========================================================
    
    conditions = []
    
    # 1) Simple season averages
    off_season_avg_pts = off_games["PTS"].mean()
    def_season_avg_pts_allowed = def_games["PTS_ALLOWED"].mean()
    conditions.append({
        "condition": "Season Averages",
        "off_team_pts_scored": off_season_avg_pts,
        "def_team_pts_allowed": def_season_avg_pts_allowed
    })
    
    # 2) Bucket averages
    # off_team result: stats against def_team's defensive bucket
    # def_team result: stats against off_team's offensive bucket
    
    if def_def_bucket is not None:
        # Prepare daily ranks for merge_asof
        daily_ranks_opp = daily_ranks.copy()
        daily_ranks_opp["game_date_dt"] = pd.to_datetime(daily_ranks_opp["game_date"])
        daily_ranks_opp = daily_ranks_opp.rename(columns={"TEAM_ABBREVIATION": "OPP_TEAM"})
        daily_ranks_opp = daily_ranks_opp.sort_values(["game_date_dt", "OPP_TEAM"])
        
        # Prepare offensive team games for merge
        off_games_merge = off_games.copy()
        off_games_merge["GAME_DATE_DT"] = pd.to_datetime(off_games_merge["GAME_DATE"])
        off_games_merge = off_games_merge.sort_values("GAME_DATE_DT")
        
        # Merge with opponent defensive ranks using merge_asof
        off_games_with_opp_rank = pd.merge_asof(
            off_games_merge,
            daily_ranks_opp,
            left_on="GAME_DATE_DT",
            right_on="game_date_dt",
            left_by="OPP_TEAM",
            right_by="OPP_TEAM",
            direction="backward"
        )
        off_games_with_opp_rank["opp_def_bucket"] = off_games_with_opp_rank["def_rank"].apply(def_bucket)
        off_pts_vs_def_bucket = off_games_with_opp_rank[
            off_games_with_opp_rank["opp_def_bucket"] == def_def_bucket
        ]["PTS"].mean()
    else:
        off_pts_vs_def_bucket = np.nan
    
    if off_off_bucket is not None:
        # Prepare daily ranks for merge_asof
        daily_ranks_opp = daily_ranks.copy()
        daily_ranks_opp["game_date_dt"] = pd.to_datetime(daily_ranks_opp["game_date"])
        daily_ranks_opp = daily_ranks_opp.rename(columns={"TEAM_ABBREVIATION": "OPP_TEAM"})
        daily_ranks_opp = daily_ranks_opp.sort_values(["game_date_dt", "OPP_TEAM"])
        
        # Prepare defensive team games for merge
        def_games_merge = def_games.copy()
        def_games_merge["GAME_DATE_DT"] = pd.to_datetime(def_games_merge["GAME_DATE"])
        def_games_merge = def_games_merge.sort_values("GAME_DATE_DT")
        
        # Merge with opponent offensive ranks using merge_asof
        def_games_with_opp_rank = pd.merge_asof(
            def_games_merge,
            daily_ranks_opp,
            left_on="GAME_DATE_DT",
            right_on="game_date_dt",
            left_by="OPP_TEAM",
            right_by="OPP_TEAM",
            direction="backward"
        )
        def_games_with_opp_rank["opp_off_bucket"] = def_games_with_opp_rank["off_rank"].apply(off_bucket)
        def_pts_allowed_vs_off_bucket = def_games_with_opp_rank[
            def_games_with_opp_rank["opp_off_bucket"] == off_off_bucket
        ]["PTS_ALLOWED"].mean()
    else:
        def_pts_allowed_vs_off_bucket = np.nan
    
    # Add bucket averages as two separate rows
    if off_pts_vs_def_bucket is not None and not pd.isna(off_pts_vs_def_bucket):
        conditions.append({
            "condition": f"{off_team} vs {def_def_bucket}",
            "off_team_pts_scored": off_pts_vs_def_bucket,
            "def_team_pts_allowed": np.nan  # Empty for second line
        })
    
    if def_pts_allowed_vs_off_bucket is not None and not pd.isna(def_pts_allowed_vs_off_bucket):
        conditions.append({
            "condition": f"{def_team} vs {off_off_bucket}",
            "off_team_pts_scored": np.nan,  # Empty for second line
            "def_team_pts_allowed": def_pts_allowed_vs_off_bucket
        })
    
    # 3) Home/Away conditions (only show the relevant one based on actual home/away teams)
    if off_team == home_team:
        # Offensive team is home
        off_pts_at_home = off_games[off_games["HOME_AWAY"] == "HOME"]["PTS"].mean()
        def_pts_allowed_on_road = def_games[def_games["HOME_AWAY"] == "AWAY"]["PTS_ALLOWED"].mean()
        conditions.append({
            "condition": f"{off_team} @ Home / {def_team} on Road",
            "off_team_pts_scored": off_pts_at_home,
            "def_team_pts_allowed": def_pts_allowed_on_road
        })
    else:
        # Offensive team is away
        off_pts_on_road = off_games[off_games["HOME_AWAY"] == "AWAY"]["PTS"].mean()
        def_pts_allowed_at_home = def_games[def_games["HOME_AWAY"] == "HOME"]["PTS_ALLOWED"].mean()
        conditions.append({
            "condition": f"{off_team} on Road / {def_team} @ Home",
            "off_team_pts_scored": off_pts_on_road,
            "def_team_pts_allowed": def_pts_allowed_at_home
        })
    
    # 5) Offensive team in wins vs defensive team in losses
    off_pts_in_wins = off_games[off_games["WL"] == "W"]["PTS"].mean()
    def_pts_allowed_in_losses = def_games[def_games["WL"] == "L"]["PTS_ALLOWED"].mean()
    conditions.append({
        "condition": f"{off_team} in Wins / {def_team} in Losses",
        "off_team_pts_scored": off_pts_in_wins,
        "def_team_pts_allowed": def_pts_allowed_in_losses
    })
    
    # 6) Offensive team in losses vs defensive team in wins
    off_pts_in_losses = off_games[off_games["WL"] == "L"]["PTS"].mean()
    def_pts_allowed_in_wins = def_games[def_games["WL"] == "W"]["PTS_ALLOWED"].mean()
    conditions.append({
        "condition": f"{off_team} in Losses / {def_team} in Wins",
        "off_team_pts_scored": off_pts_in_losses,
        "def_team_pts_allowed": def_pts_allowed_in_wins
    })
    
    # Convert to DataFrame
    result_df = pd.DataFrame(conditions)
    
    return result_df

def plot_team_matchup_comparison(matchup_df, off_team, def_team, home_team, away_team):
    """
    Create a horizontal bar graph with pairs of adjacent bars representing team points scored 
    and opponent points allowed across various conditions.
    
    Parameters:
    -----------
    matchup_df : pd.DataFrame
        DataFrame with columns: condition, off_team_pts_scored, def_team_pts_allowed
        (output from build_team_matchup_stats)
    off_team : str
        Offensive team abbreviation (e.g., "LAL")
    def_team : str
        Defensive team abbreviation (e.g., "NOP")
    home_team : str
        Home team abbreviation (e.g., "NOP")
    away_team : str
        Away team abbreviation (e.g., "LAL")
    
    Returns:
    --------
    matplotlib.figure.Figure
        The matplotlib Figure object
    """
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Number of conditions
    n_conditions = len(matchup_df)
    
    # Adjust y-positions to handle bucket averages that are split into two rows
    # We want consistent spacing: each condition category should have the same vertical space
    # Bucket averages use 2 rows but should share the same y-position (like regular conditions)
    y_pos = []
    current_y = 0
    i = 0
    while i < n_conditions:
        condition = matchup_df.iloc[i]["condition"]
        # Check if this is a bucket average row (single team vs bucket)
        if " vs " in condition and " / " not in condition and condition != "Season Averages":
            # Check if this row has only one value (part of a bucket average pair)
            has_off = pd.notna(matchup_df.iloc[i]["off_team_pts_scored"])
            has_def = pd.notna(matchup_df.iloc[i]["def_team_pts_allowed"])
            # If this row has only one value, check if next row is the matching pair
            if (has_off and not has_def) or (not has_off and has_def):
                if i < n_conditions - 1:
                    next_condition = matchup_df.iloc[i+1]["condition"]
                    next_has_off = pd.notna(matchup_df.iloc[i+1]["off_team_pts_scored"])
                    next_has_def = pd.notna(matchup_df.iloc[i+1]["def_team_pts_allowed"])
                    # If next row is also a bucket average with the complementary value, they're a pair
                    if (" vs " in next_condition and " / " not in next_condition and 
                        next_condition != "Season Averages" and
                        ((next_has_off and not next_has_def) or (not next_has_off and next_has_def))):
                        # These are a pair - they share the same y-position
                        y_pos.append(current_y)  # First row of pair
                        y_pos.append(current_y)  # Second row of pair (same y-position)
                        current_y += 1
                        i += 2  # Skip both rows
                        continue
        # Regular condition (including Season Averages and conditions with " / ")
        y_pos.append(current_y)
        current_y += 1
        i += 1
    
    y_pos = np.array(y_pos)
    
    # Bar width
    bar_width = 0.35
    
    # Plot bars with brighter colors (handle NaN values)
    # Filter out NaN values for plotting
    off_pts = matchup_df["off_team_pts_scored"].fillna(0)
    def_pts_allowed = matchup_df["def_team_pts_allowed"].fillna(0)
    
    bars1 = ax.barh(
        y_pos - bar_width/2,
        off_pts,
        bar_width,
        label=f"{off_team} Points Scored",
        color="orange",
        alpha=0.9
    )
    
    bars2 = ax.barh(
        y_pos + bar_width/2,
        def_pts_allowed,
        bar_width,
        label=f"{def_team} Points Allowed",
        color="blue",
        alpha=0.9
    )
    
    # Hide bars where values are NaN (width = 0)
    for i, (bar, val) in enumerate(zip(bars1, matchup_df["off_team_pts_scored"])):
        if pd.isna(val) or val == 0:
            bar.set_width(0.01)  # Tiny width to make it invisible
            bar.set_visible(False)
    
    for i, (bar, val) in enumerate(zip(bars2, matchup_df["def_team_pts_allowed"])):
        if pd.isna(val) or val == 0:
            bar.set_width(0.01)  # Tiny width to make it invisible
            bar.set_visible(False)
    
    # Completely hide y-axis (spine, ticks, labels)
    ax.set_yticks([])
    ax.set_yticklabels([])
    ax.spines['left'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Set x-axis label and start from 100
    ax.set_xlabel("Points", fontsize=25, fontweight="bold")
    ax.set_xlim(left=100)
    # Increase x-axis tick label font size
    ax.tick_params(axis='x', labelsize=16)
    
    # Remove plot title (will be added separately above)
    ax.set_title("")
    
    # Remove extra margin - labels will be outside the plot using HTML/CSS
    ax.margins(x=0)  # No horizontal margin for x-axis
    
    # Add value labels on each individual bar (only for visible bars)
    for i, bar in enumerate(bars1):
        width = bar.get_width()
        val = matchup_df["off_team_pts_scored"].iloc[i]
        if not pd.isna(val) and val != 0 and width > 0.01:
            ax.text(
                width + 0.5,
                bar.get_y() + bar.get_height() / 2,
                f'{width:.1f}',
                ha="left",
                va="center",
                fontsize=20,
                fontweight="bold"
            )
    
    for i, bar in enumerate(bars2):
        width = bar.get_width()
        val = matchup_df["def_team_pts_allowed"].iloc[i]
        if not pd.isna(val) and val != 0 and width > 0.01:
            ax.text(
                width + 0.5,
                bar.get_y() + bar.get_height() / 2,
                f'{width:.1f}',
                ha="left",
                va="center",
                fontsize=20,
                fontweight="bold"
            )
    
    # Add grid for readability
    ax.grid(axis="x", alpha=0.3, linestyle="--", zorder=0)
    ax.set_axisbelow(True)
    
    # Add legend
    ax.legend(
        loc="lower right",
        fontsize=24,
        framealpha=0.9
    )
    
    # Invert y-axis so top condition is at top
    ax.invert_yaxis()
    
    plt.tight_layout()
    # Adjust left margin to leave space for labels, and adjust top/bottom margins for better label alignment
    # Reduce top margin to minimize gap between labels and bars
    fig.subplots_adjust(left=0.40, top=0.98, bottom=0.08)
    
    return fig, matchup_df
