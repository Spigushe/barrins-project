"""Per-deck feature vector construction from `extract.load_deck_cards()` +
`extract.load_cards_features()`.

Ported from the prior attempt at this
(`barrins-archive/barrins_api/app/services/ml/features.py`), which itself
ported the analytical-feature logic from an earlier spike
(`tst_deck_features`, github.com/barrins-project/tst_deck_features).
Column names already match this app's `extract.py` output (`card_uuid`,
`mana_value`, `colors`, `type_line`, `text`, ...) -- no schema-adaptation
changes needed beyond that.

Two feature vectors:

1. ``flatten_features_dict`` -- count-weighted average of intrinsic card
   features per deck. Feeds `clustering.clusterize`.
2. ``build_deck_analytical_features`` -- a 51-dimension analytical vector
   per deck (structure, mana curve shape, functional/text-derived
   signals, efficiency scores). Not wired into v1's clustering input
   directly (kept for a future iteration -- clustering runs on
   `flatten_features_dict`'s simpler vector for v1), but the functional
   classification it's built on (``classify_functions``) is reused by
   `flatten_features_dict` too, since that's the actual text-analysis
   capability this module exists to provide (T6).
"""

import re
from typing import Any

import numpy as np
import pandas as pd

# -- Feature-engineering constants -------------------------------------------

COLORS = ["W", "U", "B", "R", "G"]
CARD_TYPES = [
    "Creature",
    "Instant",
    "Sorcery",
    "Enchantment",
    "Artifact",
    "Planeswalker",
    "Land",
]
RARITY_ORD = {"common": 0, "uncommon": 1, "rare": 2, "mythic": 3}

_EPS = 0.001  # epsilon for safe division

# -- Functional classification patterns --------------------------------------
# Ported from tst_deck_features/js/analytics.js (oracle text: MTGJSON == Scryfall).

FUNCTION_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "Removal": [
        re.compile(r"destroy target", re.I),
        re.compile(r"exile target", re.I),
        re.compile(
            r"deals? \d+ damage to (any target|target creature|target planeswalker)",
            re.I,
        ),
        re.compile(r"target creature gets? [+\-]\d+/[+\-]\d+", re.I),
        re.compile(r"-\d+/-\d+ until", re.I),
        re.compile(r"destroy all", re.I),
        re.compile(r"exile all", re.I),
        re.compile(r"\bsacrifice\b", re.I),
        re.compile(r"\bfight\b", re.I),
        re.compile(r"\bdeathtouch\b", re.I),
    ],
    "Counterspell": [
        re.compile(r"counter target spell", re.I),
        re.compile(r"counter target activated", re.I),
        re.compile(r"counter target triggered", re.I),
        re.compile(r"counter it\b", re.I),
    ],
    "Card Draw": [
        re.compile(r"draw (a |one |two |three |\d+ )?cards?", re.I),
        re.compile(r"draws? (a |one |two |three |\d+ )?cards?", re.I),
        re.compile(r"look at the top", re.I),
        re.compile(r"reveal the top", re.I),
        re.compile(r"\bscry\b", re.I),
    ],
    "Ramp": [
        re.compile(r"search your library for a.*land", re.I),
        re.compile(r"add \{", re.I),
        re.compile(r"adds? (one|two|\d+) mana", re.I),
        re.compile(r"\{T\}: Add", re.I),
    ],
    "Tutor": [
        re.compile(r"search your library for a card", re.I),
        re.compile(r"search your library for an?\s", re.I),
    ],
    "Recursion": [
        re.compile(r"return.*from (your )?graveyard", re.I),
        re.compile(r"put.*from (your )?graveyard", re.I),
        re.compile(r"cast.*from (your )?graveyard", re.I),
        re.compile(r"\bflashback\b", re.I),
        re.compile(r"\bunearth\b", re.I),
        re.compile(r"\bescape\b", re.I),
    ],
    "Protection": [
        re.compile(r"\bhexproof\b", re.I),
        re.compile(r"\bshroud\b", re.I),
        re.compile(r"\bindestructible\b", re.I),
        re.compile(r"protection from", re.I),
        re.compile(r"prevent.*damage", re.I),
        re.compile(r"\bward\b", re.I),
    ],
    "Buff/Anthem": [
        re.compile(r"creatures you control get \+", re.I),
        re.compile(r"other creatures you control", re.I),
        re.compile(r"equipped creature gets", re.I),
        re.compile(r"enchanted creature gets", re.I),
    ],
    "Evasion": [
        re.compile(r"\bflying\b", re.I),
        re.compile(r"\btrample\b", re.I),
        re.compile(r"\bunblockable\b", re.I),
        re.compile(r"can't be blocked", re.I),
        re.compile(r"\bmenace\b", re.I),
        re.compile(r"\bshadow\b", re.I),
        re.compile(r"\bfear\b", re.I),
        re.compile(r"\bintimidation\b", re.I),
    ],
    "Token Generation": [
        re.compile(r"creates? .* token", re.I),
    ],
    "Discard": [
        re.compile(r"target (player|opponent) discards?", re.I),
        re.compile(r"each opponent discards?", re.I),
        re.compile(r"discard (a|their|two|three|\d+) card", re.I),
    ],
    "Life Gain": [
        re.compile(r"gains? \d+ life", re.I),
        re.compile(r"\blifelink\b", re.I),
    ],
    "Free Spell": [
        re.compile(r"without paying (its|their) mana cost", re.I),
        re.compile(r"you may pay \d+ life (rather|instead)", re.I),
        re.compile(r"rather than pay (this spell's|its) mana cost", re.I),
        re.compile(r"\bdash\b", re.I),
        re.compile(r"\bevoke\b", re.I),
        re.compile(r"you may pay 0 rather than", re.I),
    ],
    "Board Wipe": [
        re.compile(r"destroy all (creatures|nonland permanents|permanents)", re.I),
        re.compile(r"exile all (creatures|nonland permanents|permanents)", re.I),
        re.compile(r"each (\w+ )?creature gets -", re.I),
        re.compile(r"all (\w+ )?creatures get -", re.I),
        re.compile(r"deals? \d+ damage to each creature", re.I),
        re.compile(r"return all .* to (their|its) owner", re.I),
    ],
}

