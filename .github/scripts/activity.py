"""Draws the profile's activity graph: contributions per week over the last
year, from GitHub's own contribution calendar, as two SVGs (light and dark)
committed next to the README. Replaces github-readme-activity-graph, whose
host was switched off.

Needs GITHUB_TOKEN (any token can read a public calendar) and GITHUB_USER.
"""

import datetime as dt
import json
import os
import urllib.request

USER = os.environ.get("GITHUB_USER", "Esmaeelpour")
QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

THEMES = {
    "activity.svg": {"line": "#0969da", "fill": "#0969da", "text": "#57606a", "grid": "#d0d7de"},
    "activity-dark.svg": {"line": "#58a6ff", "fill": "#58a6ff", "text": "#8b949e", "grid": "#30363d"},
}
W, H = 840, 200
LEFT, RIGHT, TOP, BOTTOM = 36, 12, 34, 28


def calendar() -> tuple[int, list[tuple[dt.date, int]]]:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        cal = json.load(r)["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = []
    for week in cal["weeks"]:
        days = week["contributionDays"]
        weeks.append((dt.date.fromisoformat(days[0]["date"]), sum(d["contributionCount"] for d in days)))
    return cal["totalContributions"], weeks


def smooth(points: list[tuple[float, float]], floor: float) -> str:
    """A path through the points with gentle curves (Catmull-Rom as Béziers),
    never dipping below `floor` (no week has fewer than none)."""
    d = f"M{points[0][0]:.1f},{points[0][1]:.1f}"
    for i in range(len(points) - 1):
        p0 = points[max(i - 1, 0)]
        p1, p2 = points[i], points[i + 1]
        p3 = points[min(i + 2, len(points) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, min(floor, p1[1] + (p2[1] - p0[1]) / 6))
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, min(floor, p2[1] - (p3[1] - p1[1]) / 6))
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def nice_top(peak: int) -> int:
    for step in (5, 10, 20, 25, 50, 100, 200, 250, 500, 1000):
        if peak <= step * 4:
            return step * 4
    return peak


def draw(total: int, weeks: list[tuple[dt.date, int]], c: dict) -> str:
    top = nice_top(max((n for _, n in weeks), default=0) or 1)
    pw, ph = W - LEFT - RIGHT, H - TOP - BOTTOM
    xs = [LEFT + pw * i / max(1, len(weeks) - 1) for i in range(len(weeks))]
    ys = [TOP + ph * (1 - min(n, top) / top) for _, n in weeks]
    pts = list(zip(xs, ys))
    line = smooth(pts, TOP + ph)
    area = f"{line} L{xs[-1]:.1f},{TOP + ph:.1f} L{xs[0]:.1f},{TOP + ph:.1f} Z"
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">',
        f'<title>{total} contributions in the last year</title>',
        '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{c["fill"]}" stop-opacity="0.35"/>'
        f'<stop offset="1" stop-color="{c["fill"]}" stop-opacity="0.02"/></linearGradient></defs>',
        f'<text x="{LEFT}" y="18" font-size="13" font-weight="600" fill="{c["text"]}">'
        f'{total:,} contributions in the last year · per week</text>',
    ]
    for k in range(5):
        v = top * k // 4
        y = TOP + ph * (1 - k / 4)
        out.append(f'<line x1="{LEFT}" x2="{W - RIGHT}" y1="{y:.1f}" y2="{y:.1f}" stroke="{c["grid"]}" '
                   f'stroke-width="1" stroke-dasharray="{"" if k == 0 else "3 4"}"/>')
        out.append(f'<text x="{LEFT - 6}" y="{y + 4:.1f}" font-size="10" text-anchor="end" fill="{c["text"]}">{v}</text>')
    last_month = None
    for (start, _), x in zip(weeks, xs):
        if start.month != last_month and start.day <= 7:
            out.append(f'<text x="{x:.1f}" y="{H - 8}" font-size="10" text-anchor="middle" fill="{c["text"]}">'
                       f'{start.strftime("%b")}</text>')
        last_month = start.month
    out.append(f'<path d="{area}" fill="url(#g)"/>')
    out.append(f'<path d="{line}" fill="none" stroke="{c["line"]}" stroke-width="2" stroke-linejoin="round"/>')
    out.append(f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="3" fill="{c["line"]}"/>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    total, weeks = calendar()
    out = os.environ.get("OUT_DIR", "assets")
    os.makedirs(out, exist_ok=True)
    for name, colours in THEMES.items():
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(draw(total, weeks, colours))
    print(f"{total} contributions, {len(weeks)} weeks")


if __name__ == "__main__":
    main()
