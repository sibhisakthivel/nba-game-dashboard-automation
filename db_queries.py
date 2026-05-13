import streamlit as st
import pandas as pd
from sqlalchemy import text

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_all_teams(_engine):
    """
    Query all unique teams from the league game log.
    
    Parameters:
    -----------
    _engine : sqlalchemy.engine
        Database connection engine (prefixed with _ to skip hashing)
    
    Returns:
    --------
    pd.DataFrame with columns: team_abbreviation, team_name
    """
    query = text("""
        SELECT DISTINCT 
            team_abbreviation,
            team_name
        FROM raw.league_game_log
        WHERE team_abbreviation IS NOT NULL
        ORDER BY team_abbreviation
    """)
    
    df = pd.read_sql(query, _engine)
    return df

@st.cache_data(ttl=3600)
def get_players_by_team(_engine, team_abbrev):
    """
    Query all unique players for a given team, ordered by season average PPG.

    Parameters:
    -----------
    _engine : sqlalchemy.engine
        Database connection engine (prefixed with _ to skip hashing)
    team_abbrev : str
        Team abbreviation (e.g., "LAL", "NOP")

    Returns:
    --------
    pd.DataFrame with columns: person_id, first_name, family_name, display_name, avg_ppg
    """
    query = text("""
        WITH player_stats AS (
            SELECT
                person_id,
                first_name,
                family_name,
                AVG(points) as avg_ppg
            FROM raw.box_score_traditional_v3
            WHERE team_tricode = :team_abbrev
                AND person_id IS NOT NULL
                AND points IS NOT NULL
            GROUP BY person_id, first_name, family_name
        )
        SELECT
            person_id,
            first_name,
            family_name,
            CONCAT(first_name, ' ', family_name) as display_name,
            avg_ppg
        FROM player_stats
        ORDER BY avg_ppg DESC, family_name, first_name
    """)

    df = pd.read_sql(query, _engine, params={"team_abbrev": team_abbrev})
    return df

@st.cache_data(ttl=3600)
def load_process_pbs_from_db(_engine, person_id=None, team_abbrev=None):
    """
    Load and process player box scores from database.
    Equivalent to load_process_pbs() but from database.

    Parameters:
    -----------
    _engine : sqlalchemy.engine
        Database connection engine (prefixed with _ to skip hashing)
    person_id : int, optional
        If provided, filter to this player only
    team_abbrev : str, optional
        If provided, filter to this team only (e.g. "LAL")

    Returns:
    --------
    pd.DataFrame with processed player box scores
    """
    team_filter = "\n                AND bs.team_tricode = :team_abbrev" if team_abbrev is not None else ""

    if person_id is not None:
        query = f"""
            SELECT DISTINCT ON (bs.game_id, bs.person_id)
                bs.game_id,
                bs.person_id,
                bs.team_tricode,
                bs.first_name,
                bs.family_name,
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
                lgl.game_date
            FROM raw.box_score_traditional_v3 bs
            INNER JOIN raw.league_game_log lgl
                ON bs.game_id = lgl.game_id
                AND bs.team_tricode = lgl.team_abbreviation
            WHERE bs.person_id = :person_id
                AND bs.person_id IS NOT NULL{team_filter}
            ORDER BY bs.game_id, bs.person_id, lgl.game_date
        """
    else:
        query = f"""
            SELECT DISTINCT ON (bs.game_id, bs.person_id)
                bs.game_id,
                bs.person_id,
                bs.team_tricode,
                bs.first_name,
                bs.family_name,
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
                lgl.game_date
            FROM raw.box_score_traditional_v3 bs
            INNER JOIN raw.league_game_log lgl
                ON bs.game_id = lgl.game_id
                AND bs.team_tricode = lgl.team_abbreviation
            WHERE bs.person_id IS NOT NULL{team_filter}
            ORDER BY bs.game_id, bs.person_id, lgl.game_date
        """

    query = text(query)

    params = {}
    if person_id is not None:
        params["person_id"] = person_id
    if team_abbrev is not None:
        params["team_abbrev"] = team_abbrev
    
    pbs = pd.read_sql(query, _engine, params=params)
    
    # Rename columns to match existing code
    pbs = pbs.rename(columns={
        "person_id": "personId",
        "team_tricode": "teamTricode",
        "first_name": "firstName",
        "family_name": "familyName",
        "game_id": "game_id"
    })
    
    # Convert game_date to datetime
    pbs["game_date"] = pd.to_datetime(pbs["game_date"])
    
    # Convert minutes (TEXT "MM:SS") to float
    def minutes_to_float(min_str):
        if pd.isna(min_str) or min_str is None or min_str == "":
            return None
        try:
            m, s = str(min_str).split(":")
            return int(m) + int(s) / 60
        except (ValueError, AttributeError):
            return None
    
    pbs["minutes"] = pbs["minutes"].apply(minutes_to_float)
    
    # Sort for correct window behavior before calculating averages
    pbs = (
        pbs
        .sort_values(["personId", "game_date"])
        .reset_index(drop=True)
    )

    # Compute combo stats (fill nulls only for involved columns, not globally)
    pbs["pra"] = pbs["points"].fillna(0) + pbs["rebounds_total"].fillna(0) + pbs["assists"].fillna(0)
    pbs["pr"]  = pbs["points"].fillna(0) + pbs["rebounds_total"].fillna(0)
    pbs["pa"]  = pbs["points"].fillna(0) + pbs["assists"].fillna(0)
    pbs["ra"]  = pbs["rebounds_total"].fillna(0) + pbs["assists"].fillna(0)

    # Compute season and rolling 10-game point averages (kept for points backward compat)
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

    return pbs