#: Internal column-name suffixes (`_fn_*`).
_FN_COLS: dict[str, str] = {
    "Removal": "_fn_removal",
    "Counterspell": "_fn_counterspell",
    "Card Draw": "_fn_card_draw",
    "Ramp": "_fn_ramp",
    "Tutor": "_fn_tutor",
    "Recursion": "_fn_recursion",
    "Board Wipe": "_fn_board_wipe",
    "Token Generation": "_fn_token_generation",
    "Discard": "_fn_discard",
    "Free Spell": "_fn_free_spell",
    "Buff/Anthem": "_fn_buff_anthem",
    "Life Gain": "_fn_life_gain",
    "Protection": "_fn_protection",
    "Evasion": "_fn_evasion",
}


# -- Helpers -------------------------------------------------------------------


def classify_functions(oracle_text: str | None) -> list[str]:
    """Classifies a card into one or more functional categories.

    Runs `FUNCTION_PATTERNS` against the oracle text (MTGJSON's `text`
    field). A card can belong to several categories. Returns `["Other"]`
    if nothing matches. Tolerates NaN (pandas float) values.
    """
    if not isinstance(oracle_text, str) or not oracle_text:
        return ["Other"]
    result = [
        cat
        for cat, patterns in FUNCTION_PATTERNS.items()
        if any(p.search(oracle_text) for p in patterns)
    ]
    return result if result else ["Other"]


def _parse_pt(v: Any) -> float:
    """Power/toughness/loyalty string -> float. '*', None, '', NaN -> -1.0.

    The NaN case matters in practice, not just for '*'-valued cards:
    `power`/`toughness`/`loyalty` are `None` for most non-creature cards,
    and a pandas column mixing `None` with numeric-looking strings often
    coerces those `None`s to `float('nan')` -- and `float(nan)` succeeds
    (returning `nan`) rather than raising, so the except clause alone
    doesn't catch it.
    """
    try:
        parsed = float(v)
    except TypeError, ValueError:
        return -1.0
    return -1.0 if np.isnan(parsed) else parsed


