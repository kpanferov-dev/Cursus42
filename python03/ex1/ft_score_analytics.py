"""
ex1.ft_score_analytics
Lists and lists functions
"""


def score_cruncher():
    """Function that recieves arguments check if num
       save in list and use them to get important data
    """

    import sys

    print("=== Player Score Analytics ===")
    length = len(sys.argv)
    if length == 1:
        print("No scores provided. Usage:" +
              " python3 ft_score_analytics.py <score1> <score2> ...")
    else:
        scores = []
        for arg in sys.argv[1:]:
            try:
                number = int(arg)
                scores.append(number)
            except ValueError:
                pass

        total_players = len(scores)
        total_score = sum(scores)
        average_score = total_score / total_players
        high_score = max(scores)
        low_score = min(scores)
        score_range = high_score - low_score

        print(f"Scores processed: {scores}")
        print(f"Total players: {total_players}")
        print(f"Total score: {total_score}")
        print(f"Average score: {average_score:.1f}")
        print(f"High score: {high_score}")
        print(f"Low score: {low_score}")
        print(f"Score range: {score_range}")