@st.cache_data
def load_process_tbs_from_db(_engine):
    """
    Load and process team box scores from database.
    Equivalent to load_process_tbs() but from database.
    
    Parameters:
    -----------
    _engine : sqlalchemy.engine
        Database connection engine (prefixed with _ to skip hashing)
    
    Returns:
    --------
    pd.DataFrame with processed team box scores
    """
    query = text("""
        SELECT 
            game_id,
            team_abbreviation,
            game_date,
            pts,
            matchup,
            wl
        FROM raw.league_game_log
        WHERE team_abbreviation IS NOT NULL
            AND game_id IS NOT NULL
        ORDER BY game_date, game_id
    """)
    
    tbs = pd.read_sql(query, _engine)
    
    # Rename columns to match existing code
    tbs = tbs.rename(columns={
        "team_abbreviation": "TEAM_ABBREVIATION",
        "game_id": "GAME_ID",
        "game_date": "GAME_DATE",
        "pts": "PTS",
        "matchup": "MATCHUP",
        "wl": "WL"
    })
    
    # Convert game_date to datetime
    tbs["GAME_DATE"] = pd.to_datetime(tbs["GAME_DATE"])
    
    # Build opponent relationships by merging on game_id
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
    
    # Filter out self-matches
    merged = merged[merged["TEAM_ABBREVIATION"] != merged["OPP_TEAM"]]
    
    tbs = (
        merged
        .rename(columns={"OPP_PTS": "PTS_ALLOWED"})
    )
    
    # Select final columns to match existing structure
    tbs = tbs[["GAME_ID", "TEAM_ABBREVIATION", "GAME_DATE", "PTS", "MATCHUP", "OPP_TEAM", "PTS_ALLOWED", "WL"]]
    
    return tbs

@st.cache_data(ttl=3600)
def build_ranks(tbs):
    """
    Build daily defensive rankings from team box scores.
    Same as existing build_ranks() function.
    
    Parameters:
    -----------
    tbs : pd.DataFrame
        Team box scores dataframe
    
    Returns:
    --------
    pd.DataFrame with daily defensive rankings
    """
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
