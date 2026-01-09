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
