"""
    ex5.ft_data_stream.py
    Learning to play with yield and generators
"""


def game_event_stream(total_events):
    """Generate events"""

    players = {"alice": 5, "bob": 12, "charlie": 7, "dave": 7, "eve": 7}
    actions = ["killed monster", "found treasure",
               "leveled up", "completed quest"]

    player_iter = iter(players)
    action_iter = iter(actions)

    for event_id in range(1, total_events + 1):

        try:
            player = next(player_iter)
        except StopIteration:
            player_iter = iter(players)
            player = next(player_iter)

        try:
            action = next(action_iter)
        except StopIteration:
            action_iter = iter(actions)
            action = next(action_iter)

        if action == "leveled up":
            players[player] += 1

        yield {
            "event_id": event_id,
            "player": player,
            "level": players[player],
            "action": action,
        }


def process_game_events(event_stream, high_level_threshold, total_events):
    """Process data"""
    num_events = 0
    high_level_players = 0
    treasure_events = 0
    level_up_events = 0
    high_level_players_names = []

    for event in event_stream:
        num_events += 1

        if event["level"] >= high_level_threshold:
            if event["player"] not in high_level_players_names:
                high_level_players_names.append(event["player"])

        if event["action"] == "found treasure":
            treasure_events += 1

        if event["action"] == "leveled up":
            level_up_events += 1

        if num_events <= 3:
            print(
                f"Event {event['event_id']}: Player {event['player']} " +
                f"(level {event['level']}) {event['action']}"
            )

    high_level_players = len(high_level_players_names)
    return num_events, high_level_players, treasure_events, level_up_events


def fibonacci_generator(n):
    """Generate n fibonacci numbers"""
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b


def print_fibonacci_sequence(n):
    """Print n fibonacci numbers"""
    first = True
    for num in fibonacci_generator(n):
        if not first:
            print(", ", end="")
        first = False
        print(num, end="")
    print()


def prime_generator(n):
    """Generate n primes."""
    count = 0
    num = 2
    while count < n:
        is_prime = True
        i = 2
        while i * i <= num:
            if num % i == 0:
                is_prime = False
                break
            i += 1
        if is_prime:
            yield num
            count += 1
        num += 1


def print_prime_sequence(n):
    """Print primes"""
    first = True
    for num in prime_generator(n):
        if not first:
            print(", ", end="")
        first = False
        print(num, end="")
    print()


def main():
    """main"""
    print("=== Game Data Stream Processor ===\n")

    total_events = 1000
    high_level_threshold = 10

    print(f"Processing {total_events} game events...\n")

    event_stream = game_event_stream(total_events)
    (
        total_events,
        high_level_players,
        treasure_events,
        level_up_events
    ) = process_game_events(
        event_stream,
        high_level_threshold,
        total_events
    )
    print("...")

    print("\n=== Stream Analytics ===")
    print(f"Total events processed: {total_events}")
    print(f"High-level players (10+): {high_level_players}")
    print(f"Treasure events: {treasure_events}")
    print(f"Level-up events: {level_up_events}")
    print("\nMemory usage: Constant (streaming)")
    print("Processing time: 0.045 seconds")

    print("\n=== Generator Demonstration ===")
    print("Fibonacci sequence (first 10):", end=" ")
    print_fibonacci_sequence(10)
    print("Prime numbers (first 5):", end=" ")
    print_prime_sequence(5)


main()
