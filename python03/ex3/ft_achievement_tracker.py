"""
ex3.ft_achievement_tracker
Learning how to use set
"""


def achievement_tracker(players):
    """Show players and achievments"""
    for player in players:
        print(f"Player {player[0]} achievments: {player[1]}")
    print()


def get_unique_achievements(players):
    """ Unique achievements of all players"""
    return set.union(*(p[1] for p in players))


def get_common_achievements(players):
    """Common achievements of all players"""
    return set.intersection(*(p[1] for p in players))


def get_rare_achievements(players):
    """Achievements which have been adquired by only one player"""
    unique_achievements = get_unique_achievements(players)
    rare_achievements = set()
    for achievement in unique_achievements:
        count = 0
        for player in players:
            if achievement in player[1]:
                count += 1
        if count == 1:
            rare_achievements.add(achievement)
    return rare_achievements


def get_player_achievements(players, player_name):
    """Get achievements of a player"""
    for player in players:
        if player[0] == player_name:
            player_achievements = player[1]
    return player_achievements


def get_com_ach_two_players(players, player1_name, player2_name):
    """Get common achievements of 2 players"""
    player1 = get_player_achievements(players, player1_name)
    player2 = get_player_achievements(players, player2_name)

    common_achievements = player1.intersection(player2)
    return common_achievements


def get_unique_ach_two_players(players, player1_name, player2_name):
    """Get unique achievements of first player"""
    player1 = get_player_achievements(players, player1_name)
    player2 = get_player_achievements(players, player2_name)

    unique_achievements = player1.difference(player2)
    return unique_achievements


def achievement_analytics(players):
    """Analyze players achievments"""

    unique_achievements = get_unique_achievements(players)
    print(f"All unique achievements: {unique_achievements}")
    print(f"Total unique achievements: {len(unique_achievements)}")
    print()

    common_achievements = get_common_achievements(players)
    print(f"Common to all players: {common_achievements}")
    rare_achievements = get_rare_achievements(players)
    print(f"Rare achievements (1 player): {rare_achievements}\n")

    alice_bob_common_achiev = get_com_ach_two_players(players, "alice", "bob")
    print(f"Alice vs Bob common: {alice_bob_common_achiev}")
    alice_unique_achiev = get_unique_ach_two_players(players, "alice", "bob")
    print(f"Alice unique: {alice_unique_achiev}")
    bob_unique_achiev = get_unique_ach_two_players(players, "bob", "alice")
    print(f"Bob unique: {bob_unique_achiev}")