def count_mana_pips(mana_cost: str | None, qty: int = 1) -> dict[str, float]:
    """Counts colored mana pips from an MTGJSON/Scryfall mana-cost string.

    Format: ``{1}{W}{U}`` -> W: qty, U: qty, C: qty x 1.
    Hybrid: ``{W/U}`` -> W: qty x 0.5, U: qty x 0.5.
    Phyrexian: ``{W/P}`` -> W: qty.
    Generic numeric ``{3}`` -> C: qty x 3.

    Returns a `{W, U, B, R, G, C}` dict of pip totals.
    """
    pips: dict[str, float] = dict.fromkeys([*COLORS, "C"], 0.0)
    if not isinstance(mana_cost, str) or not mana_cost:
        return pips
    for sym in re.findall(r"\{([^}]+)\}", mana_cost):
        if re.match(r"^[WUBRG]$", sym):
            pips[sym] += qty
        elif re.match(r"^[WUBRG]/[WUBRG]$", sym):
            pips[sym[0]] += qty * 0.5
            pips[sym[2]] += qty * 0.5
        elif re.match(r"^[WUBRG]/P$", sym):
            pips[sym[0]] += qty
        elif re.match(r"^\d+$", sym):
            pips["C"] += qty * int(sym)
        elif sym in ("X", "C", "S"):
            pips["C"] += qty
    return pips


def _shannon_entropy(values: list[float]) -> float:
    """Shannon entropy (bits) of a distribution of counts."""
    total = sum(values)
    if total == 0:
        return 0.0
    entropy = 0.0
    for v in values:
        if v > 0:
            p = v / total
            entropy -= p * np.log2(p)
    return round(float(entropy), 4)


# -- Card-level encoding ---------------------------------------------------------


def encode_card_features(row: pd.Series) -> dict[str, float | int]:
    """Encodes one card into a numeric feature vector."""
    feats: dict[str, float | int] = {}
    feats["mana_value"] = float(row["mana_value"] or 0.0)

    colors = set(row["colors"] or [])
    for c in COLORS:
        feats[f"color_{c}"] = int(c in colors)
    feats["is_multicolor"] = int(len(colors) > 1)
    feats["is_colorless"] = int(len(colors) == 0)

    types = set(row["types"] or [])
    for t in CARD_TYPES:
        feats[f"type_{t.lower()}"] = int(t in types)

    feats["rarity_ord"] = RARITY_ORD.get(row["rarity"] or "", -1)
    feats["n_keywords"] = len(row["keywords"] or [])

    feats["power"] = _parse_pt(row["power"])
    feats["toughness"] = _parse_pt(row["toughness"])
    feats["loyalty"] = _parse_pt(row["loyalty"])

    fns = classify_functions(row.get("text"))
    for fn, col in _FN_COLS.items():
        feats[col] = int(fn in fns)
    return feats


# -- flatten_features_dict --------------------------------------------------------


def flatten_features_dict(
    df_deck_cards: pd.DataFrame,  # deck_id, card_uuid, count (mainboard only)
    df_cards: pd.DataFrame,  # extract.load_cards_features()'s output
) -> pd.DataFrame:
    """Builds a (n_decks x n_features) DataFrame.

    Each feature is the count-weighted average of every card's own
    feature in the deck:
        feature_deck = sum(count_i * feature_i) / total_cards
    """
    card_features = pd.DataFrame(
        [encode_card_features(row) for _, row in df_cards.iterrows()],
        index=df_cards["uuid"],
    )
    df = df_deck_cards.merge(
        card_features, left_on="card_uuid", right_index=True, how="left"
    ).fillna(0)

    numeric_cols = list(card_features.columns)
    for col in numeric_cols:
        df[col] = df[col] * df["count"]

    agg = (
        df.groupby("deck_id")[numeric_cols]
        .sum()
        .div(df.groupby("deck_id")["count"].sum(), axis=0)
    )
    return agg.reset_index()  # columns: deck_id + features


# -- 51-feature analytical vector (kept for a future iteration) ------------------


