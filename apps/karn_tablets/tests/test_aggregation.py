from karn_tablets.aggregation import aggregate_decks
from karn_tablets.schemas import Decklist


class TestAggregateDecks:
    def test_empty_input_returns_none(self):
        assert aggregate_decks([]) is None

    def test_cards_in_every_deck_survive_aggregation(self):
        decks = [
            Decklist(mainboard={"Sol Ring": 1, "Lightning Bolt": 4}),
            Decklist(mainboard={"Sol Ring": 1, "Lightning Bolt": 4}),
            Decklist(mainboard={"Sol Ring": 1, "Lightning Bolt": 4}),
        ]
        result = aggregate_decks(decks)
        assert result is not None
        assert result.decklist.mainboard["Sol Ring"] == 1
        assert result.decklist.mainboard["Lightning Bolt"] == 4

    def test_mainboard_size_targets_the_modal_deck_size(self):
        # Two decks of size 5, one of size 3 -- mode is 5.
        decks = [
            Decklist(mainboard={f"Card {i}": 1 for i in range(5)}),
            Decklist(mainboard={f"Card {i}": 1 for i in range(5, 10)}),
            Decklist(mainboard={f"Card {i}": 1 for i in range(10, 13)}),
        ]
        result = aggregate_decks(decks)
        assert result is not None
        assert sum(result.decklist.mainboard.values()) <= 5

    def test_limit_caps_the_number_of_decks_considered(self):
        decks = [Decklist(mainboard={"Sol Ring": 1}) for _ in range(200)]
        result = aggregate_decks(decks, limit=10)
        assert result is not None
        assert len(result.decks) == 10

    def test_empty_sideboards_fall_back_to_empty_aggregate(self):
        decks = [Decklist(mainboard={"Sol Ring": 1}) for _ in range(3)]
        result = aggregate_decks(decks)
        assert result is not None
        assert result.decklist.sideboard == {}

    def test_order_and_frequency_threshold_are_recorded(self):
        decks = [Decklist(mainboard={"Sol Ring": 1}) for _ in range(3)]
        result = aggregate_decks(decks, order=2)
        assert result is not None
        assert result.order == 2
        assert result.frequency_threshold == -1
