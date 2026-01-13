import pandas as pd
import numpy as np

def export_player_scoring(player_id, prop_line, pbs, tbs, daily_ranks, teammate_ids=None):
    """
    Export all data used to build the player scoring plot to a CSV-ready DataFrame.
    
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
    teammate_ids : list, optional
        List of teammate identifiers (personId int or familyName str) to track absence
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with all columns used in the plot, ready for CSV export
    """
    
    # =========================================================
    # 1) Prepare player plotting dataframe (same as plot function)
    # =========================================================

    export_df = pbs[pbs["personId"] == player_id].copy()

    export_df = (
        export_df
        .sort_values(["game_date", "game_id"])
        .reset_index(drop=True)
    )

    export_df["game_number"] = np.arange(1, len(export_df) + 1)
    export_df["game_date_dt"] = pd.to_datetime(export_df["game_date"])

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

    team = export_df["teamTricode"].iloc[0]

    export_df = export_df.merge(
        opp_lookup[opp_lookup["team"] == team][["game_id", "OPP_TEAM"]],
        on="game_id",
        how="left",
        validate="one_to_one"
    )

    # =========================================================
    # 3) AS-OF MERGE opponent defensive rank
    # =========================================================

    # Convert daily_ranks to match team_defense_daily structure
    daily_ranks_export = daily_ranks.copy()
    daily_ranks_export["as_of_date"] = pd.to_datetime(daily_ranks_export["game_date"]) + pd.Timedelta(days=1)
    
    daily_ranks_export = daily_ranks_export.rename(
        columns={"TEAM_ABBREVIATION": "OPP_TEAM"}
    )

    export_df = export_df.sort_values("game_date_dt")
    daily_ranks_export = daily_ranks_export.sort_values("as_of_date")

    export_df = pd.merge_asof(
        export_df,
        daily_ranks_export,
        left_on="game_date_dt",
        right_on="as_of_date",
        by="OPP_TEAM",
        direction="backward"
    )

    export_df = export_df.rename(columns={"def_rank": "opp_def_rank"})

    # =========================================================
    # 4) Add prop line hit flag
    # =========================================================
    
    export_df["hit_prop_line"] = export_df["points"] >= prop_line
    export_df["prop_line"] = prop_line

    # =========================================================
    # 5) Add low minutes flag (≤30)
    # =========================================================
    
    export_df["low_minutes"] = export_df["minutes"] <= 30

    # =========================================================
    # 6) Add teammate absence flags
    # =========================================================

    pbs_names = pbs.copy()
    pbs_names["firstName"] = pbs_names["firstName"].str.lower()
    pbs_names["familyName"] = pbs_names["familyName"].str.lower()

    player_game_ids = set(export_df["game_id"])

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
                
                # Get teammate name for column header
                name_row = (
                    pbs_names[pbs_names["familyName"] == teammate_id.lower()]
                    [["firstName", "familyName"]]
                    .drop_duplicates()
                    .iloc[0]
                )
                teammate_name = f"{name_row['familyName'].title()}"
                
                # Create column with teammate name
                out_col = f"teammate_{i+1}_out_{teammate_name}"
                export_df[out_col] = ~export_df["game_id"].isin(teammate_games)
            else:
                # personId-based identification
                teammate_games = set(
                    pbs_names[
                        (pbs_names["personId"] == teammate_id) &
                        (pbs_names["game_id"].isin(player_game_ids))
                    ]["game_id"]
                )
                
                # Get teammate name for column header
                name_row = (
                    pbs_names[pbs_names["personId"] == teammate_id]
                    [["firstName", "familyName"]]
                    .drop_duplicates()
                    .iloc[0]
                )
                teammate_name = f"{name_row['firstName'].title()}_{name_row['familyName'].title()}"
                
                # Create column with teammate name
                out_col = f"teammate_{i+1}_out_{teammate_name}"
                export_df[out_col] = ~export_df["game_id"].isin(teammate_games)

    # =========================================================
    # 7) Select and order columns for export
    # =========================================================
    
    # Core columns
    core_cols = [
        "game_number",
        "game_date",
        "game_id",
        "points",
        "minutes",
        "szn_avg_ppg",
        "r10_avg_ppg",
        "OPP_TEAM",
        "opp_def_rank",
        "prop_line",
        "hit_prop_line",
        "low_minutes"
    ]
    
    # Add teammate columns if they exist
    teammate_cols = [col for col in export_df.columns if col.startswith("teammate_") and "_out_" in col]
    # Sort teammate columns
    teammate_cols = sorted(teammate_cols)
    
    # Combine columns
    export_cols = core_cols + teammate_cols
    
    # Only include columns that exist in the dataframe
    export_cols = [col for col in export_cols if col in export_df.columns]
    
    # Select final columns
    export_df = export_df[export_cols].copy()
    
    # Sort by game_number to ensure proper order
    export_df = export_df.sort_values("game_number").reset_index(drop=True)

    export_df.to_csv(
        f"player_{player_id}_scoring_plot.csv",
        index=False
    )
    
    return export_df