import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

# Set consistent DPI for matplotlib to ensure visual consistency across local and Streamlit Cloud
matplotlib.rcParams['figure.dpi'] = 100
matplotlib.rcParams['savefig.dpi'] = 100

from plots.player import plot_player_scoring  # , plot_player_scoring_by_def_bucket
from tables import player_hit_rate_summary

# New database query imports
from db_queries import (
    get_all_teams,
    get_players_by_team,
    load_process_pbs_from_db,
    load_process_tbs_from_db,
    build_ranks
)

import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

@st.cache_resource
def get_engine():
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        host=st.secrets["DB_HOST"],
        port=int(st.secrets["DB_PORT"]),
        database=st.secrets["DB_NAME"],
    )

    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"sslmode": "require"},
    )

engine = get_engine()

st.set_page_config(
    page_title="NBA Player Prop Dashboard",
    layout="wide"
)

# Custom CSS to maximize screen usage and reduce spacing
st.markdown("""
    <style>
    .main .block-container {
        padding-top: 0.25rem;
        padding-bottom: 0.25rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
        max-width: 100%;
    }
    h2, h3 {
        margin-top: 0.1rem;
        margin-bottom: 0.1rem;
    }
    .stDataFrame {
        margin-bottom: 0;
        height: 100%;
    }
    /* Increase dataframe font sizes globally - very aggressive selectors */
    [data-testid="stDataFrame"],
    [data-testid="stDataFrame"] *,
    [data-testid="stDataFrame"] table,
    [data-testid="stDataFrame"] table *,
    [data-testid="stDataFrame"] tbody,
    [data-testid="stDataFrame"] thead,
    [data-testid="stDataFrame"] tr,
    [data-testid="stDataFrame"] td,
    [data-testid="stDataFrame"] th,
    .stDataFrame,
    .stDataFrame *,
    .stDataFrame table,
    .stDataFrame table *,
    .stDataFrame tbody,
    .stDataFrame thead,
    .stDataFrame tr,
    .stDataFrame td,
    .stDataFrame th,
    /* Try targeting by streamlit's internal classes */
    div[data-baseweb="data-table"],
    div[data-baseweb="data-table"] *,
    div[data-baseweb="data-table"] table,
    div[data-baseweb="data-table"] table *,
    /* Generic table selectors within dataframe containers */
    [data-testid="stDataFrame"] > div table,
    [data-testid="stDataFrame"] > div table * {
        font-size: 22px !important;
    }
    /* Headers specifically */
    [data-testid="stDataFrame"] table th,
    .stDataFrame table th,
    [data-testid="stDataFrame"] thead th,
    .stDataFrame thead th {
        font-size: 24px !important;
        font-weight: bold !important;
    }
    .element-container {
        margin-bottom: 0.1rem;
    }
    [data-testid="stVerticalBlock"] {
        gap: 0.1rem;
    }
    section[data-testid="stSidebar"] {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)

# Team name mapping
TEAM_NAMES = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets", "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers", "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets",
    "DET": "Detroit Pistons", "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "LA Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies", "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves", "NOP": "New Orleans Pelicans", "NYK": "New York Knicks",
    "OKC": "Oklahoma City Thunder", "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers", "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs", "TOR": "Toronto Raptors",
    "UTA": "Utah Jazz", "WAS": "Washington Wizards"
}

def get_team_full_name(abbrev):
    """Get full team name from abbreviation."""
    return TEAM_NAMES.get(abbrev, abbrev)

# =========================================================
# MAIN APP
# =========================================================
    
    # =========================================================
# NEW: Cascading Dropdown Selections
    # =========================================================
    
# Initialize session state for selections
if "selected_team" not in st.session_state:
    st.session_state.selected_team = None
if "selected_player_id" not in st.session_state:
    st.session_state.selected_player_id = None
if "selected_opponent" not in st.session_state:
    st.session_state.selected_opponent = None
if "prop_line" not in st.session_state:
    st.session_state.prop_line = None
if "prev_team" not in st.session_state:
    st.session_state.prev_team = None
if "player_team_home_away" not in st.session_state:
    st.session_state.player_team_home_away = None  # "home" or "away"
if "opponent_team_home_away" not in st.session_state:
    st.session_state.opponent_team_home_away = None  # "home" or "away"

# Track team changes to reset player selection
if st.session_state.prev_team != st.session_state.selected_team:
    if st.session_state.prev_team is not None:
        st.session_state.selected_player_id = None
    st.session_state.prev_team = st.session_state.selected_team

# Get all teams for dropdowns - with error handling
try:
    teams_df = get_all_teams(engine)
    team_options = teams_df["team_abbreviation"].tolist()
except Exception as e:
    st.error(f"Database connection error: {str(e)}")
    st.info("Please check your database connection and try again.")
    team_options = []  # Provide empty list as fallback
    st.stop()  # Stop execution if we can't get teams

# Dropdown 1: Player Team Selection (always visible)
col_team_title, col_team_buttons = st.columns([3, 1])
with col_team_title:
    st.markdown("### Select Player Team")
with col_team_buttons:
    # Home/Away buttons for player team
    if st.session_state.selected_team is not None:
        col_home, col_away = st.columns(2)
        with col_home:
            home_selected = st.button("Home", key="player_team_home_btn", 
                                    type="primary" if st.session_state.player_team_home_away == "home" else "secondary",
                                    use_container_width=True)
            if home_selected:
                st.session_state.player_team_home_away = "home"
                st.session_state.opponent_team_home_away = "away"
                st.rerun()
        with col_away:
            away_selected = st.button("Away", key="player_team_away_btn",
                                    type="primary" if st.session_state.player_team_home_away == "away" else "secondary",
                                    use_container_width=True)
            if away_selected:
                st.session_state.player_team_home_away = "away"
                st.session_state.opponent_team_home_away = "home"
                st.rerun()

# Calculate index for current selection
team_index = 0
if st.session_state.selected_team is not None and st.session_state.selected_team in team_options:
    team_index = team_options.index(st.session_state.selected_team) + 1

selected_team = st.selectbox(
    "Player Team",
    options=[None] + team_options,
    index=team_index,
    key="team_selectbox"
)

st.session_state.selected_team = selected_team

# Update prev_team tracking
if st.session_state.prev_team != st.session_state.selected_team:
    st.session_state.selected_player_id = None
st.session_state.prev_team = st.session_state.selected_team

# Dropdown 2: Player Selection (only visible after team is selected)
if st.session_state.selected_team is not None:
    # Get players for selected team
    players_df = get_players_by_team(engine, st.session_state.selected_team)
    
    if len(players_df) > 0:
        # Create display options: "FirstName LastName (avg_ppg PPG)"
        player_options = [
            (row["person_id"], f"{row['display_name']} ({row['avg_ppg']:.1f} PPG)")
            for _, row in players_df.iterrows()
        ]
        
        st.markdown("### Select Player")
        
        # Find current selection index
        # Reset to None if the selected player doesn't exist in the new team
        player_found = False
        current_idx = 0
        if st.session_state.selected_player_id is not None:
            for idx, (pid, _) in enumerate(player_options):
                if pid == st.session_state.selected_player_id:
                    current_idx = idx
                    player_found = True
                    break
            # If player not found in new team, reset selection
            if not player_found:
                st.session_state.selected_player_id = None
        
        selected_player_option = st.selectbox(
            "Player",
            options=[None] + player_options,
            format_func=lambda x: "Select a player..." if x is None else (x[1] if isinstance(x, tuple) else x),
            index=0 if st.session_state.selected_player_id is None else current_idx + 1,
            key="player_selectbox"
        )
        
        if selected_player_option is not None:
            st.session_state.selected_player_id = selected_player_option[0]
        else:
            st.session_state.selected_player_id = None
            
        # Dropdown 3: Opponent Team Selection (only visible after player is selected)
        if st.session_state.selected_player_id is not None:
            # Get opponent teams (exclude selected team)
            opponent_options = [opt for opt in team_options if opt != st.session_state.selected_team]
            
            col_opp_title, col_opp_buttons = st.columns([3, 1])
            with col_opp_title:
                st.markdown("### Select Opponent Team")
            with col_opp_buttons:
                # Home/Away buttons for opponent team
                if st.session_state.selected_opponent is not None:
                    col_home, col_away = st.columns(2)
                    with col_home:
                        home_selected = st.button("Home", key="opponent_team_home_btn",
                                                type="primary" if st.session_state.opponent_team_home_away == "home" else "secondary",
                                                use_container_width=True)
                        if home_selected:
                            st.session_state.opponent_team_home_away = "home"
                            st.session_state.player_team_home_away = "away"
                            st.rerun()
                    with col_away:
                        away_selected = st.button("Away", key="opponent_team_away_btn",
                                                type="primary" if st.session_state.opponent_team_home_away == "away" else "secondary",
                                                use_container_width=True)
                        if away_selected:
                            st.session_state.opponent_team_home_away = "away"
                            st.session_state.player_team_home_away = "home"
                            st.rerun()
            
            # Find current selection index
            current_opp_idx = 0
            if st.session_state.selected_opponent is not None and st.session_state.selected_opponent in opponent_options:
                current_opp_idx = opponent_options.index(st.session_state.selected_opponent) + 1
            
            selected_opponent = st.selectbox(
                "Opponent Team",
                options=[None] + opponent_options,
                index=0 if st.session_state.selected_opponent is None else current_opp_idx,
                key="opponent_selectbox"
            )
            
            st.session_state.selected_opponent = selected_opponent
            
            # Dropdown 4: Prop Line Input (only visible after player is selected)
            if st.session_state.selected_opponent is not None:
                st.markdown("### Enter Prop Line")
                prop_line = st.number_input(
                    "Prop Line",
                    min_value=0.0,
                    max_value=100.0,
                    value=29.5 if st.session_state.prop_line is None else st.session_state.prop_line,
                    step=0.5,
                    key="prop_line_input"
                )
                
                st.session_state.prop_line = prop_line
                
                # Render player scoring plot when all selections are made
                if (st.session_state.selected_team is not None and
                    st.session_state.selected_player_id is not None and
                    st.session_state.selected_opponent is not None and
                    st.session_state.prop_line is not None):
                    
                    # Query data from database
                    pbs = load_process_pbs_from_db(engine, person_id=st.session_state.selected_player_id)
                    tbs = load_process_tbs_from_db(engine)
                    daily_ranks = build_ranks(tbs)

                    # Get team records and ranks for matchup header
                    # Get most recent daily_ranks for current records
                    latest_ranks = daily_ranks[daily_ranks["game_date"] == daily_ranks["game_date"].max()]
                    
                    # Get player team stats
                    player_team_stats = latest_ranks[latest_ranks["TEAM_ABBREVIATION"] == st.session_state.selected_team]
                    player_team_record = tbs[tbs["TEAM_ABBREVIATION"] == st.session_state.selected_team].sort_values("GAME_DATE")
                    player_wins = len(player_team_record[player_team_record["WL"] == "W"])
                    player_losses = len(player_team_record[player_team_record["WL"] == "L"])
                    player_l10_record = player_team_record.tail(10)
                    player_l10_wins = len(player_l10_record[player_l10_record["WL"] == "W"])
                    player_l10_losses = len(player_l10_record[player_l10_record["WL"] == "L"])
                    player_off_rank = int(player_team_stats["off_rank"].iloc[0]) if len(player_team_stats) > 0 else None
                    player_def_rank = int(player_team_stats["def_rank"].iloc[0]) if len(player_team_stats) > 0 else None
                    
                    # Get opponent team stats
                    opp_team_stats = latest_ranks[latest_ranks["TEAM_ABBREVIATION"] == st.session_state.selected_opponent]
                    opp_team_record = tbs[tbs["TEAM_ABBREVIATION"] == st.session_state.selected_opponent].sort_values("GAME_DATE")
                    opp_wins = len(opp_team_record[opp_team_record["WL"] == "W"])
                    opp_losses = len(opp_team_record[opp_team_record["WL"] == "L"])
                    opp_l10_record = opp_team_record.tail(10)
                    opp_l10_wins = len(opp_l10_record[opp_l10_record["WL"] == "W"])
                    opp_l10_losses = len(opp_l10_record[opp_l10_record["WL"] == "L"])
                    opp_def_rank = int(opp_team_stats["def_rank"].iloc[0]) if len(opp_team_stats) > 0 else None
                    opp_off_rank = int(opp_team_stats["off_rank"].iloc[0]) if len(opp_team_stats) > 0 else None
                    
                    # Get team full names
                    player_team_name = get_team_full_name(st.session_state.selected_team)
                    opp_team_name = get_team_full_name(st.session_state.selected_opponent)
                    
                    # Determine home/away based on selection or default
                    if st.session_state.player_team_home_away == "home":
                        away_team = st.session_state.selected_opponent
                        home_team = st.session_state.selected_team
                        away_name = opp_team_name
                        home_name = player_team_name
                    elif st.session_state.opponent_team_home_away == "home":
                        away_team = st.session_state.selected_team
                        home_team = st.session_state.selected_opponent
                        away_name = player_team_name
                        home_name = opp_team_name
                    else:
                        # Default: player team at home
                        away_team = st.session_state.selected_opponent
                        home_team = st.session_state.selected_team
                        away_name = opp_team_name
                        home_name = player_team_name
                    
                    # Determine records based on which team is away/home
                    if away_team == st.session_state.selected_opponent:
                        away_record_szn = f"{opp_wins}-{opp_losses}"
                        away_record_l10 = f"{opp_l10_wins}-{opp_l10_losses}"
                        home_record_szn = f"{player_wins}-{player_losses}"
                        home_record_l10 = f"{player_l10_wins}-{player_l10_losses}"
                    else:
                        away_record_szn = f"{player_wins}-{player_losses}"
                        away_record_l10 = f"{player_l10_wins}-{player_l10_losses}"
                        home_record_szn = f"{opp_wins}-{opp_losses}"
                        home_record_l10 = f"{opp_l10_wins}-{opp_l10_losses}"
                    
                    # Render matchup header
                    # Always show player team on left (offensive rank) and opponent team on right (defensive rank)
                    # Determine which team is left/right based on away/home position
                    if away_team == st.session_state.selected_team:
                        # Player team is away (left side)
                        left_record_szn = away_record_szn
                        left_record_l10 = away_record_l10
                        left_name = away_name
                        left_rank_label = "Off Rank"
                        left_rank_value = player_off_rank
                        
                        right_record_szn = home_record_szn
                        right_record_l10 = home_record_l10
                        right_name = home_name
                        right_rank_label = "Def Rank"
                        right_rank_value = opp_def_rank
                    else:
                        # Opponent team is away (left side), player team is home (right side)
                        left_record_szn = away_record_szn
                        left_record_l10 = away_record_l10
                        left_name = away_name
                        left_rank_label = "Def Rank"
                        left_rank_value = opp_def_rank
                        
                        right_record_szn = home_record_szn
                        right_record_l10 = home_record_l10
                        right_name = home_name
                        right_rank_label = "Off Rank"
                        right_rank_value = player_off_rank
                    
                    st.markdown("---")
                    matchup_html = f"""
                    <div style='text-align: center; padding: 1rem; background-color: rgba(0,0,0,0.1); border-radius: 10px; margin: 1rem 0;'>
                        <h2 style='margin-bottom: 1rem;'>{away_name} @ {home_name}</h2>
                        <div style='display: flex; justify-content: center; gap: 1rem;'>
                            <div style='text-align: center; flex: 1;'>
                                <div style='margin-bottom: 0.5rem; font-size: 16px; font-weight: bold;'>{left_record_szn} (L10: {left_record_l10})</div>
                                <div style='font-size: 16px; font-weight: bold;'>{left_rank_label} #{left_rank_value if left_rank_value else 'N/A'}</div>
                            </div>
                            <div style='text-align: center; flex: 1;'>
                                <div style='margin-bottom: 0.5rem; font-size: 16px; font-weight: bold;'>{right_record_szn} (L10: {right_record_l10})</div>
                                <div style='font-size: 16px; font-weight: bold;'>{right_rank_label} #{right_rank_value if right_rank_value else 'N/A'}</div>
                            </div>
                        </div>
                    </div>
                    """
                    st.markdown(matchup_html, unsafe_allow_html=True)
                    
                    # Get player name for header
                    player_name_row = (
                        pbs[pbs["personId"] == st.session_state.selected_player_id]
                        [["firstName", "familyName"]]
                        .drop_duplicates()
                        .iloc[0]
                    )
                    player_display_name = f"{player_name_row['firstName']} {player_name_row['familyName']}"
                    
                    # Render player scoring plot and hit rate table
                    st.markdown(f"<h2 style='text-align: center;'>{player_display_name} - Over {st.session_state.prop_line} Points</h2>", unsafe_allow_html=True)
                    
                    # Render player scoring plot (full width)
                    player_scoring_fig, _ = plot_player_scoring(
                        st.session_state.selected_player_id,
                        st.session_state.prop_line,
                        pbs,
                        tbs,
                        daily_ranks,
                        teammate_ids=None  # Can add teammate selection later
                    )
                    
                    # Use larger size for the plot
                    player_scoring_fig.set_size_inches(32, 15)
                    player_scoring_fig.set_dpi(100)  # Ensure consistent DPI across environments
                    player_scoring_fig.tight_layout()
                    st.pyplot(player_scoring_fig, use_container_width=True)
                    plt.close(player_scoring_fig)
                    
                    # Add spacing between player scoring plot and bottom section
                    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
                    
                    # Render hit rate summary table and team matchup comparison side by side
                    # Condensed table (35%) and expanded plot (65%)
                    col_table, col_plot = st.columns([0.35, 0.65])
                    
                    with col_table:
                        st.markdown("<h2 style='text-align: center; margin-bottom: 1rem; font-size: 32px;'>Hit Rate Summary<br></h2>", unsafe_allow_html=True)
                        
                        # Determine player's home/away status for this matchup
                        if home_team == st.session_state.selected_team:
                            player_home_away = "HOME"
                        else:
                            player_home_away = "AWAY"
                        
                        # Determine opponent defensive bucket based on their current defensive rank
                        matchup_opp_def_bucket = None
                        if opp_def_rank is not None:
                            if opp_def_rank <= 10:
                                matchup_opp_def_bucket = "Top 10 Defense"
                            elif opp_def_rank <= 20:
                                matchup_opp_def_bucket = "Middle 10 Defense"
                            else:
                                matchup_opp_def_bucket = "Bottom 10 Defense"
                        
                        summary_table = player_hit_rate_summary(
                            st.session_state.selected_player_id,
                            st.session_state.prop_line,
                            pbs,
                            tbs,
                            daily_ranks,
                            teammates=None,  # Can add teammate selection later
                            matchup_home_away=player_home_away,
                            matchup_opp_def_bucket=matchup_opp_def_bucket
                        )
                        
                        # Filter out rows with no data (Games = 0 or Hit Rate is None, or empty categories)
                        summary_table_filtered = summary_table[
                            (summary_table["Games"] > 0) & 
                            (summary_table["Hit Rate (%)"].notna()) &
                            (summary_table["Category"].notna()) &  # Remove rows with empty category names
                            (summary_table["Category"] != "")  # Remove rows with empty string categories
                        ].copy()
                        
                        # Calculate table height with increased row height to fill available space
                        # Increase per-row height to make table fill more space - expanded to fill empty space
                        table_height = (len(summary_table_filtered) + 1) * 65 + 50  # Increased row height to fill more space
                        
                        # Render as HTML table for better font size control
                        html_table = '<table style="width: 100%; border-collapse: collapse; font-size: 20px;">'
                        html_table += '<thead><tr style="background-color: rgba(49, 51, 63, 0.6);">'
                        for col in summary_table_filtered.columns:
                            html_table += f'<th style="padding: 12px; text-align: left; font-size: 22px; font-weight: bold; border-bottom: 2px solid rgba(250, 250, 250, 0.2);">{col}</th>'
                        html_table += '</tr></thead><tbody>'
                        for idx, row in summary_table_filtered.iterrows():
                            html_table += '<tr>'
                            for col in summary_table_filtered.columns:
                                html_table += f'<td style="padding: 12px; border-bottom: 1px solid rgba(250, 250, 250, 0.1); font-size: 19px;">{row[col]}</td>'
                            html_table += '</tr>'
                        html_table += '</tbody></table>'
                        
                        st.markdown(html_table, unsafe_allow_html=True)
                        
                        # Add spacing to align table and plot tops
                        st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
                        
                        # Keep original dataframe as fallback (commented out)
                        # st.dataframe(
                        #     summary_table_filtered,
                        #     use_container_width=True,
                        #     hide_index=True,
                        #     height=table_height
                        # )
                    
                    with col_plot:
                        # Get team abbreviations from session state
                        player_team_abbrev = st.session_state.selected_team
                        opponent_team_abbrev = st.session_state.selected_opponent
                        
                        # Determine home/away based on session state assignments
                        # Check which team is assigned as home/away from button clicks
                        if st.session_state.player_team_home_away == "home":
                            home_team = player_team_abbrev
                            away_team = opponent_team_abbrev
                        elif st.session_state.opponent_team_home_away == "home":
                            home_team = opponent_team_abbrev
                            away_team = player_team_abbrev
                        else:
                            # Default: player team at home if no assignment made
                            home_team = player_team_abbrev
                            away_team = opponent_team_abbrev
                        
                        # Build matchup stats and plot
                        # off_team = player's team (always shows points scored)
                        # def_team = opponent team (always shows points allowed)
                        # home_team/away_team determine which filtered stats to use
                        from plots.team import build_team_matchup_stats, plot_team_matchup_comparison_with_labels
                        
                        matchup_df = build_team_matchup_stats(
                            off_team=player_team_abbrev,
                            def_team=opponent_team_abbrev,
                            home_team=home_team,
                            away_team=away_team,
                            tbs=tbs,
                            daily_ranks=daily_ranks
                        )
                        
                        matchup_fig, matchup_df_returned = plot_team_matchup_comparison_with_labels(
                            matchup_df=matchup_df,
                            off_team=player_team_abbrev,
                            def_team=opponent_team_abbrev,
                            home_team=home_team,
                            away_team=away_team
                        )
                        
                        # Calculate plot height to match hit rate table height - even more condensed
                        # Use the same table_height calculation as in col_table block
                        # table_height is in pixels: (len(summary_table_filtered) + 1) * 65 + 50
                        table_height_pixels = (len(summary_table_filtered) + 1) * 65 + 50
                        # Convert pixels to inches: use even larger conversion factor to further condense plot
                        plot_height_inches = table_height_pixels / 140  # Increased from 120 to 140 to further condense
                        # Cap at reasonable min/max values - further reduced max
                        plot_height_inches = max(3.5, min(7, plot_height_inches))
                        
                        matchup_fig.set_size_inches(9, plot_height_inches)  # Further reduced width from 10 to 9 inches
                        matchup_fig.set_dpi(100)  # Ensure consistent DPI across environments
                        # Reapply subplots_adjust after resizing - further condensed margins
                        matchup_fig.subplots_adjust(left=0.20, top=0.90, bottom=0.14, right=0.95)
                        
                        # Display plot with title (labels are now integrated in matplotlib)
                        # Title uses the home/away assignments to show correct matchup
                        st.markdown(f"<h2 style='text-align: center; margin-bottom: 1rem; font-size: 32px;'>{away_team} @ {home_team}<br>Points Scored vs Points Allowed by Condition</h2>", unsafe_allow_html=True)
                        st.pyplot(matchup_fig, use_container_width=False)  # Don't scale to container width
                        
                        plt.close(matchup_fig)
    else:
        st.warning(f"No players found for team {st.session_state.selected_team}")