import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

USER = "Aditya1809-08"
OUT = Path("assets/github-stats.svg")
TOKEN = os.environ["GITHUB_TOKEN"]
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

QUERY = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      totalContributions
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""

now = datetime.now(timezone.utc)
start = now - timedelta(days=365)
r = requests.post("https://api.github.com/graphql", json={"query": QUERY, "variables": {"login": USER, "from": start.isoformat(), "to": now.isoformat()}}, headers=HEADERS, timeout=30)
r.raise_for_status()
body = r.json()
if body.get("errors"):
    raise RuntimeError(body["errors"])
data = body["data"]["user"]["contributionsCollection"]
daily = sorted([d for w in data["contributionCalendar"]["weeks"] for d in w["contributionDays"]], key=lambda x: x["date"])

# Streaks.
longest = run = 0
for day in daily:
    if day["contributionCount"] > 0:
        run += 1
        longest = max(longest, run)
    else:
        run = 0
current = 0
for day in reversed(daily):
    if day["contributionCount"] > 0:
        current += 1
    elif day["date"] == now.date().isoformat():
        continue
    else:
        break

# Weekly progress.
weekly = []
for i in range(0, len(daily), 7):
    chunk = daily[i:i+7]
    if chunk:
        weekly.append((chunk[0]["date"], sum(x["contributionCount"] for x in chunk)))
weekly = weekly[-26:]

# Public-repository language distribution.
repos, page = [], 1
while True:
    rr = requests.get(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}", timeout=30)
    rr.raise_for_status()
    batch = rr.json(); repos.extend(batch)
    if len(batch) < 100: break
    page += 1
language_bytes = {}
for repo in repos:
    if repo.get("fork"): continue
    lr = requests.get(repo["languages_url"], timeout=30)
    if lr.ok:
        for lang, amount in lr.json().items():
            language_bytes[lang] = language_bytes.get(lang, 0) + amount
if not language_bytes: language_bytes = {"HTML": 1}
languages = sorted(language_bytes.items(), key=lambda x: x[1], reverse=True)[:6]
total_bytes = sum(x[1] for x in languages)

# Overall commits: sum commit counts returned by GitHub for each public repo.
overall_commits = 0
for repo in repos:
    if repo.get("fork"): continue
    cr = requests.get(f"https://api.github.com/repos/{repo['full_name']}/commits?author={USER}&per_page=1", timeout=30)
    if not cr.ok: continue
    link = cr.headers.get("Link", "")
    import re
    match = re.search(r'page=(\d+)>; rel="last"', link)
    overall_commits += int(match.group(1)) if match else len(cr.json())
if overall_commits == 0:
    overall_commits = data["totalCommitContributions"]


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def txt(x, y, value, size=13, fill="#c9d1d9", weight="400", anchor="start"):
    return f'<text x="{x}" y="{y}" fill="{fill}" font-family="Arial,sans-serif" font-size="{size}px" font-weight="{weight}" text-anchor="{anchor}">{esc(value)}</text>'

W, H = 1100, 690
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', '<rect width="1100" height="690" rx="20" fill="#0d1117" stroke="#30363d"/>']
svg.append(txt(35, 42, "GitHub Progress", 24, "#f0f6fc", "700"))
svg.append(txt(35, 67, "Daily-updating contribution dashboard", 13, "#8b949e"))

# Four visual KPI cards.
stats = [("TOTAL COMMITS", overall_commits), ("CONTRIBUTIONS", data["totalContributions"]), ("CURRENT STREAK", f"{current} days"), ("LONGEST STREAK", f"{longest} days")]
for i, (label, value) in enumerate(stats):
    x = 35 + i * 265
    svg.append(f'<rect x="{x}" y="88" width="245" height="82" rx="12" fill="#161b22" stroke="#30363d"/>')
    svg.append(txt(x+18, 113, label, 10, "#8b949e", "700"))
    svg.append(txt(x+18, 148, value, 25, "#f0f6fc", "700"))

# Detailed 26-week progress graph.
chart_x, chart_y, chart_w, chart_h = 45, 205, 670, 205
svg.append(txt(45, 193, "Contribution Progress · 26 Weeks", 15, "#f0f6fc", "700"))
maxv = max([v for _, v in weekly] or [1])
for grid in range(5):
    y = chart_y + chart_h - chart_h * grid / 4
    svg.append(f'<line x1="{chart_x}" y1="{y:.1f}" x2="{chart_x+chart_w}" y2="{y:.1f}" stroke="#21262d"/>')
