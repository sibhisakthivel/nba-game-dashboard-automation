import pandas as pd
import numpy as np

def player_hit_rate_summary(player_id, prop_line, pbs, tbs, daily_ranks, teammates=None):
    """
    Generate a hit rate summary table for a player across various game categories.
    
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
    teammates : list, optional
        List of teammate identifiers (personId int or familyName str) to track absence
        
    Returns:
    --------
    pd.DataFrame
        Summary table with Category, Games, and Hit Rate (%)
    """
    
    if teammates is None:
        teammates = []
    
    # =========================================================
    # 1) Base: Player game-level dataframe
    # =========================================================
    
    player_df = (
        pbs[pbs["personId"] == player_id]
        .copy()
    )
    
    player_df["game_date_dt"] = pd.to_datetime(player_df["game_date"])
    
    # Get player's team
    team_abbrev = player_df["teamTricode"].iloc[0]
    
    # =========================================================
    # 2) Merge TEAM context (WL, team points, opponent)
    # =========================================================
    
    tbs_ctx = tbs.copy()
    tbs_ctx["GAME_DATE_DT"] = pd.to_datetime(tbs_ctx["GAME_DATE"])
    
    # Team rows only
    team_games = tbs_ctx[tbs_ctx["TEAM_ABBREVIATION"] == team_abbrev][
        ["GAME_ID", "GAME_DATE_DT", "WL", "PTS", "MATCHUP"]
    ].rename(columns={
        "PTS": "team_pts"
    })
    
    player_df = player_df.merge(
        team_games,
        left_on="game_id",
        right_on="GAME_ID",
        how="left"
    )
    
    # Home / Away
    player_df["HOME_AWAY"] = player_df["MATCHUP"].apply(
        lambda x: "AWAY" if "@" in x else "HOME"
    )
    
    # =========================================================
    # 3) Merge opponent defensive rank (NO leakage)
    # =========================================================
    
    daily_ranks_plot = daily_ranks.copy()
    daily_ranks_plot["game_date_dt"] = pd.to_datetime(daily_ranks_plot["game_date"])
    
    # Opponent abbreviation
    player_df["OPP_TEAM"] = player_df["MATCHUP"].str[-3:]
    
    player_df = player_df.sort_values("game_date_dt")
    daily_ranks_plot = daily_ranks_plot.sort_values("game_date_dt")
    
    player_df = pd.merge_asof(
        player_df,
        daily_ranks_plot,
        left_on="game_date_dt",
        right_on="game_date_dt",
        left_by="OPP_TEAM",
        right_by="TEAM_ABBREVIATION",
        direction="backward"
    )
    
    # =========================================================
    # 4) Teammate OUT flags (build dynamically)
    # =========================================================
    
    pbs_names = pbs.copy()
    pbs_names["familyName"] = pbs_names["familyName"].str.lower()
    
    player_game_ids = set(player_df["game_id"])
    
    teammate_out_cols = []
    teammate_names = []
    
    if teammates:
        for i, teammate_id in enumerate(teammates):
            if isinstance(teammate_id, str):
                # Name-based identification (e.g., "reaves")
                teammate_games = set(
                    pbs_names[
                        (pbs_names["familyName"] == teammate_id.lower()) &
                        (pbs_names["game_id"].isin(player_game_ids))
                    ]["game_id"]
                )
                out_col = f"teammate_{i}_out"
                player_df[out_col] = ~player_df["game_id"].isin(teammate_games)
                
                # Get teammate name for labels
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
                player_df[out_col] = ~player_df["game_id"].isin(teammate_games)
                
                # Get teammate name for labels
                name_row = (
                    pbs_names[pbs_names["personId"] == teammate_id]
                    [["firstName", "familyName"]]
                    .drop_duplicates()
                    .iloc[0]
                )
                teammate_name = f"{name_row['firstName'].title()} {name_row['familyName'].title()}"
            
            teammate_out_cols.append(out_col)
            teammate_names.append(teammate_name)
    
    # Fill NaN values for teammate columns
    for col in teammate_out_cols:
        player_df[col] = player_df[col].fillna(False)
    
    # =========================================================
    # 5) Hit flag + defense buckets
    # =========================================================
    
    player_df["hit"] = player_df["points"] > prop_line
    
    def def_bucket(rank):
        if pd.isna(rank):
            return None
        if rank <= 10:
            return "Top 10 Defense"
        elif rank <= 20:
            return "Middle 10 Defense"
        else:
            return "Bottom 10 Defense"
    
    player_df["def_bucket"] = player_df["def_rank"].apply(def_bucket)
    
    # =========================================================
    # 6) Helper for hit-rate rows
    # =========================================================
    
    def hit_row(df, label):
        if len(df) == 0:
            return {
                "Category": label,
                "Games": 0,
                "Hit Rate (%)": None
            }
        return {
            "Category": label,
            "Games": len(df),
            "Hit Rate (%)": round(df["hit"].mean() * 100, 1)
        }
    
    rows = []
    
    # =========================================================
    # 7) Build summary table
    # =========================================================
    
    rows.append(hit_row(player_df, "Season (All Games)"))
    rows.append(hit_row(player_df.tail(10), "Last 10 Games"))
    
    rows.append(hit_row(player_df[player_df["WL"] == "W"], "Wins"))
    rows.append(hit_row(player_df[player_df["WL"] == "L"], "Losses"))
    
    rows.append(hit_row(player_df[player_df["HOME_AWAY"] == "HOME"], "Home"))
    rows.append(hit_row(player_df[player_df["HOME_AWAY"] == "AWAY"], "Away"))
    
    # Teammate absence rows
    for i, (out_col, teammate_name) in enumerate(zip(teammate_out_cols, teammate_names)):
        rows.append(hit_row(player_df[player_df[out_col]], f"{teammate_name} OUT"))
    
    # Combined teammate absence (if 2+ teammates)
    if len(teammate_out_cols) >= 2:
        combined_mask = player_df[teammate_out_cols[0]]
        for col in teammate_out_cols[1:]:
            combined_mask = combined_mask & player_df[col]
        combined_name = " + ".join(teammate_names) + " OUT"
        rows.append(hit_row(player_df[combined_mask], combined_name))
    
    # Defense bucket rows
    rows.append(hit_row(
        player_df[player_df["def_bucket"] == "Top 10 Defense"],
        "Top 10 Defense"
    ))
    rows.append(hit_row(
        player_df[player_df["def_bucket"] == "Middle 10 Defense"],
        "Middle 10 Defense"
    ))
    rows.append(hit_row(
        player_df[player_df["def_bucket"] == "Bottom 10 Defense"],
        "Bottom 10 Defense"
    ))
    
    summary_table = pd.DataFrame(rows)
    
    return summary_table
