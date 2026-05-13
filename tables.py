import calendar
import pandas as pd
from config import DEF_BUCKET_TOP, DEF_BUCKET_MIDDLE
from utils import get_teammate_game_ids

def player_hit_rate_summary(player_id, prop_line, pbs, tbs, daily_ranks, teammates=None, matchup_home_away=None, matchup_opp_def_bucket=None, stat="points"):
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
    matchup_home_away : str, optional
        Home/away status for the current matchup ("HOME" or "AWAY")
    matchup_opp_def_bucket : str, optional
        Opponent defensive bucket for the current matchup (e.g., "Top 10 Defense")
        
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

    if len(player_df) == 0:
        return pd.DataFrame(columns=["Category", "Games", "Hit Rate (%)"])

    player_df["game_date_dt"] = player_df["game_date"]

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
        lambda x: "AWAY" if pd.notna(x) and "@" in str(x) else "HOME" if pd.notna(x) else None
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
    pbs_names["firstName"] = pbs_names["firstName"].str.lower()
    pbs_names["familyName"] = pbs_names["familyName"].str.lower()

    player_game_ids = set(player_df["game_id"])

    teammate_out_cols = []
    teammate_names = []

    if teammates:
        for i, teammate_id in enumerate(teammates):
            # Game-id lookup via shared utility (lowercases both name fields)
            teammate_games = get_teammate_game_ids(pbs, teammate_id, player_game_ids)

            out_col = f"teammate_{i}_out"
            player_df[out_col] = ~player_df["game_id"].isin(teammate_games)

            # Name lookup for row labels
            if isinstance(teammate_id, str):
                name_rows = (
                    pbs_names[pbs_names["familyName"] == teammate_id.lower()]
                    [["familyName"]]
                    .drop_duplicates()
                )
                if len(name_rows) > 0:
                    teammate_name = name_rows.iloc[0]["familyName"].title()
                else:
                    teammate_name = teammate_id.title()
            else:
                name_rows = (
                    pbs_names[pbs_names["personId"] == teammate_id]
                    [["firstName", "familyName"]]
                    .drop_duplicates()
                )
                if len(name_rows) > 0:
                    name_row = name_rows.iloc[0]
                    teammate_name = f"{name_row['firstName'].title()} {name_row['familyName'].title()}"
                else:
                    teammate_name = f"Teammate {i+1}"

            teammate_out_cols.append(out_col)
            teammate_names.append(teammate_name)

    # Fill NaN values for teammate columns
    for col in teammate_out_cols:
        player_df[col] = player_df[col].fillna(False)
    
    # =========================================================
    # 5) Hit flag + defense buckets
    # =========================================================
    
    player_df["hit"] = player_df[stat] > prop_line
    
    def def_bucket(rank):
        if pd.isna(rank):
            return None
        if rank <= DEF_BUCKET_TOP:
            return "Top 10 Defense"
        elif rank <= DEF_BUCKET_MIDDLE:
            return "Middle 10 Defense"
        else:
            return "Bottom 10 Defense"
    
    player_df["def_bucket"] = player_df["def_rank"].apply(def_bucket)

    # Back-to-back detection (player_df is sorted by game_date ascending from merge_asof)
    player_df["days_since_prev"] = player_df["game_date"].diff().dt.days
    player_df["is_b2b"] = player_df["days_since_prev"] == 1

    # Month column for monthly split rows
    player_df["month"] = player_df["game_date"].dt.month

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

    # Last-N rows (player_df is sorted by game_date ascending from merge_asof)
    for _n in [5, 10, 15, 20]:
        if len(player_df) >= _n:
            rows.append(hit_row(player_df.tail(_n), f"Last {_n} Games"))

    rows.append(hit_row(player_df[player_df["WL"] == "W"], "Wins"))
    rows.append(hit_row(player_df[player_df["WL"] == "L"], "Losses"))
    
    # Only include Home or Away row based on matchup_home_away
    if matchup_home_away is not None:
        if matchup_home_away == "HOME":
            rows.append(hit_row(player_df[player_df["HOME_AWAY"] == "HOME"], "Home"))
        elif matchup_home_away == "AWAY":
            rows.append(hit_row(player_df[player_df["HOME_AWAY"] == "AWAY"], "Away"))
    else:
        # Default: show both if no matchup specified
        rows.append(hit_row(player_df[player_df["HOME_AWAY"] == "HOME"], "Home"))
        rows.append(hit_row(player_df[player_df["HOME_AWAY"] == "AWAY"], "Away"))

    rows.append(hit_row(player_df[player_df["is_b2b"]], "Back-to-Back"))

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
    
    # Team points threshold rows
    rows.append(hit_row(
        player_df[player_df["team_pts"] >= 100],
        "Team ≥100 Points"
    ))
    rows.append(hit_row(
        player_df[player_df["team_pts"] >= 110],
        "Team ≥110 Points"
    ))
    rows.append(hit_row(
        player_df[player_df["team_pts"] >= 120],
        "Team ≥120 Points"
    ))

    # Month rows (NBA season order: October through June)
    _NBA_MONTH_ORDER = [10, 11, 12, 1, 2, 3, 4, 5, 6]
    _months_present = set(player_df["month"].dropna().unique())
    for _month in _NBA_MONTH_ORDER:
        if _month in _months_present:
            rows.append(hit_row(
                player_df[player_df["month"] == _month],
                calendar.month_name[_month]
            ))

    # Matchup-specific row: Home/Away AND Opponent Defensive Bucket
    if matchup_home_away is not None and matchup_opp_def_bucket is not None:
        matchup_mask = (
            (player_df["HOME_AWAY"] == matchup_home_away) & 
            (player_df["def_bucket"] == matchup_opp_def_bucket)
        )
        matchup_label = f"{matchup_home_away} vs {matchup_opp_def_bucket}"
        rows.append(hit_row(player_df[matchup_mask], matchup_label))
    
    summary_table = pd.DataFrame(rows)
    
    # Filter out rows with no data (Games = 0 or Hit Rate is None)
    summary_table = summary_table[
        (summary_table["Games"] > 0) & (summary_table["Hit Rate (%)"].notna())
    ].copy()
    
    return summary_table
