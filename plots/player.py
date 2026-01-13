import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

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

    plot_df["game_date_dt"] = pd.to_datetime(plot_df["game_date"])

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

    # Convert daily_ranks to match team_defense_daily structure
    daily_ranks_plot = daily_ranks.copy()
    daily_ranks_plot["as_of_date"] = pd.to_datetime(daily_ranks_plot["game_date"]) + pd.Timedelta(days=1)
    
    daily_ranks_plot = daily_ranks_plot.rename(
        columns={"TEAM_ABBREVIATION": "OPP_TEAM"}
    )

    plot_df = plot_df.sort_values("game_date_dt")
    daily_ranks_plot = daily_ranks_plot.sort_values("as_of_date")

    plot_df = pd.merge_asof(
        plot_df,
        daily_ranks_plot,
        left_on="game_date_dt",
        right_on="as_of_date",
        by="OPP_TEAM",
        direction="backward"
    )

    plot_df = plot_df.rename(columns={"def_rank": "opp_def_rank"})

    # =========================================================
    # 4) Bar colors (prop logic)
    # =========================================================

    bar_colors = np.where(
        plot_df["points"] >= prop_line,
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

    low_min_mask = plot_df["minutes"] <= 30

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
    # 7) Teammate absence markers
    # =========================================================

    pbs_names = pbs.copy()
    pbs_names["firstName"] = pbs_names["firstName"].str.lower()
    pbs_names["familyName"] = pbs_names["familyName"].str.lower()

    player_game_ids = set(plot_df["game_id"])

    # Visual config (cycled if 2 teammates)
    markers = ["^", "s"]
    colors = ["tab:blue", "tab:purple"]
    y_offsets = [2.0, 3.2]

    if teammate_ids is not None:
        for i, teammate_id in enumerate(teammate_ids):
            if isinstance(teammate_id, str):
                # Name-based identification (e.g., "reaves")
                teammate_games = set(
                    pbs_names[
                        (pbs_names["familyName"] == teammate_id.lower()) &
                        (pbs_names["game_id"].isin(player_game_ids))
                    ]["game_id"]
                )
                out_col = f"teammate_{i}_out"
                plot_df[out_col] = ~plot_df["game_id"].isin(teammate_games)
                
                # Get teammate name for legend
                name_row = (
                    pbs_names[pbs_names["familyName"] == teammate_id.lower()]
                    [["firstName", "familyName"]]
                    .drop_duplicates()
                    .iloc[0]
                )
                teammate_name = f"{name_row['familyName'].title()}"
            else:
                # personId-based identification
                teammate_games = set(
                    pbs_names[
                        (pbs_names["personId"] == teammate_id) &
                        (pbs_names["game_id"].isin(player_game_ids))
                    ]["game_id"]
                )
                out_col = f"teammate_{i}_out"
                plot_df[out_col] = ~plot_df["game_id"].isin(teammate_games)
                
                # Get teammate name for legend
                name_row = (
                    pbs_names[pbs_names["personId"] == teammate_id]
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

    # Get player name for dynamic title
    player_name_row = (
        pbs[pbs["personId"] == player_id]
        [["firstName", "familyName"]]
        .drop_duplicates()
        .iloc[0]
    )
    player_name = f"{player_name_row['firstName']} {player_name_row['familyName']}"

    ax.set_ylim(10, plot_df["points"].max() + 5)
    ax.set_ylabel("Points")
    ax.set_xlabel("Game Number")
    ax.set_title(f"{player_name} — Scoring Outcomes vs Baselines")

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

    return fig, ax

def plot_player_scoring_by_def_bucket(player_id, prop_line, pbs, tbs, daily_ranks, opp_def_bucket, teammate_ids=None):
    """
    Plot a player's scoring outcomes filtered by opponent defensive bucket.
    Same output as plot_player_scoring() but only shows games where opponent
    defensive rank falls within the specified bucket.
    
    Parameters:
    -----------
    player_id : int
        Player personId
    prop_line : float
        Prop line threshold (e.g., 29.5)
    pbs : pd.DataFrame
        Player box scores dataframe
    tbs : pd.DataFrame
        Team box scores dataframe
    daily_ranks : pd.DataFrame
        Daily team rankings dataframe with defensive ranks
    opp_def_bucket : str or tuple
        Opponent defensive bucket to filter by. Can be:
        - String: "top10", "middle10", "bottom10" (case-insensitive)
        - Tuple: (min_rank, max_rank) for custom range (e.g., (1, 10), (11, 20))
    teammate_ids : list, optional
        List of teammate identifiers (personId int or familyName str) to track absence
    
    Returns:
    --------
    fig, ax : matplotlib figure and axis objects
        Same format as plot_player_scoring()
    """
    
    # =========================================================
    # 1) Prepare player plotting dataframe (same as plot_player_scoring)
    # =========================================================

    plot_df = pbs[pbs["personId"] == player_id]

    plot_df = (
        plot_df
        .sort_values(["game_date", "game_id"])
        .reset_index(drop=True)
    )

    plot_df["game_date_dt"] = pd.to_datetime(plot_df["game_date"])

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

    # Convert daily_ranks to match team_defense_daily structure
    daily_ranks_plot = daily_ranks.copy()
    daily_ranks_plot["as_of_date"] = pd.to_datetime(daily_ranks_plot["game_date"]) + pd.Timedelta(days=1)
    
    daily_ranks_plot = daily_ranks_plot.rename(
        columns={"TEAM_ABBREVIATION": "OPP_TEAM"}
    )

    plot_df = plot_df.sort_values("game_date_dt")
    daily_ranks_plot = daily_ranks_plot.sort_values("as_of_date")

    plot_df = pd.merge_asof(
        plot_df,
        daily_ranks_plot,
        left_on="game_date_dt",
        right_on="as_of_date",
        by="OPP_TEAM",
        direction="backward"
    )

    plot_df = plot_df.rename(columns={"def_rank": "opp_def_rank"})

    # =========================================================
    # 4) Filter by opponent defensive bucket
    # =========================================================
    
    # Parse the bucket input
    if isinstance(opp_def_bucket, str):
        bucket_lower = opp_def_bucket.lower().strip()
        if bucket_lower in ["top10", "top 10", "top 10 defense"]:
            bucket_mask = plot_df["opp_def_rank"] <= 10
            bucket_label = "Top 10 Defense"
        elif bucket_lower in ["middle10", "middle 10", "middle 10 defense"]:
            bucket_mask = (plot_df["opp_def_rank"] > 10) & (plot_df["opp_def_rank"] <= 20)
            bucket_label = "Middle 10 Defense"
        elif bucket_lower in ["bottom10", "bottom 10", "bottom 10 defense"]:
            bucket_mask = plot_df["opp_def_rank"] > 20
            bucket_label = "Bottom 10 Defense"
        else:
            raise ValueError(
                f"Invalid bucket string '{opp_def_bucket}'. "
                f"Must be one of: 'top10', 'middle10', 'bottom10'"
            )
    elif isinstance(opp_def_bucket, (tuple, list)) and len(opp_def_bucket) == 2:
        min_rank, max_rank = opp_def_bucket
        bucket_mask = (plot_df["opp_def_rank"] >= min_rank) & (plot_df["opp_def_rank"] <= max_rank)
        bucket_label = f"Rank {min_rank}-{max_rank}"
    else:
        raise TypeError(
            f"opp_def_bucket must be a string ('top10', 'middle10', 'bottom10') "
            f"or a tuple (min_rank, max_rank), got {type(opp_def_bucket)}"
        )
    
    # Filter the dataframe
    plot_df = plot_df[bucket_mask & plot_df["opp_def_rank"].notna()].copy()
    
    if len(plot_df) == 0:
        raise ValueError(f"No games found for opponent defensive bucket: {bucket_label}")
    
    # Recalculate game numbers after filtering
    plot_df = plot_df.reset_index(drop=True)
    plot_df["game_number"] = np.arange(1, len(plot_df) + 1)
    x = np.arange(len(plot_df))

    # =========================================================
    # 5) Bar colors (prop logic)
    # =========================================================

    bar_colors = np.where(
        plot_df["points"] >= prop_line,
        "tab:green",
        "tab:red"
    )

    # =========================================================
    # 6) Plot
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
    # 7) Low minutes marker (≤30)
    # =========================================================

    low_min_mask = plot_df["minutes"] <= 30

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
    # 8) Teammate absence markers
    # =========================================================

    pbs_names = pbs.copy()
    pbs_names["firstName"] = pbs_names["firstName"].str.lower()
    pbs_names["familyName"] = pbs_names["familyName"].str.lower()

    player_game_ids = set(plot_df["game_id"])

    # Visual config (cycled if 2 teammates)
    markers = ["^", "s"]
    colors = ["tab:blue", "tab:purple"]
    y_offsets = [2.0, 3.2]

    if teammate_ids is not None:
        for i, teammate_id in enumerate(teammate_ids):
            if isinstance(teammate_id, str):
                # Name-based identification (e.g., "reaves")
                teammate_games = set(
                    pbs_names[
                        (pbs_names["familyName"] == teammate_id.lower()) &
                        (pbs_names["game_id"].isin(player_game_ids))
                    ]["game_id"]
                )
                out_col = f"teammate_{i}_out"
                plot_df[out_col] = ~plot_df["game_id"].isin(teammate_games)
                
                # Get teammate name for legend
                name_row = (
                    pbs_names[pbs_names["familyName"] == teammate_id.lower()]
                    [["firstName", "familyName"]]
                    .drop_duplicates()
                    .iloc[0]
                )
                teammate_name = f"{name_row['familyName'].title()}"
            else:
                # personId-based identification
                teammate_games = set(
                    pbs_names[
                        (pbs_names["personId"] == teammate_id) &
                        (pbs_names["game_id"].isin(player_game_ids))
                    ]["game_id"]
                )
                out_col = f"teammate_{i}_out"
                plot_df[out_col] = ~plot_df["game_id"].isin(teammate_games)
                
                # Get teammate name for legend
                name_row = (
                    pbs_names[pbs_names["personId"] == teammate_id]
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
    # 9) Opponent team + defensive rank labels (BOTTOM)
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
    # 10) Formatting
    # =========================================================

    # Get player name for dynamic title
    player_name_row = (
        pbs[pbs["personId"] == player_id]
        [["firstName", "familyName"]]
        .drop_duplicates()
        .iloc[0]
    )
    player_name = f"{player_name_row['firstName']} {player_name_row['familyName']}"

    ax.set_ylim(10, plot_df["points"].max() + 5)
    ax.set_ylabel("Points")
    ax.set_xlabel("Game Number")
    ax.set_title(f"{player_name} — Scoring Outcomes vs Baselines ({bucket_label})")

    ax.set_xticks(x[::max(1, len(x)//10)])  # Show ~10 ticks
    ax.set_xticklabels(plot_df["game_number"][::max(1, len(x)//10)])

    ax.grid(axis="y", alpha=0.25)
    ax.legend(
        fontsize=9,
        frameon=False,
        labelspacing=0.4,
        handlelength=1.5,
        handletextpad=0.6
    )

    plt.tight_layout()

    return fig, ax

def plot_player_team_points_overlap(player_id, pbs, tbs, daily_ranks, teammate_ids=None):
    """
    Plot a player's points vs team total points with overlapping bars and season averages.
    
    Parameters:
    -----------
    player_id : int
        Player personId
    pbs : pd.DataFrame
        Player box scores dataframe
    tbs : pd.DataFrame
        Team box scores dataframe
    daily_ranks : pd.DataFrame
        Daily team rankings dataframe with defensive ranks
    teammate_ids : list, optional
        List of teammate identifiers (personId int or familyName str) to track absence
    """
    
    if teammate_ids is None:
        teammate_ids = []
    if len(teammate_ids) > 2:
        raise ValueError("Max 2 teammates allowed (visual clarity).")
    
    # =========================================================
    # 1) Build player-game dataframe
    # =========================================================
    
    player_df = pbs[pbs["personId"] == player_id].copy()
    player_df = player_df.sort_values(["game_date", "game_id"]).reset_index(drop=True)
    
    # Get player's team
    team_abbrev = player_df["teamTricode"].iloc[0]
    
    # =========================================================
    # 2) Get team points for those games
    # =========================================================
    
    team_pts_df = (
        tbs[tbs["TEAM_ABBREVIATION"] == team_abbrev]
        [["GAME_ID", "GAME_DATE", "PTS", "MATCHUP"]]
        .rename(columns={
            "GAME_ID": "game_id",
            "GAME_DATE": "game_date",
            "PTS": "team_pts"
        })
    )
    
    # Merge player with team points
    plot_df = player_df.merge(
        team_pts_df,
        on=["game_id", "game_date"],
        how="left",
        validate="one_to_one"
    )
    
    # =========================================================
    # 3) Opponent team abbreviation
    # =========================================================
    
    plot_df["OPP_TEAM"] = plot_df["MATCHUP"].str[-3:]
    plot_df["GAME_DATE_DT"] = pd.to_datetime(plot_df["game_date"])
    plot_df = plot_df.sort_values("GAME_DATE_DT").reset_index(drop=True)
    
    # =========================================================
    # 4) Calculate player season averages (no leakage)
    # =========================================================
    
    plot_df["szn_avg_player_pts"] = (
        plot_df["points"]
        .shift(1)
        .expanding()
        .mean()
    )
    
    plot_df["r10_avg_player_pts"] = (
        plot_df["points"]
        .shift(1)
        .rolling(10, min_periods=1)
        .mean()
    )
    
    # =========================================================
    # 5) Attach opponent defensive rank (as of game date)
    # =========================================================
    
    daily_ranks_plot = daily_ranks.copy()
    daily_ranks_plot["game_date_dt"] = pd.to_datetime(daily_ranks_plot["game_date"])
    
    plot_df = plot_df.sort_values("GAME_DATE_DT")
    daily_ranks_plot = daily_ranks_plot.sort_values("game_date_dt")
    
    plot_df = pd.merge_asof(
        plot_df,
        daily_ranks_plot,
        left_on="GAME_DATE_DT",
        right_on="game_date_dt",
        left_by="OPP_TEAM",
        right_by="TEAM_ABBREVIATION",
        direction="backward"
    )
    
    # =========================================================
    # 6) Teammate absence markers
    # =========================================================
    
    pbs_names = pbs.copy()
    pbs_names["familyName"] = pbs_names["familyName"].str.lower()
    
    player_game_ids = set(plot_df["game_id"])
    
    # Visual config (cycled if 2 teammates)
    markers = ["^", "s"]
    colors = ["orange", "purple"]
    y_offsets = [2, 4.2]
    
    teammate_out_cols = []
    teammate_names = []
    
    if teammate_ids:
        for i, teammate_id in enumerate(teammate_ids):
            if isinstance(teammate_id, str):
                # Name-based identification (e.g., "reaves")
                teammate_games = set(
                    pbs_names[
                        (pbs_names["familyName"] == teammate_id.lower()) &
                        (pbs_names["game_id"].isin(player_game_ids))
                    ]["game_id"]
                )
                out_col = f"teammate_{i}_out"
                plot_df[out_col] = ~plot_df["game_id"].isin(teammate_games)
                
                # Get teammate name for legend
                name_row = (
                    pbs_names[pbs_names["familyName"] == teammate_id.lower()]
                    [["familyName"]]
                    .drop_duplicates()
                    .iloc[0]
                )
                teammate_name = name_row['familyName'].title()
            else:
                # personId-based identification
                teammate_games = set(
                    pbs_names[
                        (pbs_names["personId"] == teammate_id) &
                        (pbs_names["game_id"].isin(player_game_ids))
                    ]["game_id"]
                )
                out_col = f"teammate_{i}_out"
                plot_df[out_col] = ~plot_df["game_id"].isin(teammate_games)
                
                # Get teammate name for legend
                name_row = (
                    pbs_names[pbs_names["personId"] == teammate_id]
                    [["firstName", "familyName"]]
                    .drop_duplicates()
                    .iloc[0]
                )
                teammate_name = f"{name_row['firstName'].title()} {name_row['familyName'].title()}"
            
            teammate_out_cols.append(out_col)
            teammate_names.append(teammate_name)
    
    # =========================================================
    # 7) Plot
    # =========================================================
    
    x = np.arange(len(plot_df))
    
    fig, ax = plt.subplots(figsize=(15, 6))
    
    # -----------------------------
    # Bars: TEAM points (background)
    # -----------------------------
    ax.bar(
        x,
        plot_df["team_pts"],
        width=0.7,
        color="steelblue",
        alpha=0.35,
        label=f"{team_abbrev} Team Points"
    )
    
    # -----------------------------
    # Bars: PLAYER points (foreground)
    # -----------------------------
    player_name = f"{player_df['firstName'].iloc[0]} {player_df['familyName'].iloc[0]}"
    ax.bar(
        x,
        plot_df["points"],
        width=0.4,
        color="navy",
        alpha=0.85,
        label=f"{player_name} Points"
    )
    
    # -----------------------------
    # Player season avg line
    # -----------------------------
    ax.plot(
        x,
        plot_df["szn_avg_player_pts"],
        linestyle="--",
        linewidth=2.5,
        color="black",
        alpha=0.9,
        label=f"{player_name} Season Avg PTS"
    )
    
    # -----------------------------
    # Player rolling 10 avg line
    # -----------------------------
    ax.plot(
        x,
        plot_df["r10_avg_player_pts"],
        linestyle=":",
        linewidth=3,
        color="green",
        alpha=0.9,
        label=f"{player_name} Rolling 10 Avg PTS"
    )
    
    # -----------------------------
    # Teammate absence markers
    # -----------------------------
    for i, (out_col, teammate_name) in enumerate(zip(teammate_out_cols, teammate_names)):
        ax.scatter(
            x[plot_df[out_col]],
            plot_df.loc[plot_df[out_col], "points"] + y_offsets[i],
            marker=markers[i],
            s=90,
            color=colors[i],
            label=f"{teammate_name} OUT",
            zorder=5
        )
    
    # -----------------------------
    # Bottom labels: opponent + DEF rank
    # -----------------------------
    for i, row in plot_df.iterrows():
        if pd.notna(row.get("def_rank")):
            ax.text(
                i,
                5,
                f'{row["OPP_TEAM"]}\n#{int(row["def_rank"])}',
                ha="center",
                va="bottom",
                color="white",
                fontsize=8,
                alpha=0.85
            )
    
    # -----------------------------
    # Formatting
    # -----------------------------
    ax.set_title(f"{player_name} — Points vs {team_abbrev} Team Total (Opponent Defensive Rank)")
    ax.set_xlabel("Game Number")
    ax.set_ylabel("Points")
    
    ax.set_ylim(0, max(plot_df["team_pts"].max(), plot_df["points"].max()) + 10)
    
    ax.grid(axis="y", alpha=0.25)
    
    ax.legend(
        loc="upper left",
        frameon=False,
        fontsize=10
    )
    
    plt.tight_layout()
    plt.show()
    
    return fig, ax

def plot_player_pct_team_points(player_id, pbs, tbs, daily_ranks, teammate_ids=None):
    """
    Plot a player's percentage of team points by game with season averages and opponent defensive ranks.
    
    Parameters:
    -----------
    player_id : int
        Player personId
    pbs : pd.DataFrame
        Player box scores dataframe
    tbs : pd.DataFrame
        Team box scores dataframe
    daily_ranks : pd.DataFrame
        Daily team rankings dataframe with defensive ranks
    teammate_ids : list, optional
        List of teammate identifiers (personId int or familyName str) to track absence
    """
    
    if teammate_ids is None:
        teammate_ids = []
    if len(teammate_ids) > 2:
        raise ValueError("Max 2 teammates allowed (visual clarity).")
    
    # =========================================================
    # 1) Build player-game dataframe
    # =========================================================
    
    player_df = pbs[pbs["personId"] == player_id].copy()
    player_df = player_df.sort_values(["game_date", "game_id"]).reset_index(drop=True)
    
    # Get player's team
    team_abbrev = player_df["teamTricode"].iloc[0]
    
    # =========================================================
    # 2) Get team points for those games
    # =========================================================
    
    team_pts_df = (
        tbs[tbs["TEAM_ABBREVIATION"] == team_abbrev]
        [["GAME_ID", "GAME_DATE", "PTS", "MATCHUP"]]
        .rename(columns={
            "GAME_ID": "game_id",
            "GAME_DATE": "game_date",
            "PTS": "team_pts"
        })
    )
    
    # Merge player with team points
    plot_df = player_df.merge(
        team_pts_df,
        on=["game_id", "game_date"],
        how="left",
        validate="one_to_one"
    )
    
    # =========================================================
    # 3) Opponent team abbreviation
    # =========================================================
    
    plot_df["OPP_TEAM"] = plot_df["MATCHUP"].str[-3:]
    plot_df["GAME_DATE_DT"] = pd.to_datetime(plot_df["game_date"])
    plot_df = plot_df.sort_values("GAME_DATE_DT").reset_index(drop=True)
    
    # =========================================================
    # 4) Calculate percentage of team points
    # =========================================================
    
    plot_df["player_pct_team_pts"] = plot_df["points"] / plot_df["team_pts"] * 100
    
    # Season avg % (prior games only)
    plot_df["szn_avg_pct"] = (
        plot_df["player_pct_team_pts"]
        .shift(1)
        .expanding()
        .mean()
    )
    
    # Rolling 10-game avg % (prior games only)
    plot_df["r10_avg_pct"] = (
        plot_df["player_pct_team_pts"]
        .shift(1)
        .rolling(10, min_periods=1)
        .mean()
    )
    
    # =========================================================
    # 5) Attach opponent defensive rank (as of game date)
    # =========================================================
    
    daily_ranks_plot = daily_ranks.copy()
    daily_ranks_plot["game_date_dt"] = pd.to_datetime(daily_ranks_plot["game_date"])
    
    plot_df = plot_df.sort_values("GAME_DATE_DT")
    daily_ranks_plot = daily_ranks_plot.sort_values("game_date_dt")
    
    plot_df = pd.merge_asof(
        plot_df,
        daily_ranks_plot,
        left_on="GAME_DATE_DT",
        right_on="game_date_dt",
        left_by="OPP_TEAM",
        right_by="TEAM_ABBREVIATION",
        direction="backward"
    )
    
    # =========================================================
    # 6) Teammate absence markers
    # =========================================================
    
    pbs_names = pbs.copy()
    pbs_names["familyName"] = pbs_names["familyName"].str.lower()
    
    player_game_ids = set(plot_df["game_id"])
    
    # Visual config (cycled if 2 teammates)
    markers = ["^", "s"]
    colors = ["tab:orange", "tab:purple"]
    y_offsets = [1.5, 2.3]
    
    teammate_out_cols = []
    teammate_names = []
    
    if teammate_ids:
        for i, teammate_id in enumerate(teammate_ids):
            if isinstance(teammate_id, str):
                # Name-based identification (e.g., "reaves")
                teammate_games = set(
                    pbs_names[
                        (pbs_names["familyName"] == teammate_id.lower()) &
                        (pbs_names["game_id"].isin(player_game_ids))
                    ]["game_id"]
                )
                out_col = f"teammate_{i}_out"
                plot_df[out_col] = ~plot_df["game_id"].isin(teammate_games)
                
                # Get teammate name for legend
                name_row = (
                    pbs_names[pbs_names["familyName"] == teammate_id.lower()]
                    [["familyName"]]
                    .drop_duplicates()
                    .iloc[0]
                )
                teammate_name = name_row['familyName'].title()
            else:
                # personId-based identification
                teammate_games = set(
                    pbs_names[
                        (pbs_names["personId"] == teammate_id) &
                        (pbs_names["game_id"].isin(player_game_ids))
                    ]["game_id"]
                )
                out_col = f"teammate_{i}_out"
                plot_df[out_col] = ~plot_df["game_id"].isin(teammate_games)
                
                # Get teammate name for legend
                name_row = (
                    pbs_names[pbs_names["personId"] == teammate_id]
                    [["firstName", "familyName"]]
                    .drop_duplicates()
                    .iloc[0]
                )
                teammate_name = f"{name_row['firstName'].title()} {name_row['familyName'].title()}"
            
            teammate_out_cols.append(out_col)
            teammate_names.append(teammate_name)
    
    # =========================================================
    # 7) Plot
    # =========================================================
    
    x = np.arange(len(plot_df))
    
    fig, ax = plt.subplots(figsize=(15, 6))
    
    # -----------------------------
    # Bars: Player % of team points
    # -----------------------------
    ax.bar(
        x,
        plot_df["player_pct_team_pts"],
        width=0.7,
        color="tab:blue",
        alpha=0.5,
        label=f"{player_df['firstName'].iloc[0]} {player_df['familyName'].iloc[0]} % of Team Points"
    )
    
    # -----------------------------
    # Avg lines
    # -----------------------------
    ax.plot(
        x,
        plot_df["szn_avg_pct"],
        linestyle="--",
        linewidth=2.5,
        color="black",
        label="Season Avg %"
    )
    
    ax.plot(
        x,
        plot_df["r10_avg_pct"],
        linestyle=":",
        linewidth=2.5,
        color="tab:green",
        label="Rolling 10 Avg %"
    )
    
    # -----------------------------
    # Teammate absence markers
    # -----------------------------
    for i, (out_col, teammate_name) in enumerate(zip(teammate_out_cols, teammate_names)):
        ax.scatter(
            plot_df.index[plot_df[out_col]],
            plot_df.loc[plot_df[out_col], "player_pct_team_pts"] + y_offsets[i],
            marker=markers[i],
            s=80 if i == 0 else 70,
            color=colors[i],
            label=f"{teammate_name} OUT",
            zorder=5
        )
    
    # -----------------------------
    # Bottom labels: opponent + def rank
    # -----------------------------
    y_min = plot_df["player_pct_team_pts"].min()
    
    for i, row in plot_df.iterrows():
        if pd.notna(row.get("def_rank")):
            ax.text(
                i,
                y_min - 3,
                f'{row["OPP_TEAM"]}\n#{int(row["def_rank"])}',
                ha="center",
                va="top",
                fontsize=8,
                alpha=0.85
            )
    
    # -----------------------------
    # Formatting
    # -----------------------------
    player_name = f"{player_df['firstName'].iloc[0]} {player_df['familyName'].iloc[0]}"
    ax.set_title(f"{player_name} — % of Team Points by Game (Opponent Defensive Rank)")
    ax.set_ylabel("Percent of Team Points (%)")
    ax.set_xlabel("Game Number")
    
    ax.set_ylim(y_min - 6, plot_df["player_pct_team_pts"].max() + 5)
    
    ax.grid(axis="y", alpha=0.25)
    
    ax.legend(
        loc="upper right",
        frameon=False,
        fontsize=10
    )
    
    plt.tight_layout()
    plt.show()
    
    return fig, ax
