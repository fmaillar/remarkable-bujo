from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

from reportlab.pdfgen import canvas


# Native reMarkable 2 display ratio/resolution. PDF units are arbitrary here;
# using the native pixel dimensions makes layout calculations straightforward.
PAGE_WIDTH = 1404.0
PAGE_HEIGHT = 1872.0

MARGIN_X = 72.0
MARGIN_TOP = 84.0
MARGIN_BOTTOM = 72.0

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

MONTH_NAMES = (
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


@dataclass(frozen=True)
class WeekKey:
    iso_year: int
    iso_week: int

    @property
    def destination(self) -> str:
        return f"week-{self.iso_year:04d}-{self.iso_week:02d}"

    @property
    def label(self) -> str:
        return f"W{self.iso_week:02d}"


def _day_destination(day: date) -> str:
    return f"day-{day.isoformat()}"


def _month_destination(year: int, month: int) -> str:
    return f"month-{year:04d}-{month:02d}"


def _reflection_destination(year: int, month: int) -> str:
    return f"reflection-{year:04d}-{month:02d}"


def _monthly_log_destination(year: int, month: int) -> str:
    return f"monthly-log-{year:04d}-{month:02d}"


def _future_log_destination(year: int, page: int) -> str:
    return f"future-log-{year:04d}-{page:02d}"


def _weekly_log_destination(key: WeekKey) -> str:
    return f"weekly-log-{key.iso_year:04d}-{key.iso_week:02d}"


def _all_days(year: int) -> list[date]:
    first = date(year, 1, 1)
    last = date(year, 12, 31)
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


def _all_weeks(year: int) -> list[WeekKey]:
    keys = {
        WeekKey(*day.isocalendar()[:2])
        for day in _all_days(year)
    }
    return sorted(keys, key=lambda key: (key.iso_year, key.iso_week))


def _week_start(key: WeekKey) -> date:
    return date.fromisocalendar(key.iso_year, key.iso_week, 1)


def _draw_header(c: canvas.Canvas, title: str, subtitle: str | None = None) -> None:
    c.setFont(FONT_BOLD, 42)
    c.drawString(MARGIN_X, PAGE_HEIGHT - MARGIN_TOP, title)
    if subtitle:
        c.setFont(FONT, 20)
        c.drawRightString(PAGE_WIDTH - MARGIN_X, PAGE_HEIGHT - MARGIN_TOP + 4, subtitle)


def _draw_footer(c: canvas.Canvas, year: int, *, left: str = "HOME", right: str = "YEAR") -> None:
    y = MARGIN_BOTTOM - 26
    c.setFont(FONT, 16)

    c.drawString(MARGIN_X, y, left)
    c.linkRect(
        "",
        "home",
        (MARGIN_X - 8, y - 8, MARGIN_X + 70, y + 22),
        relative=0,
        thickness=0,
    )

    c.drawRightString(PAGE_WIDTH - MARGIN_X, y, right)
    c.linkRect(
        "",
        f"year-{year}",
        (PAGE_WIDTH - MARGIN_X - 70, y - 8, PAGE_WIDTH - MARGIN_X + 8, y + 22),
        relative=0,
        thickness=0,
    )


def _draw_dot_grid(
    c: canvas.Canvas,
    *,
    top: float,
    bottom: float = MARGIN_BOTTOM,
    left: float = MARGIN_X,
    right: float = PAGE_WIDTH - MARGIN_X,
    spacing: float = 36.0,
) -> None:
    c.saveState()
    c.setFillGray(0.78)
    radius = 1.25
    y = top
    while y >= bottom:
        x = left
        while x <= right:
            c.circle(x, y, radius, stroke=0, fill=1)
            x += spacing
        y -= spacing
    c.restoreState()


def _new_page(c: canvas.Canvas, destination: str) -> None:
    c.bookmarkPage(destination)


def _finish_page(c: canvas.Canvas) -> None:
    c.showPage()


def _draw_home(c: canvas.Canvas, year: int) -> None:
    _new_page(c, "home")
    c.setFont(FONT_BOLD, 68)
    c.drawString(MARGIN_X, PAGE_HEIGHT - 220, f"Bullet Journal {year}")

    items = [
        ("YEAR", f"year-{year}"),
        ("FUTURE LOG", _future_log_destination(year, 1)),
        ("PROJECTS", "projects"),
        ("COLLECTIONS", "collections"),
        ("ANNUAL REFLECTION", f"annual-reflection-{year}"),
    ]
    y = PAGE_HEIGHT - 430
    for label, destination in items:
        c.setFont(FONT_BOLD, 32)
        c.drawString(MARGIN_X, y, label)
        c.linkRect(
            "",
            destination,
            (MARGIN_X - 8, y - 12, MARGIN_X + 420, y + 38),
            relative=0,
            thickness=0,
        )
        y -= 90

    c.setFont(FONT, 18)
    c.drawString(MARGIN_X, MARGIN_BOTTOM, "Minimal. Hyperlinked. Reproducible.")
    _finish_page(c)


def _draw_year(c: canvas.Canvas, year: int) -> None:
    destination = f"year-{year}"
    _new_page(c, destination)
    _draw_header(c, str(year), "YEAR")

    cols = 3
    rows = 4
    gap_x = 28
    gap_y = 34
    top = PAGE_HEIGHT - 190
    usable_w = PAGE_WIDTH - 2 * MARGIN_X
    usable_h = top - 170
    box_w = (usable_w - gap_x * (cols - 1)) / cols
    box_h = (usable_h - gap_y * (rows - 1)) / rows

    for month in range(1, 13):
        idx = month - 1
        row = idx // cols
        col = idx % cols
        x0 = MARGIN_X + col * (box_w + gap_x)
        y1 = top - row * (box_h + gap_y)
        y0 = y1 - box_h

        c.setLineWidth(1)
        c.rect(x0, y0, box_w, box_h, stroke=1, fill=0)
        c.setFont(FONT_BOLD, 26)
        c.drawString(x0 + 18, y1 - 40, MONTH_NAMES[month].upper())

        c.linkRect(
            "",
            _month_destination(year, month),
            (x0, y0, x0 + box_w, y1),
            relative=0,
            thickness=0,
        )

    c.setFont(FONT_BOLD, 18)
    c.drawString(MARGIN_X, 110, "FUTURE LOG")
    c.linkRect(
        "",
        _future_log_destination(year, 1),
        (MARGIN_X - 8, 94, MARGIN_X + 150, 132),
        relative=0,
        thickness=0,
    )

    _draw_footer(c, year)
    _finish_page(c)


def _draw_future_log(c: canvas.Canvas, year: int, page: int) -> None:
    start_month = (page - 1) * 2 + 1
    end_month = min(start_month + 1, 12)
    _new_page(c, _future_log_destination(year, page))
    _draw_header(c, "Future Log", f"{year} · {start_month:02d}-{end_month:02d}")

    top = PAGE_HEIGHT - 210
    bottom = 180
    gap = 42
    section_h = (top - bottom - gap) / 2

    for offset, month in enumerate((start_month, end_month)):
        y1 = top - offset * (section_h + gap)
        y0 = y1 - section_h

        c.setFont(FONT_BOLD, 28)
        c.drawString(MARGIN_X, y1 - 34, MONTH_NAMES[month])

        c.setFont(FONT, 16)
        c.drawRightString(PAGE_WIDTH - MARGIN_X, y1 - 32, "MONTH")
        c.linkRect(
            "",
            _month_destination(year, month),
            (PAGE_WIDTH - MARGIN_X - 90, y1 - 50, PAGE_WIDTH - MARGIN_X + 8, y1 - 12),
            relative=0,
            thickness=0,
        )

        _draw_dot_grid(
            c,
            top=y1 - 78,
            bottom=y0 + 10,
            spacing=36.0,
        )

    nav_y = 112
    c.setFont(FONT, 18)
    if page > 1:
        c.drawString(MARGIN_X, nav_y, "< PREV")
        c.linkRect(
            "",
            _future_log_destination(year, page - 1),
            (MARGIN_X - 8, nav_y - 8, MARGIN_X + 100, nav_y + 24),
            relative=0,
            thickness=0,
        )
    if page < 6:
        c.drawRightString(PAGE_WIDTH - MARGIN_X, nav_y, "NEXT >")
        c.linkRect(
            "",
            _future_log_destination(year, page + 1),
            (PAGE_WIDTH - MARGIN_X - 110, nav_y - 8, PAGE_WIDTH - MARGIN_X + 8, nav_y + 24),
            relative=0,
            thickness=0,
        )

    _draw_footer(c, year)
    _finish_page(c)


def _draw_monthly_log(c: canvas.Canvas, year: int, month: int) -> None:
    _new_page(c, _monthly_log_destination(year, month))
    _draw_header(c, f"{MONTH_NAMES[month]} log", str(year))

    nav_y = PAGE_HEIGHT - 160
    c.setFont(FONT, 18)
    c.drawString(MARGIN_X, nav_y, "< CALENDAR")
    c.linkRect(
        "",
        _month_destination(year, month),
        (MARGIN_X - 8, nav_y - 8, MARGIN_X + 150, nav_y + 24),
        relative=0,
        thickness=0,
    )

    c.drawCentredString(PAGE_WIDTH / 2, nav_y, "MONTHLY LOG")
    c.linkRect(
        "",
        _monthly_log_destination(year, month),
        (PAGE_WIDTH / 2 - 85, nav_y - 8, PAGE_WIDTH / 2 + 85, nav_y + 24),
        relative=0,
        thickness=0,
    )

    _draw_dot_grid(c, top=PAGE_HEIGHT - 225)
    _draw_footer(c, year)
    _finish_page(c)


def _draw_month(c: canvas.Canvas, year: int, month: int) -> None:
    _new_page(c, _month_destination(year, month))
    _draw_header(c, MONTH_NAMES[month], str(year))

    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    weeks = cal.monthdatescalendar(year, month)

    grid_left = MARGIN_X
    grid_right = PAGE_WIDTH - MARGIN_X
    grid_top = PAGE_HEIGHT - 220
    grid_bottom = 300
    cell_w = (grid_right - grid_left) / 7
    cell_h = (grid_top - grid_bottom) / len(weeks)

    c.setFont(FONT_BOLD, 18)
    for col, name in enumerate(WEEKDAY_NAMES):
        x = grid_left + col * cell_w + 8
        c.drawString(x, grid_top + 24, name)

    for row, week in enumerate(weeks):
        y1 = grid_top - row * cell_h
        y0 = y1 - cell_h

        for col, day in enumerate(week):
            x0 = grid_left + col * cell_w
            x1 = x0 + cell_w
            c.rect(x0, y0, cell_w, cell_h, stroke=1, fill=0)

            if day.month == month:
                c.setFont(FONT_BOLD, 20)
                c.drawString(x0 + 10, y1 - 30, str(day.day))
                c.linkRect(
                    "",
                    _day_destination(day),
                    (x0, y0, x1, y1),
                    relative=0,
                    thickness=0,
                )
            else:
                c.setFont(FONT, 16)
                c.setFillGray(0.65)
                c.drawString(x0 + 10, y1 - 28, str(day.day))
                c.setFillGray(0)

        week_key = WeekKey(*week[0].isocalendar()[:2])
        c.setFont(FONT, 14)
        c.drawRightString(grid_left - 12, (y0 + y1) / 2, week_key.label)
        c.linkRect(
            "",
            week_key.destination,
            (grid_left - 60, y0, grid_left - 4, y1),
            relative=0,
            thickness=0,
        )

    y = 230
    c.setFont(FONT_BOLD, 20)

    c.drawString(MARGIN_X, y, "MONTHLY LOG")
    c.linkRect(
        "",
        _monthly_log_destination(year, month),
        (MARGIN_X - 8, y - 10, MARGIN_X + 190, y + 28),
        relative=0,
        thickness=0,
    )

    c.drawRightString(PAGE_WIDTH - MARGIN_X, y, "REFLECTION")
    c.linkRect(
        "",
        _reflection_destination(year, month),
        (PAGE_WIDTH - MARGIN_X - 190, y - 10, PAGE_WIDTH - MARGIN_X + 8, y + 28),
        relative=0,
        thickness=0,
    )

    _draw_footer(c, year)
    _finish_page(c)


def _draw_week(c: canvas.Canvas, year: int, key: WeekKey, all_weeks: list[WeekKey]) -> None:
    _new_page(c, key.destination)
    start = _week_start(key)
    end = start + timedelta(days=6)
    if start.year == end.year:
        period = f"{start:%d %b} - {end:%d %b %Y}"
    else:
        period = f"{start:%d %b %Y} - {end:%d %b %Y}"
    _draw_header(c, key.label, period)

    top = PAGE_HEIGHT - 210
    bottom = 180
    row_h = (top - bottom) / 7

    for offset in range(7):
        day = start + timedelta(days=offset)
        y1 = top - offset * row_h
        y0 = y1 - row_h
        c.line(MARGIN_X, y0, PAGE_WIDTH - MARGIN_X, y0)
        c.setFont(FONT_BOLD, 22)
        c.drawString(MARGIN_X, y1 - 36, f"{WEEKDAY_NAMES[offset]} {day.day:02d}")

        if day.year == year:
            c.linkRect(
                "",
                _day_destination(day),
                (MARGIN_X - 8, y0, PAGE_WIDTH - MARGIN_X, y1),
                relative=0,
                thickness=0,
            )

    c.setFont(FONT_BOLD, 18)
    c.drawCentredString(PAGE_WIDTH / 2, 146, "WEEKLY LOG / REFLECTION")
    c.linkRect(
        "",
        _weekly_log_destination(key),
        (PAGE_WIDTH / 2 - 135, 130, PAGE_WIDTH / 2 + 135, 170),
        relative=0,
        thickness=0,
    )

    idx = all_weeks.index(key)
    nav_y = 112
    c.setFont(FONT, 18)

    if idx > 0:
        prev_key = all_weeks[idx - 1]
        c.drawString(MARGIN_X, nav_y, f"< {prev_key.label}")
        c.linkRect(
            "",
            prev_key.destination,
            (MARGIN_X - 8, nav_y - 8, MARGIN_X + 90, nav_y + 24),
            relative=0,
            thickness=0,
        )

    if idx + 1 < len(all_weeks):
        next_key = all_weeks[idx + 1]
        c.drawRightString(PAGE_WIDTH - MARGIN_X, nav_y, f"{next_key.label} >")
        c.linkRect(
            "",
            next_key.destination,
            (PAGE_WIDTH - MARGIN_X - 90, nav_y - 8, PAGE_WIDTH - MARGIN_X + 8, nav_y + 24),
            relative=0,
            thickness=0,
        )

    _draw_footer(c, year)
    _finish_page(c)


def _draw_weekly_log(c: canvas.Canvas, year: int, key: WeekKey) -> None:
    _new_page(c, _weekly_log_destination(key))
    start = _week_start(key)
    end = start + timedelta(days=6)
    if start.year == end.year:
        period = f"{start:%d %b} - {end:%d %b %Y}"
    else:
        period = f"{start:%d %b %Y} - {end:%d %b %Y}"
    _draw_header(c, f"{key.label} log / reflection", period)

    nav_y = PAGE_HEIGHT - 160
    c.setFont(FONT, 18)
    c.drawString(MARGIN_X, nav_y, "< WEEK")
    c.linkRect(
        "",
        key.destination,
        (MARGIN_X - 8, nav_y - 8, MARGIN_X + 100, nav_y + 24),
        relative=0,
        thickness=0,
    )

    _draw_dot_grid(c, top=PAGE_HEIGHT - 225)
    _draw_footer(c, year)
    _finish_page(c)


def _draw_day(c: canvas.Canvas, year: int, day: date, days: list[date]) -> None:
    _new_page(c, _day_destination(day))
    iso_year, iso_week, _ = day.isocalendar()
    week_key = WeekKey(iso_year, iso_week)

    title = day.strftime("%A %d")
    _draw_header(c, title, f"{MONTH_NAMES[day.month]} {day.year}")

    nav_y = PAGE_HEIGHT - 160
    c.setFont(FONT, 18)

    month_label = MONTH_NAMES[day.month].upper()
    c.drawString(MARGIN_X, nav_y, month_label)
    c.linkRect(
        "",
        _month_destination(year, day.month),
        (MARGIN_X - 8, nav_y - 8, MARGIN_X + 170, nav_y + 24),
        relative=0,
        thickness=0,
    )

    c.drawCentredString(PAGE_WIDTH / 2, nav_y, week_key.label)
    c.linkRect(
        "",
        week_key.destination,
        (PAGE_WIDTH / 2 - 50, nav_y - 8, PAGE_WIDTH / 2 + 50, nav_y + 24),
        relative=0,
        thickness=0,
    )

    idx = days.index(day)
    if idx > 0:
        c.drawString(MARGIN_X + 250, nav_y, "< PREV")
        c.linkRect(
            "",
            _day_destination(days[idx - 1]),
            (MARGIN_X + 240, nav_y - 8, MARGIN_X + 350, nav_y + 24),
            relative=0,
            thickness=0,
        )

    if idx + 1 < len(days):
        c.drawRightString(PAGE_WIDTH - MARGIN_X, nav_y, "NEXT >")
        c.linkRect(
            "",
            _day_destination(days[idx + 1]),
            (PAGE_WIDTH - MARGIN_X - 120, nav_y - 8, PAGE_WIDTH - MARGIN_X + 8, nav_y + 24),
            relative=0,
            thickness=0,
        )

    _draw_dot_grid(c, top=PAGE_HEIGHT - 225)
    _draw_footer(c, year)
    _finish_page(c)


def _draw_reflection(c: canvas.Canvas, year: int, month: int) -> None:
    _new_page(c, _reflection_destination(year, month))
    _draw_header(c, f"{MONTH_NAMES[month]} reflection", str(year))

    c.setFont(FONT, 18)
    c.drawString(MARGIN_X, PAGE_HEIGHT - 160, "< MONTH")
    c.linkRect(
        "",
        _month_destination(year, month),
        (MARGIN_X - 8, PAGE_HEIGHT - 178, MARGIN_X + 120, PAGE_HEIGHT - 136),
        relative=0,
        thickness=0,
    )

    _draw_dot_grid(c, top=PAGE_HEIGHT - 220)
    _draw_footer(c, year)
    _finish_page(c)


def _draw_index_page(c: canvas.Canvas, year: int, *, title: str, destination: str) -> None:
    _new_page(c, destination)
    _draw_header(c, title, str(year))

    y = PAGE_HEIGHT - 210
    c.setFont(FONT, 20)
    for number in range(1, 21):
        c.drawString(MARGIN_X, y, f"{number:02d}")
        c.line(MARGIN_X + 55, y - 4, PAGE_WIDTH - MARGIN_X, y - 4)
        y -= 70

    _draw_footer(c, year)
    _finish_page(c)


def _draw_annual_reflection(c: canvas.Canvas, year: int) -> None:
    _new_page(c, f"annual-reflection-{year}")
    _draw_header(c, "Annual reflection", str(year))
    _draw_dot_grid(c, top=PAGE_HEIGHT - 200)
    _draw_footer(c, year)
    _finish_page(c)


def generate_bujo(*, year: int, output: Path | str) -> Path:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    days = _all_days(year)
    weeks = _all_weeks(year)

    c = canvas.Canvas(str(output), pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    c.setTitle(f"Bullet Journal {year}")
    c.setAuthor("remarkable-bujo")

    _draw_home(c, year)
    _draw_year(c, year)

    for page in range(1, 7):
        _draw_future_log(c, year, page)

    _draw_index_page(c, year, title="Projects", destination="projects")
    _draw_index_page(c, year, title="Collections", destination="collections")

    for month in range(1, 13):
        _draw_month(c, year, month)
        _draw_monthly_log(c, year, month)

    for key in weeks:
        _draw_week(c, year, key, weeks)
        _draw_weekly_log(c, year, key)

    for day in days:
        _draw_day(c, year, day, days)

    for month in range(1, 13):
        _draw_reflection(c, year, month)

    _draw_annual_reflection(c, year)

    c.save()
    return output
