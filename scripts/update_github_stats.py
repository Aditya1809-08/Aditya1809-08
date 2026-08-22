import json
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
      contributionCalendar {
        weeks {
          contributionDays { date contributionCount }
        }
      }
    }
  }
}
"""

now = datetime.now(timezone.utc)
start = now - timedelta(days=365)
resp = requests.post(
    "https://api.github.com/graphql",
    json={"query": query, "variables": {"login": USER, "from": start.isoformat(), "to": now.isoformat()}},
    headers=headers,
    timeout=30,
)
resp.raise_for_status()
data = resp.json()["data"]["user"]["contributionsCollection"]

daily = [d for w in data["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
weeks = []
for i in range(0, len(daily), 7):
    chunk = daily[i:i+7]
    if chunk:
        weeks.append(sum(x["contributionCount"] for x in chunk))
weeks = weeks[-12:]

# Repository language distribution from public repositories.
repos = []
page = 1
while True:
    r = requests.get(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}", timeout=30)
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
    language_bytes = {"HTML / CSS": 1}

total = sum(language_bytes.values())
languages = sorted(language_bytes.items(), key=lambda x: x[1], reverse=True)[:5]

# SVG helpers.
def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

colors = ["#58a6ff", "#f78166", "#3fb950", "#d29922", "#bc8cff"]

W, H = 1000, 340
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
svg.append('<rect width="1000" height="340" rx="18" fill="#0d1117"/>')
svg.append('<text x="35" y="40" fill="#f0f6fc" font-family="Arial,sans-serif" font-size="22" font-weight="700">GitHub Progress &amp; Stats</text>')
svg.append(f'<text x="35" y="65" fill="#8b949e" font-family="Arial,sans-serif" font-size="13">{data["totalContributions"]} contributions in the last year</text>')

# Contribution line chart.
chart_x, chart_y, chart_w, chart_h = 40, 100, 560, 185
svg.append(f'<line x1="{chart_x}" y1="{chart_y+chart_h}" x2="{chart_x+chart_w}" y2="{chart_y+chart_h}" stroke="#30363d"/>')
svg.append(f'<line x1="{chart_x}" y1="{chart_y}" x2="{chart_x}" y2="{chart_y+chart_h}" stroke="#30363d"/>')
maxv = max(weeks or [1])
points = []
for i, value in enumerate(weeks or [0]):
    x = chart_x + (chart_w * i / max(1, len(weeks)-1))
    y = chart_y + chart_h - (chart_h * value / maxv if maxv else 0)
    points.append(f"{x:.1f},{y:.1f}")
svg.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="#58a6ff" stroke-width="4"/>')
for i, value in enumerate(weeks):
    x = chart_x + (chart_w * i / max(1, len(weeks)-1))
    y = chart_y + chart_h - (chart_h * value / maxv if maxv else 0)
    svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#58a6ff"/>')
svg.append('<text x="40" y="312" fill="#8b949e" font-family="Arial,sans-serif" font-size="12">Weekly contribution trend · last 12 weeks</text>')

# Pie chart.
cx, cy, radius = 750, 185, 82
start_angle = -90
for idx, (lang, amount) in enumerate(languages):
    pct = amount / total if total else 0
    end_angle = start_angle + pct * 360
    import math
    x1 = cx + radius * math.cos(math.radians(start_angle))
    y1 = cy + radius * math.sin(math.radians(start_angle))
    x2 = cx + radius * math.cos(math.radians(end_angle))
    y2 = cy + radius * math.sin(math.radians(end_angle))
    large = 1 if end_angle - start_angle > 180 else 0
    svg.append(f'<path d="M {cx} {cy} L {x1:.1f} {y1:.1f} A {radius} {radius} 0 {large} 1 {x2:.1f} {y2:.1f} Z" fill="{colors[idx]}"/>')
    start_angle = end_angle
svg.append(f'<circle cx="{cx}" cy="{cy}" r="42" fill="#0d1117"/>')
svg.append(f'<text x="{cx}" y="{cy-3}" text-anchor="middle" fill="#f0f6fc" font-family="Arial,sans-serif" font-size="20" font-weight="700">{len(languages)}</text>')
svg.append(f'<text x="{cx}" y="{cy+16}" text-anchor="middle" fill="#8b949e" font-family="Arial,sans-serif" font-size="11">languages</text>')

for idx, (lang, amount) in enumerate(languages):
    y = 95 + idx * 30
    pct = amount / total * 100 if total else 0
    svg.append(f'<circle cx="870" cy="{y}" r="5" fill="{colors[idx]}"/>')
    svg.append(f'<text x="885" y="{y+4}" fill="#c9d1d9" font-family="Arial,sans-serif" font-size="12">{esc(lang)} · {pct:.1f}%</text>')

svg.append('</svg>')
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("".join(svg), encoding="utf-8")