def _enrich_cards(df_cards: pd.DataFrame) -> pd.DataFrame:
    """Pre-computes per-card features once, before the per-deck loop.

    Adds internal `_is_*`, `_fn_*`, `_pip_*`, `_power_num`,
    `_toughness_num`, `_n_keywords`, `_cmc`, `_rarity_ord` columns on a
    copy of the cards DataFrame.
    """
    c = df_cards.copy()

    type_line = c["type_line"].fillna("")
    c["_is_land"] = type_line.str.contains("Land", regex=False)
    c["_is_creature"] = type_line.str.contains("Creature", regex=False)
    c["_is_instant"] = type_line.str.contains("Instant", regex=False)
    c["_is_sorcery"] = type_line.str.contains("Sorcery", regex=False)
    c["_is_enchantment"] = type_line.str.contains("Enchantment", regex=False)
    c["_is_artifact"] = type_line.str.contains("Artifact", regex=False)
    c["_is_planeswalker"] = type_line.str.contains("Planeswalker", regex=False)

    c["_cmc"] = c["mana_value"].fillna(0.0).astype(float)
    c["_power_num"] = c["power"].apply(_parse_pt)
    c["_toughness_num"] = c["toughness"].apply(_parse_pt)
    c["_n_keywords"] = c["keywords"].apply(
        lambda x: len(x) if isinstance(x, list) else 0
    )
    c["_rarity_ord"] = c["rarity"].apply(lambda r: RARITY_ORD.get(r or "", -1))
    colors_col = c["colors"].apply(lambda x: x if isinstance(x, list) else [])
    c["_is_multicolor"] = colors_col.apply(lambda x: len(x) > 1)
    c["_is_colorless_card"] = colors_col.apply(lambda x: len(x) == 0)

    funcs_series = c["text"].apply(classify_functions)
    for fn, col in _FN_COLS.items():
        c[col] = funcs_series.apply(lambda funcs, f=fn: f in funcs)

    def _pip_row(row: pd.Series) -> dict[str, float]:
        if row["_is_land"]:
            return dict.fromkeys([*COLORS, "C"], 0.0)
        return count_mana_pips(row.get("mana_cost"), 1)

    pips_series = c.apply(_pip_row, axis=1)
    for color in [*COLORS, "C"]:
        c[f"_pip_{color}"] = pips_series.apply(lambda p, col=color: p[col])

    return c


