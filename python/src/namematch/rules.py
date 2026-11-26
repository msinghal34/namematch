"""Loads rules.toml once."""

import tomllib
from pathlib import Path

_DIR = Path(__file__).resolve().parent

with open(_DIR / "rules.toml", "rb") as fh:
    RULES = tomllib.load(fh)

VERSION = RULES["version"]


def _load_freq(name: str) -> tuple[dict[str, int], int]:
    """Key -> count, and the number of persons counted (the '# persons' header line)."""
    path = _DIR / name
    if not path.exists():
        return {}, 0
    out, persons = {}, 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# persons"):
            persons = int(line.split("\t")[1])
        elif line and not line.startswith("#"):
            k, n = line.split("\t")
            out[k] = int(n)
    return out, persons


# Two tables of how common each name part is: the original sample, and the eAasthi export
# (1.2 million properties); the switch eaasthi_weights picks the second.
TOKEN_FREQ, TOKEN_PERSONS = _load_freq("token_freq.tsv")
TOKEN_FREQ_EAASTHI, TOKEN_PERSONS_EAASTHI = _load_freq("token_freq_eaasthi.tsv")


def _load_gender() -> dict[str, str]:
    path = _DIR / "name_gender.tsv"
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            k, m, f = line.split("\t")
            out[k] = "m" if int(m) > int(f) else "f"
    return out


NAME_GENDER = _load_gender()
