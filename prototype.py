import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from data import load_process_pbs, load_process_tbs, build_ranks
from plots.player import plot_player_scoring
from plots.opp import plot_team_points_allowed

st.set_page_config(
    page_title="NBA Player Prop Dashboard",
    layout="wide"
)

st.title("NBA Player Prop Dashboard")
st.caption("Prototype — single-game decision support")

pbs = load_process_pbs()
tbs = load_process_tbs()
daily_ranks = build_ranks(tbs)

st.info("Data loaded successfully. UI scaffolding in progress.")

player_scoring = plot_player_scoring(1629029, 29.5, pbs, tbs, daily_ranks, [1630559, 2544])
st.pyplot(player_scoring[0])

opp_pts_allowed = plot_team_points_allowed("NOP", tbs, daily_ranks)
st.pyplot(opp_pts_allowed[0])