def _compute_deck_features(deck_id: str, grp: pd.DataFrame) -> dict[str, Any]:
    """Computes the 51-feature analytical vector for one deck (mainboard group)."""
    main_total = int(grp["count"].sum())
    if main_total == 0:
        return {"deck_id": deck_id}

    lands = grp[grp["_is_land"].fillna(False)]
    non_lands = grp[~grp["_is_land"].fillna(False)]
    land_total = int(lands["count"].sum())
    non_land_total = int(non_lands["count"].sum())

    unique_count = len(grp)
    singleton_count = int((grp["count"] == 1).sum())
    uniqueness = round(unique_count / main_total, 4)
    land_ratio = round(land_total / main_total, 4)
    singleton_ratio = round(singleton_count / max(unique_count, 1), 4)

    if len(non_lands) > 0:
        cmc_expanded = np.repeat(
            non_lands["_cmc"].fillna(0.0).to_numpy(),
            non_lands["count"].clip(lower=0).astype(int).to_numpy(),
        )
    else:
        cmc_expanded = np.array([], dtype=float)

    avg_cmc = float(np.mean(cmc_expanded)) if len(cmc_expanded) > 0 else 0.0
    expected_lands = round((19.59 + 1.90 * avg_cmc) * (main_total / 60), 1)
    karsten_land_delta = round(land_total - expected_lands, 1)

    mana_curve: dict[str, int] = {str(k): 0 for k in range(7)}
    mana_curve["7+"] = 0
    for _, row in non_lands.iterrows():
        cmc_val = int(min(row["_cmc"] or 0, 7))
        key = "7+" if cmc_val >= 7 else str(cmc_val)
        mana_curve[key] += int(row["count"])

    curve_values = list(mana_curve.values())
    max_bucket = max(curve_values) if curve_values else 0
    low_curve_count = mana_curve["0"] + mana_curve["1"] + mana_curve["2"]
    high_curve_count = mana_curve["5"] + mana_curve["6"] + mana_curve["7+"]
    top3_sum = sum(sorted(curve_values, reverse=True)[:3])

    curve_dominance_ratio = round(max_bucket / (non_land_total + _EPS), 4)
    low_curve_density = round(low_curve_count / (non_land_total + _EPS), 4)
    high_curve_density = round(high_curve_count / (non_land_total + _EPS), 4)
    curve_concentration_top3 = round(top3_sum / (non_land_total + _EPS), 4)

    if len(cmc_expanded) >= 2:
        cmc_variance = round(float(np.var(cmc_expanded)), 4)
        std = float(np.std(cmc_expanded))
        if len(cmc_expanded) >= 4 and std > 0:
            m4 = float(np.mean((cmc_expanded - avg_cmc) ** 4))
            cmc_kurtosis = round(m4 / (std**4) - 3, 4)  # excess kurtosis
        else:
            cmc_kurtosis = 0.0
    else:
        cmc_variance = 0.0
        cmc_kurtosis = 0.0

    modal_key = max(mana_curve, key=lambda k: mana_curve[k])
    modal_cmc = 7 if modal_key == "7+" else int(modal_key)

    pip_totals: dict[str, float] = dict.fromkeys([*COLORS, "C"], 0.0)
    for color in [*COLORS, "C"]:
        col = f"_pip_{color}"
        if col in grp.columns:  # pragma: no branch
            pip_totals[color] = float((grp[col].fillna(0.0) * grp["count"]).sum())
    total_pips = sum(pip_totals.values())
    norm_weighted = {
        c: round(pip_totals[c] / total_pips, 4) if total_pips > 0 else 0.0
        for c in [*COLORS, "C"]
    }

    def _fn_count(col: str, df: pd.DataFrame) -> int:
        if col not in df.columns:
            return 0
        return int(df[df[col].fillna(False)]["count"].sum())

    removal_count = _fn_count("_fn_removal", non_lands)
    counter_count = _fn_count("_fn_counterspell", non_lands)
    discard_count = _fn_count("_fn_discard", non_lands)
    draw_count = _fn_count("_fn_card_draw", non_lands)
    ramp_count = _fn_count("_fn_ramp", non_lands)
    tutor_count = _fn_count("_fn_tutor", non_lands)
    recursion_count = _fn_count("_fn_recursion", non_lands)
    board_wipe_count = _fn_count("_fn_board_wipe", non_lands)
    token_count = _fn_count("_fn_token_generation", non_lands)
    free_count = _fn_count("_fn_free_spell", non_lands)
    life_gain_count = _fn_count("_fn_life_gain", non_lands)
    protection_count = _fn_count("_fn_protection", non_lands)
    evasion_count = _fn_count("_fn_evasion", non_lands)

    creatures = non_lands[non_lands["_is_creature"].fillna(False)]
    creature_total = int(creatures["count"].sum())
    instant_total = int(
        non_lands[non_lands["_is_instant"].fillna(False)]["count"].sum()
    )
    sorcery_total = int(
        non_lands[non_lands["_is_sorcery"].fillna(False)]["count"].sum()
    )
    enchantment_total = int(
        non_lands[non_lands["_is_enchantment"].fillna(False)]["count"].sum()
    )
    artifact_total = int(
        non_lands[non_lands["_is_artifact"].fillna(False)]["count"].sum()
    )
    planeswalker_total = int(
        non_lands[non_lands["_is_planeswalker"].fillna(False)]["count"].sum()
    )

    interaction_density = round(
        (removal_count + counter_count + discard_count) / (non_land_total + _EPS), 4
    )

    # Threat creatures: excludes creatures that are pure removal (no
    # anthem/token upside of their own).
    is_pure_removal = (
        non_lands["_fn_removal"].fillna(False)
        & ~non_lands["_fn_token_generation"].fillna(False)
        & ~non_lands["_fn_buff_anthem"].fillna(False)
    )
    creature_removal_overlap = int(
        non_lands[non_lands["_is_creature"].fillna(False) & is_pure_removal][
            "count"
        ].sum()
    )
    threat_cards = creature_total - creature_removal_overlap + token_count
    threat_density = round(max(0.0, threat_cards) / (non_land_total + _EPS), 4)
    creature_density = round(creature_total / (non_land_total + _EPS), 4)
    combo_potential = round(
        (tutor_count + recursion_count + free_count) / (non_land_total + _EPS), 4
    )

    threat_to_interaction_ratio = round(
        threat_density / (interaction_density + _EPS), 4
    )
    creature_to_noncreature_ratio = round(
        creature_total / (non_land_total - creature_total + _EPS), 4
    )
    land_to_spell_ratio = round(land_total / (non_land_total + _EPS), 4)

    valid_pt = creatures[
        (creatures["_power_num"] >= 0) & (creatures["_toughness_num"] >= 0)
    ]
    valid_pt_total = int(valid_pt["count"].sum())
    avg_power = round(
        float(
            (valid_pt["_power_num"] * valid_pt["count"]).sum() / max(valid_pt_total, 1)
        ),
        3,
    )
    avg_toughness = round(
        float(
            (valid_pt["_toughness_num"] * valid_pt["count"]).sum()
            / max(valid_pt_total, 1)
        ),
        3,
    )
    power_toughness_ratio = round(avg_power / (avg_toughness + _EPS), 4)
    keyword_density = round(
        float(
            (non_lands["_n_keywords"].fillna(0) * non_lands["count"]).sum()
            / (non_land_total + _EPS)
        ),
        4,
    )

    draw_efficiency_score = round(draw_count / (non_land_total + _EPS), 4)
    ramp_efficiency_score = round(ramp_count / (non_land_total + _EPS), 4)
    tutor_efficiency_score = round(tutor_count / (non_land_total + _EPS), 4)
    free_spell_aggressiveness = round(free_count / (non_land_total + _EPS), 4)

    instant_sorcery_ratio = round(instant_total / (sorcery_total + _EPS), 4)
    non_land_non_creatures = non_lands[~non_lands["_is_creature"].fillna(False)]
    ncr_total = int(non_land_non_creatures["count"].sum())
    avg_cmc_creatures = round(
        float(
            (creatures["_cmc"].fillna(0) * creatures["count"]).sum()
            / (creature_total + _EPS)
        ),
        3,
    )
    avg_cmc_noncreatures = round(
        float(
            (
                non_land_non_creatures["_cmc"].fillna(0)
                * non_land_non_creatures["count"]
            ).sum()
            / (ncr_total + _EPS)
        ),
        3,
    )

    color_entropy = _shannon_entropy(list(pip_totals.values()))

    rarity_vals = grp["_rarity_ord"].fillna(-1) * grp["count"]
    avg_rarity_ord = round(float(rarity_vals.sum() / (main_total + _EPS)), 4)
    high_rarity_total = int(grp[grp["_rarity_ord"].fillna(-1) >= 2]["count"].sum())
    high_rarity_density = round(high_rarity_total / (main_total + _EPS), 4)
    mythic_count = int(grp[grp["_rarity_ord"].fillna(-1) == 3]["count"].sum())

    enchantment_density = round(enchantment_total / (non_land_total + _EPS), 4)
    artifact_density = round(artifact_total / (non_land_total + _EPS), 4)
    planeswalker_density = round(planeswalker_total / (non_land_total + _EPS), 4)

    life_gain_density = round(life_gain_count / (non_land_total + _EPS), 4)
    protection_density = round(protection_count / (non_land_total + _EPS), 4)
    evasion_density = round(evasion_count / (non_land_total + _EPS), 4)

    color_count = int(sum(1 for c in COLORS if pip_totals[c] > 0))
    is_colorless = int(color_count == 0)

    multicolor_total = int(
        non_lands[non_lands["_is_multicolor"].fillna(False)]["count"].sum()
    )
    multicolor_density = round(multicolor_total / (non_land_total + _EPS), 4)

    if len(cmc_expanded) >= 3:
        std = float(np.std(cmc_expanded))
        if std > 0:
            m3 = float(np.mean((cmc_expanded - avg_cmc) ** 3))
            cmc_skewness = round(m3 / (std**3), 4)
        else:
            cmc_skewness = 0.0
    else:
        cmc_skewness = 0.0

    return {
        "deck_id": deck_id,
        "uniqueness": uniqueness,
        "land_ratio": land_ratio,
        "karsten_land_delta": karsten_land_delta,
        "singleton_ratio": singleton_ratio,
        "norm_weighted_W": norm_weighted["W"],
        "norm_weighted_U": norm_weighted["U"],
        "norm_weighted_B": norm_weighted["B"],
        "norm_weighted_R": norm_weighted["R"],
        "norm_weighted_G": norm_weighted["G"],
        "norm_weighted_C": norm_weighted["C"],
        "curve_dominance_ratio": curve_dominance_ratio,
        "low_curve_density": low_curve_density,
        "high_curve_density": high_curve_density,
        "curve_concentration_top3": curve_concentration_top3,
        "cmc_variance": cmc_variance,
        "cmc_kurtosis": cmc_kurtosis,
        "modal_cmc": modal_cmc,
        "interaction_density": interaction_density,
        "threat_density": threat_density,
        "creature_density": creature_density,
        "board_wipe_count": board_wipe_count,
        "combo_potential": combo_potential,
        "threat_to_interaction_ratio": threat_to_interaction_ratio,
        "creature_to_noncreature_ratio": creature_to_noncreature_ratio,
        "land_to_spell_ratio": land_to_spell_ratio,
        "avg_power": avg_power,
        "avg_toughness": avg_toughness,
        "power_toughness_ratio": power_toughness_ratio,
        "keyword_density": keyword_density,
        "draw_efficiency_score": draw_efficiency_score,
        "ramp_efficiency_score": ramp_efficiency_score,
        "tutor_efficiency_score": tutor_efficiency_score,
        "free_spell_aggressiveness": free_spell_aggressiveness,
        "instant_sorcery_ratio": instant_sorcery_ratio,
        "avg_cmc_creatures": avg_cmc_creatures,
        "avg_cmc_noncreatures": avg_cmc_noncreatures,
        "color_entropy": color_entropy,
        "color_count": color_count,
        "is_colorless": is_colorless,
        "avg_rarity_ord": avg_rarity_ord,
        "high_rarity_density": high_rarity_density,
        "mythic_count": mythic_count,
        "enchantment_density": enchantment_density,
        "artifact_density": artifact_density,
        "planeswalker_density": planeswalker_density,
        "life_gain_density": life_gain_density,
        "protection_density": protection_density,
        "evasion_density": evasion_density,
        "multicolor_density": multicolor_density,
        "cmc_skewness": cmc_skewness,
        "avg_cmc": round(avg_cmc, 3),
    }


