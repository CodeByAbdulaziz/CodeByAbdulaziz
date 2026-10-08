"""Draw the contribution calendar that is visible on a public GitHub profile."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import urllib.request
from datetime import date, datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path

USERNAME = "CodeByAbdulaziz"
SOURCE = f"https://github.com/users/{USERNAME}/contributions"
ROOT = Path(__file__).resolve().parents[1]
COLORS = ("#172638", "#155e75", "#0891b2", "#38bdf8", "#34d399")


class CalendarParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cells: list[tuple[str, str, str]] = []
        self.tooltips: dict[str, str] = {}
        self.active_tooltip: str | None = None
        self.tooltip_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = (values.get("class") or "").split()
        if "ContributionCalendar-day" in classes and values.get("data-date"):
            for key in ("id", "data-date", "data-level"):
                if not values.get(key) or sum(name == key for name, _ in attrs) != 1:
                    raise ValueError(f"Missing or repeated calendar attribute: {key}")
            self.cells.append((values["id"], values["data-date"], values["data-level"]))
        if tag == "tool-tip" and values.get("for"):
            if self.active_tooltip is not None:
                raise ValueError("Nested calendar tooltips")
            self.active_tooltip = values["for"]
            self.tooltip_text = []

    def handle_data(self, data: str) -> None:
        if self.active_tooltip is not None:
            self.tooltip_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "tool-tip" and self.active_tooltip is not None:
            if self.active_tooltip in self.tooltips:
                raise ValueError("Repeated calendar tooltip")
            self.tooltips[self.active_tooltip] = " ".join("".join(self.tooltip_text).split())
            self.active_tooltip = None


def tooltip_count(text: str) -> int | None:
    if re.match(r"^No contributions on\b", text):
        return 0
    match = re.match(r"^((?:\d{1,3}(?:,\d{3})+)|\d+) contributions? on\b", text)
    return int(match[1].replace(",", "")) if match else None


def parse_calendar(html: str, as_of: date) -> list[dict[str, object]]:
    parser = CalendarParser()
    parser.feed(html)
    parser.close()
    if parser.active_tooltip is not None:
        raise ValueError("Incomplete calendar tooltip")
    if not 365 <= len(parser.cells) <= 372:
        raise ValueError("Expected a full year of contribution days")

    days: list[dict[str, object]] = []
    seen_dates: set[str] = set()
    seen_ids: set[str] = set()
    for cell_id, day_text, level_text in parser.cells:
        day = date.fromisoformat(day_text)
        if day.isoformat() != day_text:
            raise ValueError("Calendar date must use YYYY-MM-DD")
        if day_text in seen_dates or cell_id in seen_ids:
            raise ValueError("Repeated calendar day or cell ID")
        if level_text not in {"0", "1", "2", "3", "4"}:
            raise ValueError("Contribution level is outside 0 to 4")
        seen_dates.add(day_text)
        seen_ids.add(cell_id)
        level = int(level_text)
        count = tooltip_count(parser.tooltips.get(cell_id, ""))
        if count is not None and ((count == 0) != (level == 0)):
            raise ValueError("Contribution count and intensity disagree")
        days.append({"date": day_text, "level": level, "count": count})

    days.sort(key=lambda item: str(item["date"]))
    first = date.fromisoformat(str(days[0]["date"]))
    last = date.fromisoformat(str(days[-1]["date"]))
    if first.weekday() != 6:
        raise ValueError("Contribution calendar must start on Sunday")
    if not 0 <= (as_of - last).days <= 2:
        raise ValueError("Contribution calendar is stale or in the future")
    if (last - first).days + 1 != len(days):
        raise ValueError("Contribution dates have gaps")
    return days


def render_svg(days: list[dict[str, object]], as_of: date) -> str:
    first = date.fromisoformat(str(days[0]["date"]))
    last = date.fromisoformat(str(days[-1]["date"]))
    weeks = (last - first).days // 7 + 1
    step = min(17, 916 / weeks)
    cell = step - 4
    counts = [day["count"] for day in days]
    summary = (
        f"{sum(counts):,} contributions in the visible calendar"
        if all(isinstance(count, int) for count in counts)
        else "Activity levels from the visible calendar"
    )
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="290" viewBox="0 0 1000 290" role="img" aria-labelledby="title desc">',
        '<title id="title">CodeByAbdulaziz: GitHub contribution calendar</title>',
        f'<desc id="desc">{escape(summary)}. {first} to {last}. Updated {as_of} UTC. Brighter squares mean more activity.</desc>',
        '<style>.week{animation:reveal .7s ease-out both}@keyframes reveal{from{opacity:.25}to{opacity:1}}@media(prefers-reduced-motion:reduce){.week{animation:none}}</style>',
        '<rect width="1000" height="290" rx="20" fill="#0b1220"/>',
        '<rect x="30" y="26" width="4" height="20" rx="2" fill="#34d399"/>',
        '<g font-family="Arial,sans-serif">',
        '<text x="46" y="42" fill="#f8fafc" font-size="20" font-weight="700">A year of building</text>',
        f'<text x="30" y="68" fill="#94a3b8" font-size="13">{escape(summary)}</text>',
    ]
    months_seen: set[tuple[int, int]] = set()
    for week in range(weeks):
        start = first + timedelta(days=week * 7)
        middle = min(start + timedelta(days=3), last)
        month_key = (middle.year, middle.month)
        if month_key not in months_seen:
            months_seen.add(month_key)
            parts.append(f'<text x="{62 + week * step:.1f}" y="96" fill="#94a3b8" font-size="11">{middle:%b}</text>')
        parts.append(f'<g class="week" style="animation-delay:{week * .012:.3f}s">')
        for offset in range(7):
            index = week * 7 + offset
            if index >= len(days):
                break
            day = days[index]
            label = (
                f'{day["date"]}: {day["count"]} contributions'
                if day["count"] is not None
                else f'{day["date"]}: activity level {day["level"]} of 4; count unavailable'
            )
            parts.append(
                f'<rect x="{62 + week * step:.1f}" y="{108 + offset * 17}" width="{cell:.1f}" height="13" rx="3" fill="{COLORS[int(day["level"])]}"><title>{escape(label)}</title></rect>'
            )
        parts.append('</g>')
    for name, offset in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        parts.append(f'<text x="30" y="{118 + offset * 17}" fill="#94a3b8" font-size="10">{name}</text>')
    parts.append('<text x="819" y="244" fill="#94a3b8" font-size="10">Less</text>')
    for index, color in enumerate(COLORS):
        parts.append(f'<rect x="{848 + index * 17}" y="234" width="13" height="13" rx="3" fill="{color}"/>')
    parts.extend([
        '<text x="937" y="244" fill="#94a3b8" font-size="10">More</text>',
        f'<text x="30" y="244" fill="#cbd5e1" font-size="11">{first:%d %b %Y} — {last:%d %b %Y}</text>',
        f'<text x="30" y="270" fill="#94a3b8" font-size="11">Public GitHub profile calendar · Updated {as_of} UTC</text>',
        '</g></svg>\n',
    ])
    return "\n".join(parts)


def fetch_calendar() -> str:
    request = urllib.request.Request(SOURCE, headers={"User-Agent": f"{USERNAME}-profile-calendar", "Accept": "text/html"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("Calendar response is unexpectedly large")
    return raw.decode("utf-8")


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            file.write(content)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def update_outputs(html: str, as_of: date, root: Path) -> list[dict[str, object]]:
    # Validate and render before touching either saved file.
    days = parse_calendar(html, as_of)
    svg = render_svg(days, as_of)
    payload = {"username": USERNAME, "source": SOURCE, "as_of_utc": as_of.isoformat(), "days": days}
    atomic_write(root / "data/activity.json", json.dumps(payload, separators=(",", ":")) + "\n")
    atomic_write(root / "assets/activity.svg", svg)
    return days


def main() -> int:
    try:
        days = update_outputs(fetch_calendar(), datetime.now(timezone.utc).date(), ROOT)
    except (OSError, ValueError) as error:
        print(f"Could not update activity: {error}", file=sys.stderr)
        return 1
    print(f"Updated {len(days)} contribution days from the public profile calendar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
