"""Shared fixtures: a small, real-shaped card pool and deck-card rows,
matching `extract.load_cards_features()`/`load_deck_cards()`'s output
shape -- used by feature/clustering/aggregation tests without a real
database connection.
"""

import pandas as pd
import pytest

_CARDS = [
    {
        "uuid": "sol-ring",
        "name": "Sol Ring",
        "mana_value": 1.0,
        "colors": [],
        "color_identity": [],
        "types": ["Artifact"],
        "subtypes": [],
        "supertypes": [],
        "keywords": [],
        "rarity": "uncommon",
        "power": None,
        "toughness": None,
        "loyalty": None,
        "text": "{T}: Add {C}{C}.",
        "mana_cost": "{1}",
        "type_line": "Artifact",
    },
    {
        "uuid": "swords-to-plowshares",
        "name": "Swords to Plowshares",
        "mana_value": 1.0,
        "colors": ["W"],
        "color_identity": ["W"],
        "types": ["Instant"],
        "subtypes": [],
        "supertypes": [],
        "keywords": [],
        "rarity": "uncommon",
        "power": None,
        "toughness": None,
        "loyalty": None,
        "text": "Exile target creature. Its controller gains life.",
        "mana_cost": "{W}",
        "type_line": "Instant",
    },
    {
        "uuid": "lightning-bolt",
        "name": "Lightning Bolt",
        "mana_value": 1.0,
        "colors": ["R"],
        "color_identity": ["R"],
        "types": ["Instant"],
        "subtypes": [],
        "supertypes": [],
        "keywords": [],
        "rarity": "common",
        "power": None,
        "toughness": None,
        "loyalty": None,
        "text": "Lightning Bolt deals 3 damage to any target.",
        "mana_cost": "{R}",
        "type_line": "Instant",
    },
    {
        "uuid": "plains",
        "name": "Plains",
        "mana_value": 0.0,
        "colors": [],
        "color_identity": [],
        "types": ["Land"],
        "subtypes": ["Plains"],
        "supertypes": ["Basic"],
        "keywords": [],
        "rarity": "common",
        "power": None,
        "toughness": None,
        "loyalty": None,
        "text": None,
        "mana_cost": None,
        "type_line": "Basic Land — Plains",
    },
    {
        "uuid": "grizzly-bears",
        "name": "Grizzly Bears",
        "mana_value": 2.0,
        "colors": ["G"],
        "color_identity": ["G"],
        "types": ["Creature"],
        "subtypes": ["Bear"],
        "supertypes": [],
        "keywords": [],
        "rarity": "common",
        "power": "2",
        "toughness": "2",
        "loyalty": None,
        "text": None,
        "mana_cost": "{1}{G}",
        "type_line": "Creature — Bear",
    },
    {
        "uuid": "divination",
        "name": "Divination",
        "mana_value": 3.0,
        "colors": ["U"],
        "color_identity": ["U"],
        "types": ["Sorcery"],
        "subtypes": [],
        "supertypes": [],
        "keywords": [],
        "rarity": "common",
        "power": None,
        "toughness": None,
        "loyalty": None,
        "text": "Draw two cards.",
        "mana_cost": "{2}{U}",
        "type_line": "Sorcery",
    },
]


@pytest.fixture()
def cards_df() -> pd.DataFrame:
    return pd.DataFrame(_CARDS)


def _deck_row(deck_id: str, card_uuid: str, count: int, is_sideboard: bool = False):
    return {
        "deck_id": deck_id,
        "card_uuid": card_uuid,
        "count": count,
        "is_sideboard": is_sideboard,
    }


@pytest.fixture()
def deck_cards_df() -> pd.DataFrame:
    """Three small decks sharing enough structure to cluster meaningfully:
    two "aggro" decks (Lightning Bolt-heavy, low curve) and one
    "control" deck (Divination, higher curve, more lands).
    """
    rows = [
        # deck-1: aggro-ish
        _deck_row("deck-1", "lightning-bolt", 4),
        _deck_row("deck-1", "sol-ring", 1),
        _deck_row("deck-1", "plains", 10),
        _deck_row("deck-1", "grizzly-bears", 4),
        # deck-2: aggro-ish (similar to deck-1)
        _deck_row("deck-2", "lightning-bolt", 4),
        _deck_row("deck-2", "sol-ring", 1),
        _deck_row("deck-2", "plains", 9),
        _deck_row("deck-2", "grizzly-bears", 3),
        # deck-3: control-ish (different shape)
        _deck_row("deck-3", "divination", 4),
        _deck_row("deck-3", "swords-to-plowshares", 4),
        _deck_row("deck-3", "plains", 18),
        _deck_row("deck-3", "sol-ring", 1, is_sideboard=True),
    ]
    return pd.DataFrame(rows)
