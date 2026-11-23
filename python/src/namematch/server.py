"""Local HTTP server for namematch: a JSON API and a small page to try pairs by hand.

    PYTHONPATH=src python -m namematch.server [--host 127.0.0.1] [--port 8765]

Endpoints (GET with query parameters, or POST with a JSON body):
    /api/match?a=...&b=...[&owners=any|all_a|all]
                              owners=any (default): best pair - any owner in a matching any owner in b
                              owners=all_a: every owner in a must be found in b
                              owners=all: every owner on both sides must pair one-to-one
                              every response carries `partial` and per-owner rows
    /api/covers?a=...&b=...   shortcut for owners=all_a
    /api/health               version and status
    /                         the page

Standard library only; binds to localhost by default because the inputs are personal data.
"""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import BANDS, OWNER_MODES, VERSION, match, parse

MAX_LEN = 2000


def _person(p) -> dict:
    return {
        "tokens": [{"text": t.text, "initial": t.initial} for t in p.tokens],
        "display": repr(p),
        "aliases": [[t.text for t in a] for a in p.aliases],
        "relative": [t.text for t in p.relative],
        "relation": p.relation,
        "gender": p.gender,
        "role": p.role,
        "firm": p.firm,
    }


def _parsed(text: str) -> dict:
    p = parse(text)
    return {
        "persons": [_person(x) for x in p.persons],
        "organisations": [{"tokens": o.tokens} for o in p.orgs],
        "representatives": [_person(x) for x in p.representatives],
        "placeholder": p.placeholder,
        "script": p.script,
    }


