STATS = {
    "points":              {"column": "points",              "label": "Points",         "short": "PTS",  "default_line": 29.5, "computed": False},
    "rebounds_total":      {"column": "rebounds_total",      "label": "Rebounds",       "short": "REB",  "default_line": 7.5,  "computed": False},
    "rebounds_offensive":  {"column": "rebounds_offensive",  "label": "Off Rebounds",   "short": "OREB", "default_line": 1.5,  "computed": False},
    "rebounds_defensive":  {"column": "rebounds_defensive",  "label": "Def Rebounds",   "short": "DREB", "default_line": 5.5,  "computed": False},
    "assists":             {"column": "assists",             "label": "Assists",        "short": "AST",  "default_line": 6.5,  "computed": False},
    "three_pointers_made": {"column": "three_pointers_made", "label": "3-Pointers Made","short": "3PM",  "default_line": 2.5,  "computed": False},
    "steals":              {"column": "steals",              "label": "Steals",         "short": "STL",  "default_line": 1.5,  "computed": False},
    "blocks":              {"column": "blocks",              "label": "Blocks",         "short": "BLK",  "default_line": 1.5,  "computed": False},
    "turnovers":           {"column": "turnovers",           "label": "Turnovers",      "short": "TO",   "default_line": 2.5,  "computed": False},
    "pra":                 {"column": "pra",                 "label": "PRA",            "short": "PRA",  "default_line": 44.5, "computed": True},
    "pr":                  {"column": "pr",                  "label": "PR",             "short": "PR",   "default_line": 37.5, "computed": True},
    "pa":                  {"column": "pa",                  "label": "PA",             "short": "PA",   "default_line": 37.5, "computed": True},
    "ra":                  {"column": "ra",                  "label": "RA",             "short": "RA",   "default_line": 14.5, "computed": True},
}

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

DEFAULT_PROP_LINE = 29.5

DEF_BUCKET_TOP = 10     # rank 1–10  → "Top 10 Defense"
DEF_BUCKET_MIDDLE = 20  # rank 11–20 → "Middle 10 Defense"
                        # rank 21+   → "Bottom 10 Defense"
