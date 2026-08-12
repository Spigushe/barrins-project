import pandas as pd
import pytest

from karn_tablets.features import (
    build_deck_analytical_features,
    classify_functions,
    count_mana_pips,
    encode_card_features,
    flatten_features_dict,
)


class TestClassifyFunctions:
    def test_none_and_empty_return_other(self):
        assert classify_functions(None) == ["Other"]
        assert classify_functions("") == ["Other"]

    def test_nan_float_tolerated(self):
        assert classify_functions(float("nan")) == ["Other"]

    def test_removal_matches_exile_target(self):
        assert "Removal" in classify_functions("Exile target creature.")

    def test_removal_matches_damage_to_any_target(self):
        text = "Lightning Bolt deals 3 damage to any target."
        assert "Removal" in classify_functions(text)

    def test_card_draw_matches_draw_two_cards(self):
        assert "Card Draw" in classify_functions("Draw two cards.")

    def test_board_wipe_matches_destroy_all_creatures(self):
        assert "Board Wipe" in classify_functions("Destroy all creatures.")

    def test_a_card_can_match_multiple_categories(self):
        text = "Destroy target creature. Draw a card."
        result = classify_functions(text)
        assert "Removal" in result
        assert "Card Draw" in result

    def test_no_match_returns_other(self):
        assert classify_functions("This creature has no relevant text.") == ["Other"]


class TestCountManaPips:
    def test_empty_or_none_returns_all_zero(self):
        pips = count_mana_pips(None)
        assert pips == {"W": 0.0, "U": 0.0, "B": 0.0, "R": 0.0, "G": 0.0, "C": 0.0}

    def test_simple_colored_and_generic(self):
        pips = count_mana_pips("{1}{W}{U}")
        assert pips["W"] == 1.0
        assert pips["U"] == 1.0
        assert pips["C"] == 1.0

    def test_hybrid_splits_evenly(self):
        pips = count_mana_pips("{W/U}")
        assert pips["W"] == 0.5
        assert pips["U"] == 0.5

    def test_phyrexian_counts_as_full_colored_pip(self):
        pips = count_mana_pips("{W/P}")
        assert pips["W"] == 1.0

    def test_qty_multiplies_every_pip(self):
        pips = count_mana_pips("{1}{W}", qty=4)
        assert pips["W"] == 4.0
        assert pips["C"] == 4.0

    def test_x_cost_counts_as_generic(self):
        pips = count_mana_pips("{X}{R}")
        assert pips["C"] == 1.0
        assert pips["R"] == 1.0


class TestEncodeCardFeatures:
    def test_lightning_bolt_is_flagged_removal(self, cards_df: pd.DataFrame):
        row = cards_df[cards_df["name"] == "Lightning Bolt"].iloc[0]
        feats = encode_card_features(row)
        assert feats["_fn_removal"] == 1
        assert feats["color_R"] == 1
        assert feats["mana_value"] == 1.0

    def test_land_has_no_colors_and_zero_mana_value(self, cards_df: pd.DataFrame):
        row = cards_df[cards_df["name"] == "Plains"].iloc[0]
        feats = encode_card_features(row)
        assert feats["is_colorless"] == 1
        assert feats["type_land"] == 1
        assert feats["mana_value"] == 0.0

    def test_creature_power_toughness_parsed(self, cards_df: pd.DataFrame):
        row = cards_df[cards_df["name"] == "Grizzly Bears"].iloc[0]
        feats = encode_card_features(row)
        assert feats["power"] == 2.0
        assert feats["toughness"] == 2.0

    def test_missing_power_toughness_is_negative_one(self, cards_df: pd.DataFrame):
        row = cards_df[cards_df["name"] == "Sol Ring"].iloc[0]
        feats = encode_card_features(row)
        assert feats["power"] == -1.0
        assert feats["toughness"] == -1.0


class TestFlattenFeaturesDict:
    def test_produces_one_row_per_deck(
        self, deck_cards_df: pd.DataFrame, cards_df: pd.DataFrame
    ):
        result = flatten_features_dict(deck_cards_df, cards_df)
        assert set(result["deck_id"]) == {"deck-1", "deck-2", "deck-3"}

    def test_removal_signal_matches_expected_weighted_average(
        self, deck_cards_df: pd.DataFrame, cards_df: pd.DataFrame
    ):
        result = flatten_features_dict(deck_cards_df, cards_df).set_index("deck_id")
        # deck-1: 4 Lightning Bolt (removal) out of 19 total cards.
        assert result.loc["deck-1", "_fn_removal"] == pytest.approx(4 / 19, abs=0.001)
        # deck-3: 4 Swords to Plowshares (removal) out of 27 total cards
        # (includes its 1-card sideboard row -- flatten_features_dict
        # doesn't filter zones, that's the caller's job).
        assert result.loc["deck-3", "_fn_removal"] == pytest.approx(4 / 27, abs=0.001)


class TestBuildDeckAnalyticalFeatures:
    def test_returns_51_features_plus_deck_id(
        self, deck_cards_df: pd.DataFrame, cards_df: pd.DataFrame
    ):
        result = build_deck_analytical_features(deck_cards_df, cards_df)
        assert len(result) == 3
        assert result.shape[1] == 52  # deck_id + 51 features

    def test_empty_mainboard_returns_empty_frame(self, cards_df: pd.DataFrame):
        sideboard_only = pd.DataFrame(
            [
                {
                    "deck_id": "d",
                    "card_uuid": "sol-ring",
                    "count": 1,
                    "is_sideboard": True,
                }
            ]
        )
        result = build_deck_analytical_features(sideboard_only, cards_df)
        assert result.empty

    def test_control_deck_has_higher_land_ratio_than_aggro(
        self, deck_cards_df: pd.DataFrame, cards_df: pd.DataFrame
    ):
        result = build_deck_analytical_features(deck_cards_df, cards_df).set_index(
            "deck_id"
        )
        assert result.loc["deck-3", "land_ratio"] > result.loc["deck-1", "land_ratio"]
