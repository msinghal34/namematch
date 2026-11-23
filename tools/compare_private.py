"""Compare the Python and Java libraries on your own name pairs, which never leave your machine.

    python tools/compare_private.py pairs.tsv

pairs.tsv holds one pair per line, "NAME A<TAB>NAME B" (a header line is fine; it is compared
too). Each pair is matched in all three owner modes by both libraries and every field is compared.
Build the jar first (cd java && mvn package). Run it before a release on real records: the public
conformance cases are invented, and real data finds the shapes nobody thought of.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python" / "src"))

from namematch import VERSION, match  # noqa: E402

MODES = ("any", "all_a", "all")


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def result(a: str, b: str, mode: str) -> dict:
    m = match(a, b, mode)
    return {"score": m.score, "band": m.band, "reasons": m.reasons, "left": m.left, "right": m.right,
            "owners": m.owners, "partial": m.partial, "owners_a": m.owners_a, "owners_b": m.owners_b}


def main(path: str) -> int:
    jar = ROOT / "java" / "target" / f"namematch-{VERSION}.jar"
    if not jar.exists():
        sys.exit(f"{jar} is missing; build it with: cd java && mvn package")
    pairs = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        a, _, b = line.partition("\t")
        if a.strip() or b.strip():
            pairs.append((a, b))
    with tempfile.TemporaryDirectory() as tmp:
        tsv = Path(tmp) / "pairs.tsv"
        tsv.write_text("".join(f"{esc(a)}\t{esc(b)}\t{m}\n" for a, b in pairs for m in MODES), encoding="utf-8")
        with open(tsv, encoding="utf-8") as stdin:
            java = subprocess.run(["java", "-jar", str(jar), "--jsonl"], stdin=stdin, capture_output=True, check=True,
                                  text=True, encoding="utf-8").stdout.splitlines()
    differ = 0
    for k, (a, b) in enumerate(p for p in pairs for _ in MODES):
        mode = MODES[k % len(MODES)]
        want, got = result(a, b, mode), json.loads(java[k])
        if want != got:
            differ += 1
            if differ <= 5:
                print(f"DIFFERS ({mode}): {a!r} vs {b!r}\n  python: {want}\n  java:   {got}")
    print(f"{len(pairs) * len(MODES)} results compared, {differ} differ")
    return 1 if differ else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
