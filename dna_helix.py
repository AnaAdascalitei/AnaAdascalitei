#!/usr/bin/env python3
"""Render a rotating DNA double helix from a GitHub user's contribution calendar.

Each base pair = one week of the last year. Rung brightness/thickness = contributions that week.
Usage: GITHUB_TOKEN=... python3 dna_helix.py <username> <output.svg>
       python3 dna_helix.py --demo <output.svg>   (random data, no token needed)
"""
import json, math, os, random, sys, urllib.request

QUERY = """query($login:String!){ user(login:$login){ contributionsCollection{
  contributionCalendar{ totalContributions weeks{ contributionDays{ contributionCount } } } } } }"""

# Colours (look fine on both light and dark GitHub themes)
BASES = {"A": "#4FD1C5", "T": "#F687B3", "G": "#F6E05E", "C": "#9F7AEA"}
PAIRS = [("A", "T"), ("T", "A"), ("G", "C"), ("C", "G")]
RUNG_LEVELS = ["#3b4a54", "#2c7a7b", "#38b2ac", "#4FD1C5", "#9ff5ec"]  # 0 → max
LABEL = "#8b949e"

W, H = 880, 190
MID = 88
AMP = 52          # helix radius (px)
DUR = 6.0         # seconds per full rotation
PER_TURN = 10.5   # base pairs per helical turn (like real B-DNA)
STEPS = 24        # keyframe resolution


def fetch(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json",
        "User-Agent": "dna-helix"})
    data = json.load(urllib.request.urlopen(req))
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cal["weeks"]]
    return weeks, cal["totalContributions"]


def level(n, mx):
    if n == 0 or mx == 0:
        return 0
    return 1 + min(3, int(3 * n / mx))


def keyframes(name, fn):
    lines = [f"@keyframes {name}{{"]
    for s in range(STEPS + 1):
        lines.append(f"{100 * s / STEPS:.2f}%{{transform:{fn(2 * math.pi * s / STEPS)}}}")
    lines.append("}")
    return "".join(lines)


def render(weeks, total, login):
    weeks = weeks[-52:]
    n = len(weeks)
    mx = max(weeks) if weeks else 0
    x0, x1 = 30, W - 30
    step = (x1 - x0) / max(n - 1, 1)
    rng = random.Random(login)  # stable "sequence" per user

    css = [
        "svg{font-family:'Fira Code',ui-monospace,SFMono-Regular,Menlo,monospace}",
        # top base: y = -A cos θ, size grows when in front (sin θ > 0)
        keyframes("top", lambda t: f"translateY({-AMP * math.cos(t):.2f}px) scale({1 + 0.35 * math.sin(t):.3f})"),
        keyframes("bot", lambda t: f"translateY({AMP * math.cos(t):.2f}px) scale({1 - 0.35 * math.sin(t):.3f})"),
        keyframes("rung", lambda t: f"scaleY({math.cos(t):.3f})"),
        f".t{{animation:top {DUR}s linear infinite}}",
        f".b{{animation:bot {DUR}s linear infinite}}",
        f".r{{animation:rung {DUR}s linear infinite}}",
    ]

    rungs = []
    for i, c in enumerate(weeks):
        x = x0 + i * step
        delay = -DUR * ((i / PER_TURN) % 1)
        lv = level(c, mx)
        a, b = rng.choice(PAIRS)
        width = 1.5 + lv * 0.9
        rungs.append(
            f'<g transform="translate({x:.1f},{MID})">'
            f'<title>{c} contributions</title>'
            f'<line class="r" style="animation-delay:{delay:.2f}s" x1="0" y1="{-AMP}" x2="0" y2="{AMP}" '
            f'stroke="{RUNG_LEVELS[lv]}" stroke-width="{width:.1f}" stroke-linecap="round" opacity="{0.55 + 0.11 * lv:.2f}"/>'
            f'<circle class="t" style="animation-delay:{delay:.2f}s" r="4.2" fill="{BASES[a]}"/>'
            f'<circle class="b" style="animation-delay:{delay:.2f}s" r="4.2" fill="{BASES[b]}"/>'
            f'</g>')

    legend_x = W - 30
    legend = "".join(
        f'<circle cx="{legend_x - 150 + k * 38}" cy="{H - 14}" r="4" fill="{BASES[base]}"/>'
        f'<text x="{legend_x - 143 + k * 38}" y="{H - 10}" font-size="11" fill="{LABEL}">{base}</text>'
        for k, base in enumerate("ATGC"))

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
        f'<style>{"".join(css)}</style>'
        + "".join(rungs) +
        f'<text x="30" y="{H - 10}" font-size="12" fill="{LABEL}">'
        f'🧬 {total} contributions in the last year · 1 base pair = 1 week</text>'
        + legend + "</svg>")


def main():
    if sys.argv[1] == "--demo":
        r = random.Random(7)
        weeks = [max(0, int(r.gauss(4, 4))) if r.random() > 0.3 else 0 for _ in range(52)]
        login, total = "demo", sum(weeks)
    else:
        login = sys.argv[1]
        weeks, total = fetch(login, os.environ["GITHUB_TOKEN"])
    out = sys.argv[2]
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(weeks, total, login))


if __name__ == "__main__":
    main()