def result(owners: str, a: str, b: str) -> dict:
    r = match(a, b, owners=owners)
    return {
        "version": VERSION,
        "owners": owners,
        "owners_rule": OWNER_MODES[owners],
        "a": a,
        "b": b,
        "score": r.score,
        "band": r.band,
        "auto_accept": r.band == "same",
        "partial": r.partial,
        "reasons": r.reasons,
        "matched_pair": {"a": r.left, "b": r.right},
        "owners_a": r.owners_a,
        "owners_b": r.owners_b,
        "parsed": {"a": _parsed(a), "b": _parsed(b)},
        "bands": [{"band": name, "from": floor} for floor, name in BANDS],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = f"namematch/{VERSION}"

    def _send(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"), "application/json; charset=utf-8")

    def _api(self, path: str, params: dict) -> None:
        if path == "/api/health":
            return self._json(200, {"status": "ok", "version": VERSION})
        kind = path.rsplit("/", 1)[-1]
        if kind not in ("match", "covers"):
            return self._json(404, {"error": f"unknown endpoint {path}"})
        a, b = params.get("a"), params.get("b")
        owners = "all_a" if kind == "covers" else params.get("owners") or "any"
        if not isinstance(a, str) or not isinstance(b, str):
            return self._json(400, {"error": "give two strings, 'a' and 'b'"})
        if len(a) > MAX_LEN or len(b) > MAX_LEN:
            return self._json(400, {"error": f"each string must be at most {MAX_LEN} characters"})
        if owners not in OWNER_MODES:
            return self._json(400, {"error": f"owners must be one of {', '.join(OWNER_MODES)}"})
        self._json(200, result(owners, a, b))

    def do_GET(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            return self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        if url.path.startswith("/api/"):
            params = {k: v[0] for k, v in parse_qs(url.query, keep_blank_values=True).items()}
            return self._api(url.path, params)
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        if not url.path.startswith("/api/"):
            return self._json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            params = json.loads(self.rfile.read(min(length, 64_000)) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "body must be JSON: {\"a\": \"...\", \"b\": \"...\"}"})
        if not isinstance(params, dict):
            return self._json(400, {"error": "body must be a JSON object"})
        self._api(url.path, params)

    def log_message(self, fmt, *args) -> None:  # names are personal data: log the request line only
        print(f"{self.address_string()} {self.command} {urlparse(self.path).path}", flush=True)


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Name Match</title>
<style>
:root { --on-accent:#fff; --bg:#f6f7f9; --card:#fff; --ink:#1d2330; --muted:#5e6878; --line:#dfe3ea; --accent:#2f5bd3;
  --same:#1f7a45; --same-bg:#e3f4ea; --likely:#4d7a1f; --likely-bg:#eef6e2; --review:#8a6100; --review-bg:#fdf3d6;
  --diff:#a42b2b; --diff-bg:#fbe5e5; color-scheme: light; }   /* light theme only, by design */
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 860px; margin: 0 auto; padding: 32px 16px 48px; }
h1 { font-size: 22px; margin: 0 0 4px; }
.sub { color: var(--muted); margin: 0 0 24px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 20px; margin-bottom: 16px; }
label { display:block; font-weight:600; font-size:13px; color:var(--muted); margin: 0 0 6px; }
input[type=text] { width:100%; padding:10px 12px; font:inherit; color:var(--ink); background:var(--bg);
  border:1px solid var(--line); border-radius:8px; margin-bottom:14px; }
input[type=text]:focus { outline: 2px solid var(--accent); outline-offset: 0; border-color: transparent; }
.row { display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
button { font:inherit; font-weight:600; padding:9px 18px; border-radius:8px; border:0; background:var(--accent); color:var(--on-accent); cursor:pointer; }
.mode { color: var(--muted); font-size: 14px; display:flex; gap:16px; }
.mode label { display:inline-flex; align-items:center; gap:6px; margin:0; font-weight:400; font-size:14px; color:var(--muted); cursor:pointer; }
.mode input { margin:0; accent-color: var(--accent); }
.score { display:flex; align-items:baseline; gap:14px; flex-wrap:wrap; }
.num { font-size: 40px; font-weight: 700; font-variant-numeric: tabular-nums; }
.band { font-weight:700; font-size:14px; padding:3px 10px; border-radius:999px; }
.b-same { color:var(--same); background:var(--same-bg); } .b-likely_same { color:var(--likely); background:var(--likely-bg); }
.b-review { color:var(--review); background:var(--review-bg); } .b-different { color:var(--diff); background:var(--diff-bg); }
h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); margin: 18px 0 8px; }
ul { margin: 0; padding-left: 20px; }
.pair { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 13px; overflow-wrap:anywhere; }
.grid { display:grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 640px) { .grid { grid-template-columns: 1fr; } }
.chip { display:inline-block; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 12px; border:1px solid var(--line);
  border-radius:6px; padding:1px 6px; margin: 2px 4px 2px 0; }
.muted { color: var(--muted); }
pre { font-size:12px; overflow:auto; background:var(--bg); padding:12px; border-radius:8px; border:1px solid var(--line); margin:0; }
details summary { cursor:pointer; color:var(--muted); font-size:14px; }
.err { color: var(--diff); }
.warn { margin: 12px 0 0; padding: 8px 12px; border-radius: 8px; background: var(--review-bg); color: var(--review); font-size: 14px; }
table.own { width: 100%; border-collapse: collapse; font-size: 14px; }
table.own th { text-align: left; color: var(--muted); font-weight: 600; font-size: 12px; padding: 4px 8px; border-bottom: 1px solid var(--line); }
table.own td { padding: 6px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
table.own td:first-child { color: var(--muted); width: 24px; }
.num-s { white-space: nowrap; }
</style>
</head>
<body>
<main>
  <h1>Name Match</h1>
  <p class="sub">How strongly an officer would treat two owner names as the same person. namematch <span id="ver"></span></p>
  <form class="card" id="f">
    <label for="a">Name A (e.g. Book / Tax owner name)</label>
    <input type="text" id="a" autocomplete="off" value="1.ANAND RAO 2.SAVITHA RAO">
    <label for="b">Name B (e.g. Aadhaar, deed or property tax name)</label>
    <input type="text" id="b" autocomplete="off" value="Anand Rao S/o Venkat Rao">
    <div class="row">
      <button type="submit">Match</button>
      <div class="mode">
        <label title="Any owner in A matching any owner in B is enough"><input type="radio" name="m" value="any" checked>any owner</label>
        <label title="Every owner in A must be found in B"><input type="radio" name="m" value="all_a">every owner in A</label>
        <label title="Every owner on both sides must pair one-to-one"><input type="radio" name="m" value="all">all owners, both sides</label>
      </div>
    </div>
  </form>
  <div id="out"></div>
</main>
<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const LABEL = {same: "same person", likely_same: "likely same", review: "needs review", different: "different"};
function people(p) {
  const rows = [];
  for (const x of p.persons) {
    let s = x.tokens.map(t => `<span class="chip">${esc(t.initial ? t.text.toUpperCase() + "." : t.text)}</span>`).join("");
    const extra = [];
    if (x.relative.length) extra.push(`${esc(x.relation || "rel")} ${esc(x.relative.join(" "))}`);
    if (x.gender) extra.push(x.gender === "f" ? "female" : "male");
    if (x.firm) extra.push("M/s firm");
    if (x.aliases.length) extra.push("alias " + esc(x.aliases.map(a => a.join(" ")).join(", ")));
    rows.push(`<li>${s}${extra.length ? ` <span class="muted">(${extra.join("; ")})</span>` : ""}</li>`);
  }
  for (const o of p.organisations) rows.push(`<li><span class="muted">organisation:</span> ${esc(o.tokens.join(" "))}</li>`);
  for (const r of p.representatives) rows.push(`<li><span class="muted">representative (not an owner):</span> ${esc(r.tokens.map(t => t.text).join(" "))}</li>`);
  if (p.placeholder) rows.push(`<li class="muted">placeholder: names nobody</li>`);
  if (!rows.length) rows.push(`<li class="muted">no name found</li>`);
  return `<ul>${rows.join("")}</ul><p class="muted" style="margin:6px 0 0;font-size:13px">script: ${esc(p.script)}</p>`;
}
function owners(r) {
  if (r.owners_a.length + r.owners_b.length <= 2) return "";
  const row = (side, x) => `<tr><td>${side}</td><td class="pair">${esc(x.owner)}</td><td class="pair">${esc(x.best_match ?? "")}</td>
    <td class="num-s"><span class="band b-${x.score >= 0.8 ? "same" : x.score >= 0.65 ? "likely_same" : x.score >= 0.35 ? "review" : "different"}">${x.score.toFixed(2)}</span></td></tr>`;
  return `<div class="card"><h2 style="margin-top:0">Owners</h2><table class="own"><thead><tr><th></th><th>Owner</th><th>Best counterpart</th><th>Score</th></tr></thead>
    <tbody>${r.owners_a.map(x => row("A", x)).join("")}${r.owners_b.map(x => row("B", x)).join("")}</tbody></table></div>`;
}
async function run(e) {
  if (e) e.preventDefault();
  const mode = document.querySelector("input[name=m]:checked").value;
  const res = await fetch("/api/match", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({a: $("#a").value, b: $("#b").value, owners: mode})});
  const r = await res.json();
  if (!res.ok) { $("#out").innerHTML = `<div class="card err">${esc(r.error)}</div>`; return; }
  $("#ver").textContent = r.version;
  $("#out").innerHTML = `
    <div class="card">
      <div class="score"><span class="num">${r.score.toFixed(2)}</span>
        <span class="band b-${r.band}">${LABEL[r.band]}</span>
        <span class="muted">${r.auto_accept ? "auto-accept" : "not auto-accepted"}</span></div>
      ${r.partial ? `<p class="warn">Partial: not every owner has a match on the other side. ${r.owners === "any" ? "Choose an \u201call owners\u201d option to require one." : ""}</p>` : ""}
      <h2>${r.owners === "any" ? "Best-matching pair" : "Deciding pair (the weakest)"}</h2>
      <div class="pair">${esc(r.matched_pair.a)}<br>${esc(r.matched_pair.b)}</div>
      <h2>Reasons</h2>
      ${r.reasons.length ? `<ul>${r.reasons.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : `<p class="muted" style="margin:0">exact agreement after normalisation</p>`}
    </div>
    ${owners(r)}
    <div class="grid">
      <div class="card"><h2 style="margin-top:0">A parsed</h2>${people(r.parsed.a)}</div>
      <div class="card"><h2 style="margin-top:0">B parsed</h2>${people(r.parsed.b)}</div>
    </div>
    <div class="card"><details><summary>Full JSON response</summary><pre>${esc(JSON.stringify(r, null, 2))}</pre></details></div>`;
}
$("#f").addEventListener("submit", run);
run();
</script>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description="namematch local server")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"namematch {VERSION} on http://{args.host}:{args.port}/", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
