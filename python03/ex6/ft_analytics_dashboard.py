"""
Docstring for python03.ex6.ft_analytics_dashboard
"""


def player_key(player):
    return (player["score"], player["achievements"])


def main():
    """Main"""
    print("=== Game Analytics Dashboard ===")

    players = [
        {"name": "alice", "score": 2300, "achievements": 5,
         "active": True, "region": "north"},
        {"name": "bob", "score": 1800, "achievements": 3,
         "active": True, "region": "east"},
        {"name": "charlie", "score": 2150, "achievements": 7,
         "active": True, "region": "central"},
        {"name": "diana", "score": 2050, "achievements": 2,
         "active": False, "region": "north"}
    ]

    achievements = [
        {"achievement": "first_kill", "player": "alice"},
        {"achievement": "level_10", "player": "bob"},
        {"achievement": "boss_slayer", "player": "charlie"},
        {"achievement": "first_kill", "player": "diana"},
        {"achievement": "level_10", "player": "alice"},
        {"achievement": "boss_slayer", "player": "bob"}
    ]

    print("\n=== List Comprehension Examples ===")

    high_scorers = [
        player["name"] for player in players if player["score"] > 2000
    ]
    print("High scorers (>2000):", high_scorers)

    scores_doubled = [player["score"] * 2 for player in players]
    print("Scores doubled:", scores_doubled)

    active_players = [player["name"] for player in players if player["active"]]
    print("Active players:", active_players)

    print("\n=== Dict Comprehension Examples ===")
    player_scores = {player["name"]: player["score"] for player in players}
    print("Player scores:", player_scores)

    score_categories = {
        "high": sum(1 for player in players if player["score"] > 2000),
        "medium": sum(
            1 for player in players if 1500 <= player["score"] <= 2000),
        "low": sum(1 for player in players if player["score"] < 1500)
    }
    print("Score categories:", score_categories)

    achievement_counts = {
        player["name"]: sum(
            1 for ach in achievements if ach["player"] == player["name"])
        for player in players
    }
    print("Achievement counts:", achievement_counts)

    print("\n=== Set Comprehension Examples ===")
    unique_players = {player["name"] for player in players}
    print("Unique players:", unique_players)

    unique_achievements = {ach["achievement"] for ach in achievements}
    print("Unique achievements:", unique_achievements)

    active_regions = {
        player["region"] for player in players if player["active"]}
    print("Active regions:", active_regions)

    print("\n=== Combined Analysis ===")

    total_players = len(unique_players)
    print("Total players:", total_players)

    total_unique_achievements = len(unique_achievements)
    print("Total unique achievements:", total_unique_achievements)

    average_score = sum(player["score"] for player in players) / len(players)
    print("Average score:", average_score)

    top_player = max(players, key=player_key)
    print(
        f"Top performer: {top_player['name']} " +
        f"({top_player['score']} points, " +
        f"{top_player['achievements']} achievements)"
    )


if __name__ == "__main__":
    main()
