import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from xml.etree import ElementTree

from scripts.update_activity import ROOT, parse_calendar, render_svg, update_outputs

AS_OF = date(2026, 10, 8)
START = date(2025, 10, 5)
LENGTH = (AS_OF - START).days + 1


def calendar_html(*, missing_count=False, reversed_cells=False):
    cells = []
    for index in range(LENGTH):
        day = START + timedelta(days=index)
        count = 7 if index == LENGTH - 1 else 0
        level = 3 if count else 0
        cell = f'<td class="ContributionCalendar-day" id="day-{index}" data-date="{day}" data-level="{level}"></td>'
        if not missing_count:
            text = "7 contributions on October 8th." if count else "No contributions on a day."
            cell += f'<tool-tip for="day-{index}"><span>{text}</span></tool-tip>'
        cells.append(cell)
    if reversed_cells:
        cells.reverse()
    return "<table>" + "".join(cells) + "</table>"


class CalendarTests(unittest.TestCase):
    def test_real_values_are_sorted_and_tooltip_text_is_joined(self):
        days = parse_calendar(calendar_html(reversed_cells=True), AS_OF)
        self.assertEqual(len(days), LENGTH)
        self.assertEqual(days[0], {"date": START.isoformat(), "level": 0, "count": 0})
        self.assertEqual(days[-1], {"date": AS_OF.isoformat(), "level": 3, "count": 7})

    def test_missing_counts_do_not_become_estimates(self):
        days = parse_calendar(calendar_html(missing_count=True), AS_OF)
        self.assertTrue(all(day["count"] is None for day in days))
        svg = render_svg(days, AS_OF)
        self.assertIn("Activity levels from the visible calendar", svg)
        self.assertIn("count unavailable", svg)
        self.assertNotIn("7 contributions", svg)

    def test_thousands_and_one_contribution(self):
        html = calendar_html().replace("7 contributions on October 8th.", "1,234 contributions on October 8th.")
        self.assertEqual(parse_calendar(html, AS_OF)[-1]["count"], 1234)
        html = html.replace("1,234 contributions", "1 contribution")
        self.assertEqual(parse_calendar(html, AS_OF)[-1]["count"], 1)

    def test_duplicate_dates_ids_and_invalid_dates_are_rejected(self):
        html = calendar_html()
        variants = [
            html.replace('data-date="2025-10-06"', 'data-date="2025-10-05"'),
            html.replace('id="day-1"', 'id="day-0"'),
            html.replace('data-date="2025-10-06"', 'data-date="2025-02-30"'),
            html.replace('data-date="2025-10-06"', 'data-date="2025-10-6"'),
        ]
        for candidate in variants:
            with self.subTest(candidate=candidate[:100]), self.assertRaises(ValueError):
                parse_calendar(candidate, AS_OF)

    def test_invalid_levels_mismatched_counts_and_truncated_html_are_rejected(self):
        html = calendar_html()
        variants = [
            html.replace('data-level="3"', 'data-level="5"'),
            html.replace('data-level="3"', 'data-level="0"'),
            html.replace('data-level="3"', ''),
            html + '<tool-tip for="extra">incomplete',
            '<html>Sign in to continue</html>',
        ]
        for candidate in variants:
            with self.subTest(candidate=candidate[:100]), self.assertRaises(ValueError):
                parse_calendar(candidate, AS_OF)

    def test_gaps_future_days_and_stale_calendar_are_rejected(self):
        html = calendar_html()
        with self.assertRaises(ValueError):
            parse_calendar(html.replace('data-date="2025-10-06"', 'data-date="2025-10-04"'), AS_OF)
        with self.assertRaises(ValueError):
            parse_calendar(html, AS_OF - timedelta(days=1))
        with self.assertRaises(ValueError):
            parse_calendar(html, AS_OF + timedelta(days=3))

    def test_svg_is_valid_and_has_one_square_for_each_day(self):
        svg = render_svg(parse_calendar(calendar_html(), AS_OF), AS_OF)
        tree = ElementTree.fromstring(svg)
        squares = tree.findall('.//{http://www.w3.org/2000/svg}rect/{http://www.w3.org/2000/svg}title')
        self.assertEqual(len(squares), LENGTH)
        self.assertEqual(tree.attrib["width"], "1000")
        self.assertIn("7 contributions in the visible calendar", svg)
        self.assertIn("Updated 2026-10-08 UTC", svg)
        self.assertIn("prefers-reduced-motion", svg)

    def test_bad_response_preserves_both_saved_outputs(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            update_outputs(calendar_html(), AS_OF, root)
            data_path, svg_path = root / "data/activity.json", root / "assets/activity.svg"
            old_data, old_svg = data_path.read_bytes(), svg_path.read_bytes()
            with self.assertRaises(ValueError):
                update_outputs("empty response", AS_OF, root)
            self.assertEqual(data_path.read_bytes(), old_data)
            self.assertEqual(svg_path.read_bytes(), old_svg)
            self.assertEqual(json.loads(old_data)["days"][-1]["count"], 7)


if __name__ == "__main__":
    unittest.main()
