from enum import Enum


class Formats(Enum):
    STANDARD = "Standard"
    PIONEER = "Pioneer"
    MODERN = "Modern"
    LEGACY = "Legacy"
    VINTAGE = "Vintage"
    DUEL_COMMANDER = "Duel Commander"
    PAUPER = "Pauper"
    PREMODERN = "Premodern"


FORMATS = [mtg_format.value for mtg_format in Formats]
