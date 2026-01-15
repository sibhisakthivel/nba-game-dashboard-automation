import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from data import load_process_pbs, load_process_tbs, build_ranks
from plots.player import plot_player_scoring, plot_player_scoring_by_def_bucket
from tables import player_hit_rate_summary

import os
import streamlit as st
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

import pandas as pd

test_df = pd.read_sql("SELECT 1 AS ok", engine)
st.write(test_df)

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

def render_game_dashboard(player_id, prop_line, away_team, home_team, opp_def_bucket, pbs, tbs, daily_ranks, teammate_ids=None):
    """
    Render the complete game dashboard with 4-section layout.
    
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
    opp_def_bucket : str
        Opponent defensive bucket (e.g., "top10", "middle10", "bottom10")
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
    
    # Get full team names
    away_team_name = get_team_full_name(away_team)
    home_team_name = get_team_full_name(home_team)
    
    # =========================================================
    # 2-COLUMN LAYOUT: Left (bigger) and Right (smaller)
    # =========================================================
    
    # Left column is bigger to accommodate the large player scoring plot
    col_left, col_right = st.columns([4, 2.5])
    
    # =========================================================
    # LEFT COLUMN: Top (Game Header) + Bottom (Player Scoring Plot)
    # =========================================================
    
    with col_left:
        # Top: Game Header - Centered matchup text at top
        st.markdown(f"<h2 style='text-align: center; margin-bottom: 0.5rem;'>{away_team_name} @ {home_team_name}</h2>", unsafe_allow_html=True)
        
        # Header with three sub-columns: away team (right-aligned), center (spread/total), home team (left-aligned)
        header_col1, header_col2, header_col3 = st.columns([2, 1, 2])
        
        with header_col1:
            # Away team lineup - centered
            st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
            # Starting lineup placeholder (5 lines) - directly under team name
            for i in range(5):
                st.markdown(f"<div style='text-align: center;'>Player {i+1}</div>", unsafe_allow_html=True)
            # Injuries placeholder (1 line, multiple players on same line) - centered
            st.markdown("<small style='text-align: center;'>Injuries: Player A, Player B</small>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        with header_col2:
            # Center: Game spread and total placeholder - centered under '@'
            st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
            st.markdown("**Total:** TBD")
            st.markdown("**Spread:** TBD")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with header_col3:
            # Home team lineup - centered
            st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
            # Starting lineup placeholder (5 lines) - directly under team name
            for i in range(5):
                st.markdown(f"<div style='text-align: center;'>Player {i+1}</div>", unsafe_allow_html=True)
            # Injuries placeholder (1 line, multiple players on same line) - centered
            st.markdown("<small style='text-align: center;'>Injuries: Player C</small>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Bottom: Player Scoring Plot (expanded to fill entire screen)
        player_scoring_fig, _ = plot_player_scoring(player_id, prop_line, pbs, tbs, daily_ranks, teammate_ids)
        # Use very large size to maximize screen usage
        player_scoring_fig.set_size_inches(28, 13)
        player_scoring_fig.tight_layout()
        st.pyplot(player_scoring_fig, use_container_width=True)
        plt.close(player_scoring_fig)
    
    # =========================================================
    # RIGHT COLUMN: Top (Opp Def Bucket Plot) + Bottom (Hit Rate Summary Table)
    # =========================================================
    
    with col_right:
        # Top: Opp Def Bucket Scoring Plot (expanded to fill screen)
        opp_bucket_fig, _ = plot_player_scoring_by_def_bucket(
            player_id, prop_line, pbs, tbs, daily_ranks, opp_def_bucket, teammate_ids
        )
        # Use larger size to maximize screen usage
        opp_bucket_fig.set_size_inches(20, 7)
        opp_bucket_fig.tight_layout()
        st.pyplot(opp_bucket_fig, use_container_width=True)
        plt.close(opp_bucket_fig)
        
        # Bottom: Hit Rate Summary Table (expanded to fill remaining space)
        summary_table = player_hit_rate_summary(player_id, prop_line, pbs, tbs, daily_ranks, teammates=teammate_ids)
        # Use height parameter to show all rows and fill remaining space
        st.dataframe(
            summary_table, 
            use_container_width=True, 
            hide_index=True,
            height=(len(summary_table) + 1) * 42 + 3  # Larger row height to fill space
        )

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
    opp_def_bucket="top10",  # Opponent defensive bucket
    pbs=pbs,
    tbs=tbs,
    daily_ranks=daily_ranks,
    teammate_ids=[1630559, 2544]  # Reaves and LeBron
)