import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from data import load_process_pbs, load_process_tbs, build_ranks
from plots.player import plot_player_scoring, plot_player_team_points_overlap, plot_player_pct_team_points
from plots.team import plot_team_points_scored, plot_team_points_allowed
from tables import player_hit_rate_summary

st.set_page_config(
    page_title="NBA Player Prop Dashboard",
    layout="wide"
)

# Custom CSS to reduce spacing and make everything fit on screen
st.markdown("""
    <style>
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    h3 {
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .stDataFrame {
        margin-bottom: 0.5rem;
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

def render_game_dashboard(player_id, prop_line, away_team, home_team, pbs, tbs, daily_ranks, teammate_ids=None):
    """
    Render the complete game dashboard with header and three-column layout.
    
    Parameters:
    -----------
    player_id : int
        Player personId to analyze
    prop_line : float
        Prop line threshold
    away_team : str
        Away team abbreviation (e.g., "LAL")
    home_team : str
        Home team abbreviation (e.g., "NOP")
    pbs : pd.DataFrame
        Player box scores
    tbs : pd.DataFrame
        Team box scores
    daily_ranks : pd.DataFrame
        Daily rankings
    teammate_ids : list, optional
        Teammate identifiers for tracking
    """
    
    # Get player info
    player_info = pbs[pbs["personId"] == player_id].iloc[0]
    player_team = player_info["teamTricode"]
    
    # Get full team names
    away_team_name = get_team_full_name(away_team)
    home_team_name = get_team_full_name(home_team)
    player_team_name = get_team_full_name(player_team)
    
    # Determine opponent team
    if player_team == away_team:
        opp_team = home_team
    else:
        opp_team = away_team
    opp_team_name = get_team_full_name(opp_team)
    
    # =========================================================
    # CONDENSED TOP HEADER: Game Context
    # =========================================================
    
    # Compact header with three columns
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        st.markdown(f"**{away_team_name}**")
        # Placeholder lineup (compact)
        lineup_text = " | ".join([f"Player {i+1}" for i in range(5)])
        st.markdown(f"<small>{lineup_text}</small>", unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"**{away_team} @ {home_team}**")
        st.markdown("<small>**Total:** TBD | **Spread:** TBD</small>", unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"**{home_team_name}**")
        # Placeholder lineup (compact)
        lineup_text = " | ".join([f"Player {i+1}" for i in range(5)])
        st.markdown(f"<small>{lineup_text}</small>", unsafe_allow_html=True)
    
    # =========================================================
    # THREE COLUMN LAYOUT
    # =========================================================
    
    left_col, middle_col, right_col = st.columns([1, 1, 1])
    
    # Helper function to resize plots
    def resize_figure(fig, width=18, height=7):
        """Resize matplotlib figure for larger display."""
        fig.set_size_inches(width, height)
        fig.tight_layout()
        return fig
    
    # =========================================================
    # LEFT COLUMN: Player's Team
    # =========================================================
    
    with left_col:
        st.markdown(f"**{player_team_name}**")
        
        # Top: Team points scored plot
        team_pts_fig, _ = plot_team_points_scored(player_team, tbs, daily_ranks)
        team_pts_fig = resize_figure(team_pts_fig, width=6, height=4.5)
        st.pyplot(team_pts_fig, use_container_width=True)
        plt.close(team_pts_fig)
        
        # Bottom: Player % of team points plot
        player_pct_fig, _ = plot_player_pct_team_points(player_id, pbs, tbs, daily_ranks, teammate_ids)
        player_pct_fig = resize_figure(player_pct_fig, width=6, height=4.5)
        st.pyplot(player_pct_fig, use_container_width=True)
        plt.close(player_pct_fig)
    
    # =========================================================
    # MIDDLE COLUMN: Player Analysis
    # =========================================================
    
    with middle_col:
        player_name = f"{player_info['firstName']} {player_info['familyName']}"
        st.markdown(f"**{player_name}**")
        
        # Top: Hit rate summary table (compact)
        summary_table = player_hit_rate_summary(player_id, prop_line, pbs, tbs, daily_ranks, teammates=teammate_ids)
        st.dataframe(summary_table, use_container_width=True, hide_index=True, height=180)
        
        # Bottom: Player scoring plot
        player_scoring_fig, _ = plot_player_scoring(player_id, prop_line, pbs, tbs, daily_ranks, teammate_ids)
        player_scoring_fig = resize_figure(player_scoring_fig, width=6, height=5.5)
        st.pyplot(player_scoring_fig, use_container_width=True)
        plt.close(player_scoring_fig)
    
    # =========================================================
    # RIGHT COLUMN: Opponent Team
    # =========================================================
    
    with right_col:
        st.markdown(f"**{opp_team_name}**")
        
        # Top: Opponent points allowed plot
        opp_pts_fig, _ = plot_team_points_allowed(opp_team, tbs, daily_ranks)
        opp_pts_fig = resize_figure(opp_pts_fig, width=6, height=4.5)
        st.pyplot(opp_pts_fig, use_container_width=True)
        plt.close(opp_pts_fig)
        
        # Bottom: Player vs team points overlap plot
        overlap_fig, _ = plot_player_team_points_overlap(player_id, pbs, tbs, daily_ranks, teammate_ids)
        overlap_fig = resize_figure(overlap_fig, width=6, height=4.5)
        st.pyplot(overlap_fig, use_container_width=True)
        plt.close(overlap_fig)

# =========================================================
# MAIN APP
# =========================================================

pbs = load_process_pbs()
tbs = load_process_tbs()
daily_ranks = build_ranks(tbs)

# Example usage - Luka Dončić (LAL) @ NOP
render_game_dashboard(
    player_id=1629029,
    prop_line=29.5,
    away_team="LAL",
    home_team="NOP",
    pbs=pbs,
    tbs=tbs,
    daily_ranks=daily_ranks,
    teammate_ids=[1630559, 2544]  # Reaves and LeBron
)