def build_deck_analytical_features(
    df_deck_cards: pd.DataFrame,
    df_cards: pd.DataFrame,
) -> pd.DataFrame:
    """Builds the 51-feature analytical vector for every deck.

    Parameters
    ----------
    df_deck_cards:
        Columns: `deck_id`, `card_uuid`, `count`, `is_sideboard`.
    df_cards:
        `extract.load_cards_features()`'s output -- must include `uuid`,
        `text`, `mana_cost`, `type_line`.

    Returns
    -------
    DataFrame (n_decks x 52 columns): `deck_id` + 51 numeric features.
    """
    main = df_deck_cards[~df_deck_cards["is_sideboard"]].copy()
    if main.empty:
        return pd.DataFrame()

    enriched = _enrich_cards(df_cards)
    enriched_idx = enriched.set_index("uuid")

    df = main.join(enriched_idx, on="card_uuid", how="left")
    # A left join introduces NaN into boolean columns, promoting them to
    # object dtype -- `~` would then do bitwise NOT (~True = -2) instead of
    # logical NOT. Cast back explicitly.
    _bool_cols = [c for c in df.columns if c.startswith("_is_") or c.startswith("_fn_")]
    df[_bool_cols] = df[_bool_cols].fillna(False).astype(bool)
    _num_cols = [c for c in df.columns if c.startswith("_") and c not in _bool_cols]
    df[_num_cols] = df[_num_cols].fillna(0)

    records = [
        _compute_deck_features(str(deck_id), grp)
        for deck_id, grp in df.groupby("deck_id")
    ]
    return pd.DataFrame(records)
