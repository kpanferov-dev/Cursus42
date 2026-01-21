"""
ex6.ft_analytics_dashboard
lists dicts and sets comprehensions
"""


def player_key(player):
    """get player key"""
    return (player["score"], player["achievements"])


def get_high_scorers(players):
    """get high scores"""
    return [p["name"] for p in players if p["score"] > 2000]


def get_doubled_scores(players):
    """doubles the scores"""
    return [p["score"] * 2 for p in players]


def get_active_players(players):
    """active players"""
    return [p["name"] for p in players if p["active"]]


def get_player_scores(players):
    """player scores"""
    return {p["name"]: p["score"] for p in players}


def get_score_categories(players):
    """return scores by category"""
    return {
        "high": sum(1 for p in players if p["score"] > 2000),
        "medium": sum(1 for p in players if 1500 <= p["score"] <= 2000),
        "low": sum(1 for p in players if p["score"] < 1500),
    }


def get_achievement_counts(players, achievements):
    """counts achievements """
    return {
        p["name"]: sum(1 for a in achievements if a["player"] == p["name"])
        for p in players
    }


def get_unique_players(players):
    """get unique players"""
    return {p["name"] for p in players}


def get_unique_achievements(achievements):
    """get unique achievements"""
    return {a["achievement"] for a in achievements}


def get_active_regions(players):
    """get active regions."""
    return {p["region"] for p in players if p["active"]}


def get_average_score(players):
    """get average scores"""
    return sum(p["score"] for p in players) / len(players)


def get_top_player(players):
    """get best player"""
    return max(players, key=player_key)


def show_list_comprehensions(players):
    """show lists info"""
    print("\n=== List Comprehension Examples ===")
    print("High scorers (>2000):", get_high_scorers(players))
    print("Scores doubled:", get_doubled_scores(players))
    print("Active players:", get_active_players(players))


def show_dict_comprehensions(players, achievements):
    """show dicts info"""
    print("\n=== Dict Comprehension Examples ===")
    print("Player scores:", get_player_scores(players))
    print("Score categories:", get_score_categories(players))
    print("Achievement counts:",
          get_achievement_counts(players, achievements))


def show_set_comprehensions(players, achievements):
    """show sets info"""
    print("\n=== Set Comprehension Examples ===")
    print("Unique players:", get_unique_players(players))
    print("Unique achievements:", get_unique_achievements(achievements))
    print("Active regions:", get_active_regions(players))


def show_combined_analysis(players, achievements):
    """show analysis"""
    print("\n=== Combined Analysis ===")
    print("Total players:", len(get_unique_players(players)))
    print("Total unique achievements:",
          len(get_unique_achievements(achievements)))
    print("Average score:", get_average_score(players))

    top_player = get_top_player(players)
    print(
        f"Top performer: {top_player['name']} "
        f"({top_player['score']} points, "
        f"{top_player['achievements']} achievements)"
    )
