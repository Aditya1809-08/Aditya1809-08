import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

USER = "Aditya1809-08"
OUT = Path("assets/github-stats.svg")
TOKEN = os.environ["GITHUB_TOKEN"]

headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

query = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      totalContributions
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoryContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount contributionLevel }
        }
      }
    }
  }
}
"""

now = datetime.now(timezone.utc)
# The account is new, but using a full-year window keeps this useful as the profile grows.
start = now - timedelta(days=365)
resp = requests.post(
    "https://api.github.com/graphql",
    json={"query": query, "variables": {"login": USER, "from": start.isoformat(), "to": now.isoformat()}},
    headers=headers,
    timeout=30,
)
resp.raise_for_status()
body = resp.json()
if body.get("errors"):
    raise RuntimeError(body["errors"])
data = body["data"]["user"]["contributionsCollection"]

# Flatten the contribution calendar and calculate streaks.
daily = [d for w in data["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
daily.sort(key=lambda x: x["date"])

current_streak = 0
longest_streak = 0
running = 0
for day in daily:
    if day["contributionCount"] > 0:
        running += 1
        longest_streak = max(longest_streak, running)
    else:
        running = 0

# Current streak ends today or yesterday. If the latest calendar day is today with 0,
# a streak can still end yesterday.
for day in reversed(daily):
    if day["contributionCount"] > 0:
        current_streak += 1
    else:
        if day["date"] == now.date().isoformat():
            continue
        break

# Weekly totals for the detailed trend chart.
weekly = []
for i in range(0, len(daily), 7):
    chunk = daily[i:i + 7]
    if chunk:
        weekly.append((chunk[0]["date"], sum(x["contributionCount"] for x in chunk)))
weekly = weekly[-26:]

# Repository language distribution from public repositories.
repos = []
page = 1
while True:
    r = requests.get(
        f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}",
        timeout=30,
    )
    r.raise_for_status()
    batch = r.json()
    repos.extend(batch)
    if len(batch) < 100:
        break
    page += 1

language_bytes = {}
for repo in repos:
    if repo.get("fork"):
        continue
    r = requests.get(repo["languages_url"], timeout=30)
    if r.ok:
        for lang, amount in r.json().items():
            language_bytes[lang] = language_bytes.get(lang, 0) + amount

if not language_bytes:
    language_bytes = {"HTML": 1}

total_bytes = sum(language_bytes.values())
languages = sorted(language_bytes.items(), key=lambda x: x[1], reverse=True)[:6]


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

colors = ["#58a6ff", "#3fb950", "#f78166", "#d29922", "#bc8cff", "#79c0ff"]
W, H = 1100, 690
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
svg.append('<rect width="1100" height="690" rx="20" fill="#0d1117" stroke="#30363d"/>')
svg.append('<text x="35" y="42" fill="#f0f6fc" font-family="Arial,sans-serif" font-size="23" font-weight="700">GitHub Progress &amp; Statistics</text>')
svg.append('<text x="35" y="67" fill="#8b949e" font-family="Arial,sans-serif" font-size="13">Detailed contribution activity · updated automatically every day</text>')

# Stat cards.
stats = [
    ("TOTAL CONTRIBUTIONS", data["totalContributions"]),
    ("TOTAL COMMITS", data["totalCommitContributions"]),
    ("CURRENT STREAK", f"{current_streak} days"),
    ("LONGEST STREAK", f"{longest_streak} days"),
]
for i, (label, value) in enumerate(stats):
    x = 35 + i * 265
    svg.append(f'<rect x="{x}" y="88" width="245" height="82" rx="12" fill="#161b22" stroke="#30363d"/>')
    svg.append(f'<text x="{x+18}" y="113" fill="#8b949e" font-family="Arial,sans-serif" font-size="10" font-weight="700">{label}</text>')
    svg.append(f'<text x="{x+18}" y="148" fill="#f0f6fc" font-family="Arial,sans-serif" font-size="25" font-weight="700">{value}</text>')

# Detailed 26-week line chart.
chart_x, chart_y, chart_w, chart_h = 45, 205, 670, 205
svg.append('<text x="45" y="193" fill="#f0f6fc" font-family="Arial,sans-serif" font-size="15" font-weight="700">Contribution Trend — Last 26 Weeks</text>')
maxv = max([v for _, v in weekly] or [1])
for grid in range(5):
    y = chart_y + chart_h - (chart_h * grid / 4)
    value = round(maxv * grid / 4)
    svg.append(f'<line x1="{chart_x}" y1="{y:.1f}" x2="{chart_x+chart_w}" y2="{y:.1f}" stroke="#21262d"/>')
    svg.append(f'<text x="{chart_x-10}" y="{y+4:.1f}" text-anchor="end" fill="#6e7681" font-family="Arial,sans-serif" font-size="10">{value}</text>')
points = []
for i, (_, value) in enumerate(weekly):
    x = chart_x + chart_w * i / max(1, len(weekly) - 1)
    y = chart_y + chart_h - chart_h * value / maxv
    points.append((x, y, value))
if points:
    area = f"{chart_x},{chart_y+chart_h} " + " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points) + f" {chart_x+chart_w},{chart_y+chart_h}"
    svg.append(f'<polygon points="{area}" fill="#58a6ff" opacity="0.10"/>')
    svg.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y,_ in points)}" fill="none" stroke="#58a6ff" stroke-width="3"/>')
    for x, y, value in points:
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#58a6ff"><title>{value} contributions</title></circle>')
svg.append('<text x="45" y="430" fill="#6e7681" font-family="Arial,sans-serif" font-size="10">Each point = one week · hover points for exact contribution count</text>')

# Detailed contribution heatmap.
svg.append('<text x="45" y="465" fill="#f0f6fc" font-family="Arial,sans-serif" font-size="15" font-weight="700">Daily Contribution Heatmap — Last Year</text>')
heat_x, heat_y = 45, 485
cell, gap = 11, 3
# Use the last 53 weeks from the calendar, preserving the GitHub-style weekly layout.
heat_weeks = []
for w in range(0, len(daily), 7):
    chunk = daily[w:w+7]
    if chunk:
        heat_weeks.append(chunk)
heat_weeks = heat_weeks[-53:]
levels = {"NONE": "#161b22", "FIRST_QUARTILE": "#0e4429", "SECOND_QUARTILE": "#006d32", "THIRD_QUARTILE": "#26a641", "FOURTH_QUARTILE": "#39d353"}
for wx, week in enumerate(heat_weeks):
    for dy, day in enumerate(week):
        level = levels.get(day.get("contributionLevel", "NONE"), "#161b22")
        x = heat_x + wx * (cell + gap)
        y = heat_y + dy * (cell + gap)
        svg.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{level}"><title>{day["date"]}: {day["contributionCount"]} contributions</title></rect>')
svg.append('<text x="45" y="585" fill="#6e7681" font-family="Arial,sans-serif" font-size="10">Less</text>')
for i, c in enumerate(["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]):
    svg.append(f'<rect x="75" y="576" width="11" height="11" rx="2" fill="{c}"/>')
svg.append('<text x="151" y="585" fill="#6e7681" font-family="Arial,sans-serif" font-size="10">More</text>')

# Language donut/pie and contribution breakdown.
cx, cy, radius = 850, 300, 83
start_angle = -90
for idx, (lang, amount) in enumerate(languages):
    pct = amount / total_bytes if total_bytes else 0
    end_angle = start_angle + pct * 360
    x1 = cx + radius * math.cos(math.radians(start_angle))
    y1 = cy + radius * math.sin(math.radians(start_angle))
    x2 = cx + radius * math.cos(math.radians(end_angle))
    y2 = cy + radius * math.sin(math.radians(end_angle))
    large = 1 if end_angle - start_angle > 180 else 0
    svg.append(f'<path d="M {cx} {cy} L {x1:.1f} {y1:.1f} A {radius} {radius} 0 {large} 1 {x2:.1f} {y2:.1f} Z" fill="{colors[idx]}"/>')
    start_angle = end_angle
svg.append(f'<circle cx="{cx}" cy="{cy}" r="43" fill="#0d1117"/>')
svg.append(f'<text x="{cx}" y="{cy-3}" text-anchor="middle" fill="#f0f6fc" font-family="Arial,sans-serif" font-size="20" font-weight="700">{len(languages)}</text>')
svg.append(f'<text x="{cx}" y="{cy+15}" text-anchor="middle" fill="#8b949e" font-family="Arial,sans-serif" font-size="11">languages</text>')
svg.append('<text x="760" y="420" fill="#f0f6fc" font-family="Arial,sans-serif" font-size="14" font-weight="700">Language Distribution</text>')
for idx, (lang, amount) in enumerate(languages):
    y = 445 + idx * 28
    pct = amount / total_bytes * 100 if total_bytes else 0
    svg.append(f'<circle cx="765" cy="{y-4}" r="5" fill="{colors[idx]}"/>')
    svg.append(f'<text x="778" y="{y}" fill="#c9d1d9" font-family="Arial,sans-serif" font-size="11">{esc(lang)} · {pct:.1f}%</text>')

# Contribution-type breakdown.
svg.append('<text x="900" y="205" fill="#f0f6fc" font-family="Arial,sans-serif" font-size="12" font-weight="700">Contribution Types</text>')
types = [
    ("Commits", data["totalCommitContributions"]),
    ("Pull Requests", data["totalPullRequestContributions"]),
    ("Issues", data["totalIssueContributions"]),
]
for i, (label, value) in enumerate(types):
    y = 228 + i * 24
    svg.append(f'<text x="900" y="{y}" fill="#8b949e" font-family="Arial,sans-serif" font-size="10">{esc(label)}</text>')
    svg.append(f'<text x="1055" y="{y}" text-anchor="end" fill="#f0f6fc" font-family="Arial,sans-serif" font-size="11" font-weight="700">{value}</text>')

svg.append('</svg>')
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("".join(svg), encoding="utf-8")
