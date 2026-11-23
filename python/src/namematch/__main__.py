"""python -m namematch "NAME A" "NAME B"  ->  score, band and reasons."""

import sys

from . import match, parse


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    a, b = sys.argv[1], sys.argv[2]
    r = match(a, b)
    print(f"score  {r.score:.3f}  ({r.band})")
    print(f"pair   {r.left}  ~  {r.right}")
    for reason in r.reasons:
        print(f"  - {reason}")
    print(f"parsed A: {parse(a).persons} {parse(a).orgs}")
    print(f"parsed B: {parse(b).persons} {parse(b).orgs}")


if __name__ == "__main__":
    main()
