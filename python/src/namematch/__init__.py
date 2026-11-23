"""Rule-based person-name matching for Karnataka property records."""

from .parse import ParsedName, Person, parse
from .rules import VERSION
from .score import BANDS, OWNER_MODES, MatchResult, band, covers, match

__all__ = ["match", "covers", "OWNER_MODES", "parse", "band", "BANDS", "MatchResult", "ParsedName", "Person", "VERSION"]
