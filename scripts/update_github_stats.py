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
    followers { totalCount }
    repositories(first:100, ownerAffiliations: OWNER) { totalCount }
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
user = body["data"]["user"]
data = user["contributionsCollection"]

daily = sorted([d for w in data["contributionCalendar"]["weeks"] for d in w["contributionDays"]], key=lambda x: x["date"])

# Current / longest streak.
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

# Weekly progress series.
weekly = []
for i in range(0, len(daily), 7):
    chunk = daily[i:i+7]
    if chunk:
        weekly.append((chunk[0]["date"], sum(x["contributionCount"] for x in chunk)))
weekly = weekly[-26:]

# Public repository language distribution.
repos = []
page = 1
while True:
    rr = requests.get(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}", timeout=30)
    rr.raise_for_status()
    batch = rr.json()
    repos.extend(batch)
    if len(batch) < 100:
        break
    page += 1

language_bytes = {}
for repo in repos:
    if repo.get("fork"):
        continue
    lr = requests.get(repo["languages_url"], timeout=30)
    if lr.ok:
        for lang, amount in lr.json().items():
            language_bytes[lang] = language_bytes.get(lang, 0) + amount
if not language_bytes:
    language_bytes = {"HTML": 1}
languages = sorted(language_bytes.items(), key=lambda x: x[1], reverse=True)[:6]
lang_total = sum(v for _, v in languages)

# Overall commits from public repositories. Uses GitHub pagination metadata.
overall_commits = 0
import re
for repo in repos:
    if repo.get("fork"):
        continue
    cr = requests.get(f"https://api.github.com/repos/{repo['full_name']}/commits?author={USER}&per_page=1", timeout=30)
    if not cr.ok:
        continue
    link = cr.headers.get("Link", "")
    m = re.search(r'page=(\d+)>; rel="last"', link)
    overall_commits += int(m.group(1)) if m else len(cr.json())
if overall_commits == 0:
    overall_commits = data["totalCommitContributions"]

# Simple profile activity grade from contributions and streak consistency.
grade = "A" if data["totalContributions"] >= 250 else "B" if data["totalContributions"] >= 120 else "C" if data["totalContributions"] >= 60 else "D"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def txt(x, y, value, size=10, fill="#c9d1d9", weight="400", anchor="start"):
    return f'<text x="{x}" y="{y}" fill="{fill}" font-family="Arial,sans-serif" font-size="{size}px" font-weight="{weight}" text-anchor="{anchor}">{esc(value)}</text>'

W, H = 1100, 560
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
svg.append('<rect width="1100" height="560" rx="18" fill="#0d1117" stroke="#30363d"/>')
svg.append(txt(550, 31, "Statistics", 17, "#f0f6fc", "700", "middle"))
svg.append('<line x1="20" y1="48" x2="1080" y2="48" stroke="#30363d"/>')

# Overview card.
svg.append('<rect x="20" y="64" width="520" height="145" rx="6" fill="#0b0f14" stroke="#30363d"/>')
svg.append(txt(34, 84, "GitHub Overview", 11, "#f0f6fc", "700"))
rows = [
    ("★  Total Contributions", data["totalContributions"]),
    ("⌘  Total Commits", overall_commits),
    ("⑂  Total Pull Requests", data["totalPullRequestContributions"]),
    ("!  Total Issues", data["totalIssueContributions"]),
    ("▣  Repositories", user["repositories"]["totalCount"]),
    ("◌  Contributions (last year)", data["totalContributions"]),
]
for i,(label,val) in enumerate(rows):
    y=108+i*18
    svg.append(txt(34,y,label,9,"#8b949e"))
    svg.append(txt(255,y,str(val),9,"#f0f6fc","700"))
# Grade donut.
cgx,cgy,cr=435,141,39
svg.append(f'<circle cx="{cgx}" cy="{cgy}" r="{cr}" fill="none" stroke="#30363d" stroke-width="8"/>')
arc = {"A": 0.9, "B": 0.75, "C": 0.6, "D": 0.4}[grade]
end= -90 + 360*arc
x1,y1=cgx+cr*math.cos(math.radians(-90)), cgy+cr*math.sin(math.radians(-90))
x2,y2=cgx+cr*math.cos(math.radians(end)), cgy+cr*math.sin(math.radians(end))
large=1 if end+90>180 else 0
svg.append(f'<path d="M {x1:.1f} {y1:.1f} A {cr} {cr} 0 {large} 1 {x2:.1f} {y2:.1f}" fill="none" stroke="#58a6ff" stroke-width="8"/>')
svg.append(txt(cgx,cgy+5,grade,18,"#f0f6fc","700","middle"))
svg.append(txt(cgx,cgy+28,"Grade",9,"#8b949e","400","middle"))

