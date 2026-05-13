def get_teammate_game_ids(pbs, teammate_id, player_game_ids):
    """
    Returns the set of game_ids (from player_game_ids) where the specified
    teammate appeared in the box score.

    Parameters
    ----------
    pbs : pd.DataFrame
        Full player box scores dataframe (all players on the team).
    teammate_id : int or str
        personId (int) or familyName (str) of the teammate.
    player_game_ids : set
        Set of game_ids played by the focal player.

    Returns
    -------
    set
        game_ids in player_game_ids where the teammate appeared.
    """
    pbs_names = pbs.copy()
    pbs_names["firstName"] = pbs_names["firstName"].str.lower()
    pbs_names["familyName"] = pbs_names["familyName"].str.lower()

    if isinstance(teammate_id, str):
        return set(
            pbs_names[
                (pbs_names["familyName"] == teammate_id.lower()) &
                (pbs_names["game_id"].isin(player_game_ids))
            ]["game_id"]
        )
    else:
        return set(
            pbs_names[
                (pbs_names["personId"] == teammate_id) &
                (pbs_names["game_id"].isin(player_game_ids))
            ]["game_id"]
        )
