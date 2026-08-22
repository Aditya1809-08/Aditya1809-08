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

# Current streak: count consecutive contribution days ending today; if today is empty,
# allow the streak to end yesterday.
today = date.today()
end = today if counts.get(today, 0) > 0 else today - timedelta(days=1)
current = 0
cursor = end
while counts.get(cursor, 0) > 0:
    current += 1
    cursor -= timedelta(days=1)

# Longest streak across the full contribution calendar.
longest = 0
run = 0
for d, c in days:
    if c > 0:
        run += 1
        longest = max(longest, run)
    else:
        run = 0

# SVG helpers
W, H = 900, 300
BG = "#0d1117"
PANEL = "#161b22"
BORDER = "#30363d"
TEXT = "#f0f6fc"
MUTED = "#8b949e"
BLUE = "#58a6ff"
GREEN = "#3fb950"
ORANGE = "#f78166"
R = 72
CIRC = 2 * math.pi * R


def donut(cx, cy, value, label, color, max_value=None):
    # For total contributions, use a capped visual fill; the center text remains exact.
    if max_value is None:
        max_value = max(1, value)
    ratio = min(1, value / max_value) if max_value else 0
    dash = CIRC * ratio
    return f'''<g>
  <circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{BORDER}" stroke-width="16"/>
  <circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{color}" stroke-width="16" stroke-linecap="round" stroke-dasharray="{dash:.2f} {CIRC:.2f}" transform="rotate(-90 {cx} {cy})"/>
  <text x="{cx}" y="{cy+7}" text-anchor="middle" fill="{TEXT}" font-size="28" font-weight="700" font-family="Arial, sans-serif">{value}</text>
  <text x="{cx}" y="{cy+105}" text-anchor="middle" fill="{TEXT}" font-size="18" font-weight="700" font-family="Arial, sans-serif">{label}</text>
</g>'''

# Use the maximum of the three values only for visual balance; numbers remain exact.
max_streak = max(1, longest)
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<rect width="{W}" height="{H}" rx="18" fill="{BG}"/>
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="18" fill="none" stroke="{BORDER}"/>
<text x="32" y="38" fill="{TEXT}" font-size="22" font-weight="700" font-family="Arial, sans-serif">Contribution Pulse</text>
<text x="32" y="64" fill="{MUTED}" font-size="14" font-family="Arial, sans-serif">Live data from your GitHub contribution calendar</text>
{donut(180, 145, total, 'Total Contributions', BLUE, max(1, total))}
{donut(450, 145, current, 'Current Streak', GREEN, max_streak)}
{donut(720, 145, longest, 'Longest Streak', ORANGE, max_streak)}
</svg>'''

os.makedirs("assets", exist_ok=True)
open("assets/contribution-pulse.svg", "w", encoding="utf-8").write(svg)
