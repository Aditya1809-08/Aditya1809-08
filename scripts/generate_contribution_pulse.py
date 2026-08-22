import json, math, os
from datetime import date, timedelta

DATA = json.load(open("/tmp/contributions.json", encoding="utf-8"))
weeks = DATA["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]

days = []
for week in weeks:
    for cell in week["contributionDays"]:
        days.append((date.fromisoformat(cell["date"]), cell["contributionCount"]))
days.sort()

total = sum(c for _, c in days)
counts = {d: c for d, c in days}

today = date.today()
end = today if counts.get(today, 0) > 0 else today - timedelta(days=1)
current = 0
cursor = end
while counts.get(cursor, 0) > 0:
    current += 1
    cursor -= timedelta(days=1)

longest = 0
run = 0
for _, count in days:
    if count > 0:
        run += 1
        longest = max(longest, run)
    else:
        run = 0

W, H = 900, 360
BG = "#0d1117"
CARD = "#151b23"
BORDER = "#30363d"
TEXT = "#f0f6fc"
MUTED = "#8b949e"
BLUE = "#58a6ff"
GREEN = "#3fb950"
ORANGE = "#f78166"
TRACK = "#252c35"
R = 54
CIRC = 2 * math.pi * R


def card(x, title, value, ratio, descriptor, gradient_id):
    ratio = max(0, min(1, ratio))
    dash = CIRC * ratio
    cx = x + 125
    cy = 185
    return f'''<g>
  <rect x="{x}" y="92" width="250" height="238" rx="18" fill="{CARD}" stroke="{BORDER}"/>
  <circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{TRACK}" stroke-width="12"/>
  <circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="url(#{gradient_id})" stroke-width="12" stroke-linecap="round" stroke-dasharray="{dash:.2f} {CIRC:.2f}" transform="rotate(-90 {cx} {cy})"/>
  <text x="{cx}" y="{cy+9}" text-anchor="middle" fill="{TEXT}" font-size="30" font-weight="800" font-family="Arial, sans-serif">{value}</text>
  <text x="{cx}" y="266" text-anchor="middle" fill="{TEXT}" font-size="17" font-weight="700" font-family="Arial, sans-serif">{title}</text>
  <text x="{cx}" y="290" text-anchor="middle" fill="{MUTED}" font-size="12" font-family="Arial, sans-serif">{descriptor}</text>
</g>'''

max_streak = max(1, longest)
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <linearGradient id="blue" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#79c0ff"/><stop offset="1" stop-color="#388bfd"/></linearGradient>
  <linearGradient id="green" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#56d364"/><stop offset="1" stop-color="#2ea043"/></linearGradient>
  <linearGradient id="orange" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ff9b7a"/><stop offset="1" stop-color="#f85149"/></linearGradient>
</defs>
<rect width="{W}" height="{H}" rx="20" fill="{BG}"/>
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="20" fill="none" stroke="{BORDER}"/>
<text x="32" y="42" fill="{TEXT}" font-size="23" font-weight="800" font-family="Arial, sans-serif">Contribution Pulse</text>
<text x="32" y="67" fill="{MUTED}" font-size="13" font-family="Arial, sans-serif">Live snapshot from your GitHub contribution calendar</text>
<rect x="758" y="27" width="110" height="30" rx="15" fill="#12261a" stroke="#238636"/>
<circle cx="777" cy="42" r="5" fill="{GREEN}"/>
<text x="789" y="47" fill="#7ee787" font-size="12" font-weight="700" font-family="Arial, sans-serif">LIVE DATA</text>
{card(30, 'Total Contributions', total, 1, 'this contribution year', 'blue')}
{card(325, 'Current Streak', current, current / max_streak, 'days in a row', 'green')}
{card(620, 'Longest Streak', longest, 1, 'best streak recorded', 'orange')}
</svg>'''

os.makedirs("assets", exist_ok=True)
open("assets/contribution-pulse.svg", "w", encoding="utf-8").write(svg)
