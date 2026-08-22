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

W, H = 900, 230
BG = "#171824"
DIVIDER = "#777887"
TEXT = "#e8e8f2"
MUTED = "#6f7ea6"
BLUE = "#69a8ff"
GREEN = "#33c56b"
PURPLE = "#c88cff"

ring_r = 44
circ = 2 * math.pi * ring_r
ratio = (current / longest) if longest else 0
ring_dash = circ * min(1, ratio)

flame = '''<path d="M450 38 C444 30 452 23 451 14 C464 24 471 33 467 43 C464 50 458 54 450 54 C441 54 435 48 435 40 C435 35 438 31 442 27 C442 34 445 38 450 38 Z" fill="none" stroke="#69a8ff" stroke-width="3" stroke-linejoin="round"/>'''

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<rect width="{W}" height="{H}" rx="4" fill="{BG}"/>
<line x1="300" y1="28" x2="300" y2="202" stroke="{DIVIDER}" stroke-width="2"/>
<line x1="600" y1="28" x2="600" y2="202" stroke="{DIVIDER}" stroke-width="2"/>

<text x="150" y="82" text-anchor="middle" fill="{BLUE}" font-size="28" font-weight="700" font-family="Arial, sans-serif">{total}</text>
<text x="150" y="118" text-anchor="middle" fill="{MUTED}" font-size="15" font-weight="600" font-family="Arial, sans-serif">Total Contributions</text>
<text x="150" y="146" text-anchor="middle" fill="{GREEN}" font-size="12" font-weight="600" font-family="Arial, sans-serif">{fmt(first_day)} - Present</text>

<circle cx="450" cy="72" r="44" fill="none" stroke="#303141" stroke-width="6"/>
<circle cx="450" cy="72" r="44" fill="none" stroke="{GREEN}" stroke-width="6" stroke-linecap="round" stroke-dasharray="{ring_dash:.2f} {circ:.2f}" transform="rotate(-90 450 72)"/>
{flame}
<text x="450" y="82" text-anchor="middle" fill="{TEXT}" font-size="26" font-weight="700" font-family="Arial, sans-serif">{current}</text>
<text x="450" y="118" text-anchor="middle" fill="{PURPLE}" font-size="15" font-weight="600" font-family="Arial, sans-serif">Current Streak</text>
<text x="450" y="146" text-anchor="middle" fill="{GREEN}" font-size="12" font-weight="600" font-family="Arial, sans-serif">{fmt(current_start) if current_start else 'No active streak'}</text>

<text x="750" y="82" text-anchor="middle" fill="{BLUE}" font-size="28" font-weight="700" font-family="Arial, sans-serif">{longest}</text>
<text x="750" y="118" text-anchor="middle" fill="{MUTED}" font-size="15" font-weight="600" font-family="Arial, sans-serif">Longest Streak</text>
<text x="750" y="146" text-anchor="middle" fill="{GREEN}" font-size="12" font-weight="600" font-family="Arial, sans-serif">{fmt(longest_start)} - {fmt(longest_end)}</text>
</svg>'''

os.makedirs("assets", exist_ok=True)
open("assets/contribution-pulse.svg", "w", encoding="utf-8").write(svg)