points = []
for i, (_, value) in enumerate(weekly):
    x = chart_x + chart_w * i / max(1, len(weekly)-1)
    y = chart_y + chart_h - chart_h * value / maxv
    points.append((x, y, value))
if points:
    area = f"{chart_x},{chart_y+chart_h} " + " ".join(f"{x:.1f},{y:.1f}" for x,y,_ in points) + f" {chart_x+chart_w},{chart_y+chart_h}"
    svg.append(f'<polygon points="{area}" fill="#58a6ff" opacity="0.12"/>')
    svg.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y,_ in points)}" fill="none" stroke="#58a6ff" stroke-width="3" stroke-linecap="round"/>')
    for x,y,value in points:
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#58a6ff"><title>{value} contributions</title></circle>')
svg.append(txt(45, 430, "Weekly contributions · hover points for exact values", 10, "#6e7681"))

# GitHub-style daily heatmap.
svg.append(txt(45, 465, "Daily Progress · Last 365 Days", 15, "#f0f6fc", "700"))
heat_x, heat_y, cell, gap = 45, 485, 11, 3
weeks = []
for i in range(0, len(daily), 7):
    chunk = daily[i:i+7]
    if chunk: weeks.append(chunk)
weeks = weeks[-53:]
level_color = {"NONE":"#161b22", "FIRST_QUARTILE":"#0e4429", "SECOND_QUARTILE":"#006d32", "THIRD_QUARTILE":"#26a641", "FOURTH_QUARTILE":"#39d353"}
for wx, week in enumerate(weeks):
    for dy, day in enumerate(week):
        x, y = heat_x + wx*(cell+gap), heat_y + dy*(cell+gap)
        c = level_color.get(day.get("contributionLevel"), "#161b22")
        svg.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{c}"><title>{day["date"]}: {day["contributionCount"]} contributions</title></rect>')
svg.append(txt(45, 585, "Less", 10, "#6e7681"))
for i,c in enumerate(level_color.values()): svg.append(f'<rect x="75" y="576" width="11" height="11" rx="2" fill="{c}"/>')
svg.append(txt(151, 585, "More", 10, "#6e7681"))

# Donut language chart.
cx, cy, radius = 850, 300, 83
colors = ["#58a6ff", "#3fb950", "#f78166", "#d29922", "#bc8cff", "#79c0ff"]
angle = -90
for i,(lang,amount) in enumerate(languages):
    frac = amount/total_bytes if total_bytes else 0; end = angle + frac*360
    x1,y1 = cx+radius*math.cos(math.radians(angle)), cy+radius*math.sin(math.radians(angle))
    x2,y2 = cx+radius*math.cos(math.radians(end)), cy+radius*math.sin(math.radians(end))
    large = 1 if end-angle>180 else 0
    svg.append(f'<path d="M {cx} {cy} L {x1:.1f} {y1:.1f} A {radius} {radius} 0 {large} 1 {x2:.1f} {y2:.1f} Z" fill="{colors[i]}"/>')
    angle=end
svg.append(f'<circle cx="{cx}" cy="{cy}" r="43" fill="#0d1117"/>')
svg.append(txt(cx, cy-3, str(len(languages)), 20, "#f0f6fc", "700", "middle"))
svg.append(txt(cx, cy+16, "languages", 11, "#8b949e", "400", "middle"))
svg.append(txt(760, 420, "Language Distribution", 14, "#f0f6fc", "700"))
for i,(lang,amount) in enumerate(languages):
    y=445+i*28; pct=amount/total_bytes*100 if total_bytes else 0
    svg.append(f'<circle cx="765" cy="{y-4}" r="5" fill="{colors[i]}"/>')
    svg.append(txt(778,y,f"{lang} · {pct:.1f}%",11,"#c9d1d9"))

# Contribution-type mini bars.
svg.append(txt(900, 205, "Contribution Types", 12, "#f0f6fc", "700"))
types=[("Commits",data["totalCommitContributions"]),("Pull Requests",data["totalPullRequestContributions"]),("Issues",data["totalIssueContributions"])]
for i,(label,value) in enumerate(types):
    y=230+i*27; bar=max(1, int(130*value/max(1,data["totalContributions"])))
    svg.append(txt(900,y,label,10,"#8b949e"))
    svg.append(f'<rect x="900" y="{y+6}" width="130" height="6" rx="3" fill="#21262d"/><rect x="900" y="{y+6}" width="{bar}" height="6" rx="3" fill="#58a6ff"/>')
    svg.append(txt(1055,y+5,str(value),10,"#f0f6fc","700","end"))

svg.append('</svg>')
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("".join(svg), encoding="utf-8")
