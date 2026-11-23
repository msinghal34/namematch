"""Loads rules.toml once."""

import tomllib
from pathlib import Path

_DIR = Path(__file__).resolve().parent

with open(_DIR / "rules.toml", "rb") as fh:
    RULES = tomllib.load(fh)

VERSION = RULES["version"]


def _load_freq() -> dict[str, int]:
    path = _DIR / "token_freq.tsv"
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            k, n = line.split("\t")
            out[k] = int(n)
    return out


TOKEN_FREQ = _load_freq()


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
