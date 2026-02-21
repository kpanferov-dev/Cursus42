from typing import Dict, Any, List
from .TournamentCard import TournamentCard


class TournamentPlatform:
    """
    Platform management system for card tournaments
    """

    def __init__(self, name: str = "DataDeck Tournament"):
        """
        Initialize the tournament platform

        Args:
            name: Platform name
        """
        self.name = name
        self.registered_cards: Dict[str, TournamentCard] = {}
        self.match_history: List[Dict[str, Any]] = []
        self.total_matches = 0
        self.platform_status = "active"

    def register_card(self, card: TournamentCard) -> str:
        """
        Register a card in the tournament platform

        Args:
            card: TournamentCard to register

        Returns:
            str: Card ID
        """
        if not isinstance(card, TournamentCard):
            raise TypeError("Only TournamentCard instances can be registered")

        if not card.card_id:
            card.card_id = (
                            f"{card.name.lower().replace(' ', '_')}_"
                            f"{len(self.registered_cards) + 1:03d}"
            )

        self.registered_cards[card.card_id] = card

        print(f"\n{card.name} (ID: {card.card_id}):")
        print(f"- Interfaces: {card.get_tournament_stats()['interfaces']}")
        print(f"- Rating: {card.rating}")
        print(f"- Record: {card.wins}-{card.losses}")

        return card.card_id

    def create_match(self, card1_id: str, card2_id: str) -> Dict[str, Any]:
        """
        Create a match between two registered cards

        Args:
            card1_id: ID of first card
            card2_id: ID of second card

        Returns:
            Dictionary with match results
        """
        if card1_id not in self.registered_cards:
            raise ValueError(f"Card ID '{card1_id}' not registered")

        if card2_id not in self.registered_cards:
            raise ValueError(f"Card ID '{card2_id}' not registered")

        card1 = self.registered_cards[card1_id]
        card2 = self.registered_cards[card2_id]

        # Simulate match
        card1.health = card1.max_health
        card2.health = card2.max_health
        card1.in_play = True
        card2.in_play = True

        turn = 1
        while card1.health > 0 and card2.health > 0:
            if turn % 2 == 1:
                card1.attack(card2)
            else:
                card2.attack(card1)
            turn += 1

        if card1.health > 0:
            winner, loser = card1, card2
        else:
            winner, loser = card2, card1

        card1.in_play = False
        card2.in_play = False

        # Update stats
        winner.update_wins(1)
        loser.update_losses(1)

        # Record match
        match_result = {
            "match_id": f"match_{self.total_matches + 1:03d}",
            "card1_id": card1_id,
            "card1_name": card1.name,
            "card2_id": card2_id,
            "card2_name": card2.name,
            "winner_id": winner.card_id,
            "winner_name": winner.name,
            "loser_id": loser.card_id,
            "loser_name": loser.name
        }

        self.match_history.append(match_result)
        self.total_matches += 1

        return {
            "winner": winner.card_id,
            "loser": loser.card_id,
            "winner_rating": winner.rating,
            "loser_rating": loser.rating
        }

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        """
        Get tournament leaderboard sorted by rating

        Returns:
            List of card rankings
        """
        if not self.registered_cards:
            return []

        # Sort cards by rating (highest first)
        sorted_cards = sorted(
            self.registered_cards.values(),
            key=lambda c: c.rating,
            reverse=True
        )

        leaderboard = []
        for i, card in enumerate(sorted_cards, 1):
            leaderboard.append({
                "rank": i,
                "card_id": card.card_id,
                "name": card.name,
                "rating": card.rating,
                "wins": card.wins,
                "losses": card.losses,
                "record": f"{card.wins}-{card.losses}"
            })

        return leaderboard

    def generate_tournament_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive tournament report

        Returns:
            Dictionary with tournament statistics
        """
        total_cards = len(self.registered_cards)

        if total_cards == 0:
            return {
                "total_cards": 0,
                "matches_played": self.total_matches,
                "avg_rating": 0,
                "platform_status": self.platform_status,
                "platform_name": self.name
            }

        total_rating = sum(c.rating for c in self.registered_cards.values())
        avg_rating = total_rating // total_cards

        return {
            "total_cards": total_cards,
            "matches_played": self.total_matches,
            "avg_rating": avg_rating,
            "platform_status": self.platform_status,
        }
