import json, math, os
from datetime import date, timedelta

DATA = json.load(open("/tmp/contributions.json", encoding="utf-8"))
weeks = DATA["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]

days = []
for week in weeks:
    for cell in week["contributionDays"]:
        days.append((date.fromisoformat(cell["date"]), cell["contributionCount"]))
days.sort()

counts = {d: c for d, c in days}
total = sum(c for _, c in days)

today = date.today()
end = today if counts.get(today, 0) > 0 else today - timedelta(days=1)
current = 0
cursor = end
while counts.get(cursor, 0) > 0:
    current += 1
    cursor -= timedelta(days=1)
current_start = cursor + timedelta(days=1) if current else None

longest = 0
longest_start = None
longest_end = None
run = 0
run_start = None
for d, count in days:
    if count > 0:
        if run == 0:
            run_start = d
        run += 1
        if run > longest:
            longest = run
            longest_start = run_start
            longest_end = d
    else:
        run = 0
        run_start = None

first_day = days[0][0] if days else today


def fmt(d):
    return d.strftime("%b %-d, %Y")

W, H = 900, 260
BG = "#171824"
TEXT = "#e8e8f2"
MUTED = "#8b90a7"
BLUE = "#69a8ff"
GREEN = "#33c56b"
PURPLE = "#c88cff"

ring_r = 55
circ = 2 * math.pi * ring_r

def donut(cx, cy, value, maximum, color):
    ratio = min(1, value / maximum) if maximum else 0
    dash = circ * ratio
    return f'''<circle cx="{cx}" cy="{cy}" r="{ring_r}" fill="none" stroke="#303141" stroke-width="12"/>
<circle cx="{cx}" cy="{cy}" r="{ring_r}" fill="none" stroke="{color}" stroke-width="12" stroke-linecap="round" stroke-dasharray="{dash:.2f} {circ:.2f}" transform="rotate(-90 {cx} {cy})"/>'''

# Keep the contribution donut meaningful as the total grows.
contribution_max = max(1000, total)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<rect width="{W}" height="{H}" rx="12" fill="{BG}"/>
<text x="450" y="30" text-anchor="middle" fill="{TEXT}" font-size="16" font-weight="700" font-family="Arial, sans-serif">Contribution Overview</text>

{donut(270, 105, total, contribution_max, BLUE)}
<text x="270" y="101" text-anchor="middle" fill="{TEXT}" font-size="24" font-weight="700" font-family="Arial, sans-serif">{total}</text>
<text x="270" y="126" text-anchor="middle" fill="{MUTED}" font-size="13" font-weight="600" font-family="Arial, sans-serif">Total Contributions</text>
<text x="270" y="190" text-anchor="middle" fill="{BLUE}" font-size="12" font-weight="600" font-family="Arial, sans-serif">{fmt(first_day)} - Present</text>

{donut(630, 105, current, max(1, longest), GREEN)}
<text x="630" y="101" text-anchor="middle" fill="{TEXT}" font-size="24" font-weight="700" font-family="Arial, sans-serif">{current}</text>
<text x="630" y="126" text-anchor="middle" fill="{MUTED}" font-size="13" font-weight="600" font-family="Arial, sans-serif">Current Streak</text>
<text x="630" y="158" text-anchor="middle" fill="{PURPLE}" font-size="12" font-weight="600" font-family="Arial, sans-serif">Longest: {longest} days</text>
<text x="630" y="190" text-anchor="middle" fill="{GREEN}" font-size="12" font-weight="600" font-family="Arial, sans-serif">{fmt(current_start) if current_start else 'No active streak'}</text>
</svg>'''

os.makedirs("assets", exist_ok=True)
open("assets/contribution-pulse.svg", "w", encoding="utf-8").write(svg)