# Summary card.
svg.append('<rect x="558" y="64" width="522" height="145" rx="6" fill="#0b0f14" stroke="#30363d"/>')
svg.append('<line x1="732" y1="80" x2="732" y2="193" stroke="#30363d"/>')
svg.append('<line x1="906" y1="80" x2="906" y2="193" stroke="#30363d"/>')
svg.append(txt(645,112,str(data["totalContributions"]),30,"#f0f6fc","700","middle"))
svg.append(txt(645,136,"Total",10,"#8b949e","400","middle"))
svg.append(txt(645,150,"Contributions",10,"#8b949e","400","middle"))
svg.append(txt(645,172,"Last 365 days",8,"#6e7681","400","middle"))
svg.append(f'<circle cx="819" cy="124" r="37" fill="none" stroke="#30363d" stroke-width="7"/>')
end2 = -90 + min(current/longest if longest else 0,1)*360
x2,y2=819+37*math.cos(math.radians(end2)),124+37*math.sin(math.radians(end2))
large2=1 if end2+90>180 else 0
svg.append(f'<path d="M 819 87 A 37 37 0 {large2} 1 {x2:.1f} {y2:.1f}" fill="none" stroke="#58a6ff" stroke-width="7"/>')
svg.append(txt(819,132,str(current),20,"#f0f6fc","700","middle"))
svg.append(txt(819,160,"Current Streak",10,"#8b949e","400","middle"))
svg.append(txt(993,112,str(longest),30,"#f0f6fc","700","middle"))
svg.append(txt(993,136,"Longest Streak",10,"#8b949e","400","middle"))
svg.append(txt(993,160,"days",8,"#6e7681","400","middle"))

# Contribution graph area.
svg.append('<rect x="20" y="225" width="1060" height="315" rx="6" fill="#0b0f14" stroke="#30363d"/>')
svg.append(txt(550,248,"Contribution Graph",13,"#f0f6fc","700","middle"))
left,top,w,h=70,270,968,218
svg.append(f'<line x1="{left}" y1="{top+h}" x2="{left+w}" y2="{top+h}" stroke="#30363d"/>')
svg.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+h}" stroke="#30363d"/>')
maxv=max([v for _,v in weekly] or [1])
for g in range(1,5):
    y=top+h-(h*g/4)
    svg.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left+w}" y2="{y:.1f}" stroke="#21262d"/>')
points=[]
for i,(_,v) in enumerate(weekly):
    x=left+w*i/max(1,len(weekly)-1)
    y=top+h-h*v/maxv
    points.append((x,y,v))
if points:
    svg.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y,_ in points)}" fill="none" stroke="#f0f6fc" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>')
    for x,y,v in points:
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.8" fill="#f0f6fc"><title>{v} contributions</title></circle>')
# subtle purple area under the line to match reference style.
if points:
    area=f'{left},{top+h} ' + ' '.join(f'{x:.1f},{y:.1f}' for x,y,_ in points) + f' {left+w},{top+h}'
    svg.append(f'<polygon points="{area}" fill="#8a3ffc" opacity="0.12"/>')
    # redraw line on top
    svg.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y,_ in points)}" fill="none" stroke="#f0f6fc" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>')
for g in range(0,5):
    y=top+h-h*g/4
    svg.append(txt(58,y+3,str(round(maxv*g/4)),8,"#6e7681","400","end"))
for i,label in enumerate(["May","Jun","Jul","Aug","Sep","Oct"]):
    x=left+w*i/5
    svg.append(txt(x,507,label,8,"#6e7681","400","middle"))
svg.append(txt(35,385,"Contributions",8,"#6e7681","400","middle"))

svg.append('</svg>')
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("".join(svg),encoding="utf-8")
