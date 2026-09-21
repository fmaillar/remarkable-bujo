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
    # reMarkable 2: 226 dpi -> 1 cm ~= 89 px. Keep the footer clear of
    # the bottom edge by moving both navigation buttons up by 1 cm.
    y = MARGIN_BOTTOM - 26 + 89

    # Persistent button back to page 1 / navigation hub.
    home_w = 118
    home_h = 34
    home_x = MARGIN_X
    home_y = y - 10
    c.setFont(FONT_BOLD, 15)
    c.roundRect(home_x, home_y, home_w, home_h, 5, stroke=1, fill=0)
    c.drawCentredString(home_x + home_w / 2, home_y + 10, "HOME")
    c.linkRect(
        "",
        "home",
        (home_x, home_y, home_x + home_w, home_y + home_h),
        relative=0,
        thickness=0,
    )

    # Year shortcut stays on the opposite side.
    c.setFont(FONT_BOLD, 15)
    year_w = 96
    year_h = 34
    year_x = PAGE_WIDTH - MARGIN_X - year_w
    year_y = home_y
    c.roundRect(year_x, year_y, year_w, year_h, 5, stroke=1, fill=0)
    c.drawCentredString(year_x + year_w / 2, year_y + 10, right)
    c.linkRect(
        "",
        f"year-{year}",
        (year_x, year_y, year_x + year_w, year_y + year_h),
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


def _draw_key(c: canvas.Canvas, year: int) -> None:
    _new_page(c, "key")
    _draw_header(c, "Key", str(year))

    entries = [
        ("task", "Task"),
        ("done", "Completed task"),
        ("cancelled", "Cancelled task"),
        (">", "Migrated task"),
        ("<", "Scheduled task"),
        ("-", "Note"),
        ("event", "Event"),
        ("^", "Appointment"),
        ("/", "Delegated task"),
        ("\\", "Task in progress"),
        ("=", "Emotion / feeling / impression"),
        ("~", "Intention"),
        ("?", "Question / inquiry"),
        ("??", "Confusion"),
        ("!?", "Surprise / astonishment"),
        ("*", "Priority / important"),
        ("!", "Inspiration / insight"),
    ]

    y = PAGE_HEIGHT - 220
    symbol_x = MARGIN_X + 18
    label_x = MARGIN_X + 90
    row_h = 70

    for symbol, label in entries:
        c.saveState()

        if symbol == "task":
            c.setFillGray(0)
            c.circle(symbol_x + 8, y + 6, 5, stroke=0, fill=1)

        elif symbol == "done":
            c.setFont(FONT_BOLD, 26)
            c.drawString(symbol_x, y - 2, "x")

        elif symbol == "cancelled":
            # A task marker crossed out to represent cancellation.
            c.setFillGray(0)
            c.circle(symbol_x + 8, y + 6, 5, stroke=0, fill=1)
            c.setLineWidth(2)
            c.line(symbol_x - 3, y + 6, symbol_x + 23, y + 6)

        elif symbol == "event":
            # Draw the event marker explicitly so it stays a true empty circle
            # regardless of PDF font Unicode coverage.
            c.setLineWidth(2)
            c.circle(symbol_x + 8, y + 6, 7, stroke=1, fill=0)

        else:
            c.setFont(FONT_BOLD, 26)
            c.drawString(symbol_x, y - 2, symbol)

        c.restoreState()

        c.setFont(FONT, 23)
        c.drawString(label_x, y, label)
        y -= row_h

    c.setFont(FONT, 17)
    c.drawString(MARGIN_X, y - 2, "Use only the symbols that remain useful in practice.")
    _draw_footer(c, year)
    _finish_page(c)


def _draw_global_index(c: canvas.Canvas, year: int) -> None:
    _new_page(c, "index")
    _draw_header(c, "Index", str(year))
    items = [
        ("Future Log", _future_log_destination(year, 1)),
        ("Year", f"year-{year}"),
        ("Goals / Intentions", "goals"),
        ("Someday / Maybe", "someday"),
        ("Projects", "projects"),
        ("Collections", "collections"),
        ("Annual Reflection", f"annual-reflection-{year}"),
    ]
    y = PAGE_HEIGHT - 210
    c.setFont(FONT, 22)
    for label, destination in items:
        c.drawString(MARGIN_X, y, label)
        c.drawRightString(PAGE_WIDTH - MARGIN_X, y, ">")
        c.linkRect("", destination, (MARGIN_X - 8, y - 12, PAGE_WIDTH - MARGIN_X + 8, y + 30), relative=0, thickness=0)
        c.line(MARGIN_X, y - 20, PAGE_WIDTH - MARGIN_X, y - 20)
        y -= 72

    c.setFont(FONT_BOLD, 20)
    c.drawString(MARGIN_X, y - 10, "Collections / Projects")
    y -= 65
    c.setFont(FONT, 18)
    for number in range(1, 11):
        c.drawString(MARGIN_X, y, f"C{number:02d}")
        c.linkRect("", f"collection-{number:02d}", (MARGIN_X - 8, y - 10, MARGIN_X + 75, y + 24), relative=0, thickness=0)
        c.drawString(MARGIN_X + 250, y, f"P{number:02d}")
        c.linkRect("", f"project-{number:02d}", (MARGIN_X + 240, y - 10, MARGIN_X + 325, y + 24), relative=0, thickness=0)
        c.line(MARGIN_X + 80, y - 4, MARGIN_X + 220, y - 4)
        c.line(MARGIN_X + 330, y - 4, PAGE_WIDTH - MARGIN_X, y - 4)
        y -= 58
    _draw_footer(c, year)
    _finish_page(c)


def _draw_free_page(c: canvas.Canvas, year: int, *, title: str, destination: str, subtitle: str | None = None) -> None:
    _new_page(c, destination)
    _draw_header(c, title, subtitle or str(year))
    _draw_dot_grid(c, top=PAGE_HEIGHT - 190)
    _draw_footer(c, year)
    _finish_page(c)


def _draw_collection_or_project_page(c: canvas.Canvas, year: int, *, kind: str, number: int) -> None:
    destination = f"{kind}-{number:02d}"
    title = f"{kind.capitalize()} {number:02d}"
    _new_page(c, destination)
    _draw_header(c, title, str(year))
    c.setFont(FONT, 16)
    index_dest = "collections" if kind == "collection" else "projects"
    c.drawString(MARGIN_X, PAGE_HEIGHT - 160, "< INDEX")
    c.linkRect("", index_dest, (MARGIN_X - 8, PAGE_HEIGHT - 178, MARGIN_X + 100, PAGE_HEIGHT - 136), relative=0, thickness=0)
    _draw_dot_grid(c, top=PAGE_HEIGHT - 220)
    _draw_footer(c, year)
    _finish_page(c)


def _draw_home(c: canvas.Canvas, year: int) -> None:
    """Draw the first-page navigation hub.

    Daily logs are intentionally omitted: the page exposes the complete BuJo
    structure without turning into a 365-entry date index.
    """
    _new_page(c, "home")
    c.setFont(FONT_BOLD, 56)
    c.drawString(MARGIN_X, PAGE_HEIGHT - 105, f"Bullet Journal {year}")
    c.setFont(FONT, 19)
    c.drawRightString(PAGE_WIDTH - MARGIN_X, PAGE_HEIGHT - 100, "NAVIGATION HUB")

    # Global collections / planning layers.
    shortcuts = [
        ("KEY", "key"),
        ("YEAR", f"year-{year}"),
        ("FUTURE", _future_log_destination(year, 1)),
        ("GOALS", "goals"),
        ("SOMEDAY", "someday"),
        ("PROJECTS", "projects"),
        ("COLLECTIONS", "collections"),
        ("ANNUAL REF.", f"annual-reflection-{year}"),
    ]
    shortcut_y = PAGE_HEIGHT - 170
    x = MARGIN_X
    c.setFont(FONT_BOLD, 18)
    for label, destination in shortcuts:
        width = max(86.0, c.stringWidth(label, FONT_BOLD, 18) + 28)
        if x + width > PAGE_WIDTH - MARGIN_X:
            x = MARGIN_X
            shortcut_y -= 46
        c.roundRect(x, shortcut_y - 10, width, 32, 5, stroke=1, fill=0)
        c.drawCentredString(x + width / 2, shortcut_y, label)
        c.linkRect(
            "",
            destination,
            (x, shortcut_y - 10, x + width, shortcut_y + 22),
            relative=0,
            thickness=0,
        )
        x += width + 12

    # One row per month.  Each row exposes the month calendar, monthly log,
    # monthly reflection, weekly overview, and weekly log/reflection pages.
    weeks = _all_weeks(year)
    row_top = shortcut_y - 78
    row_h = 116
    month_x = MARGIN_X
    nav_x = 260
    weeks_x = 575

    c.setFont(FONT, 15)
    c.drawString(nav_x, row_top + 22, "MONTH")
    c.drawString(weeks_x, row_top + 22, "WEEK  /  LOG-REF")
    c.line(MARGIN_X, row_top + 12, PAGE_WIDTH - MARGIN_X, row_top + 12)

    for month in range(1, 13):
        y = row_top - (month - 1) * row_h

        c.setFont(FONT_BOLD, 24)
        c.drawString(month_x, y - 28, MONTH_NAMES[month].upper())

        links = [
            ("CAL", _month_destination(year, month)),
            ("LOG", _monthly_log_destination(year, month)),
            ("REF", _reflection_destination(year, month)),
        ]
        x = nav_x
        c.setFont(FONT_BOLD, 16)
        for label, destination in links:
            w = 70
            c.drawCentredString(x + w / 2, y - 27, label)
            c.linkRect(
                "",
                destination,
                (x, y - 43, x + w, y - 10),
                relative=0,
                thickness=0,
            )
            x += w + 12

        # A week is listed under every month it intersects.  This makes
        # cross-month ISO weeks discoverable from either side of the boundary.
        month_weeks = []
        for key in weeks:
            week_start = _week_start(key)
            week_days = [week_start + timedelta(days=i) for i in range(7)]
            if any(d.year == year and d.month == month for d in week_days):
                month_weeks.append(key)

        x = weeks_x
        c.setFont(FONT_BOLD, 17)
        for key in month_weeks:
            week_label = key.label
            week_w = 48
            c.drawString(x, y - 25, week_label)
            c.linkRect(
                "",
                key.destination,
                (x - 4, y - 40, x + week_w, y - 8),
                relative=0,
                thickness=0,
            )

            log_x = x + week_w + 2
            c.setFont(FONT_BOLD, 16)
            c.drawString(log_x, y - 25, "R")
            c.linkRect(
                "",
                _weekly_log_destination(key),
                (log_x - 4, y - 40, log_x + 20, y - 8),
                relative=0,
                thickness=0,
            )
            c.setFont(FONT_BOLD, 17)
            x += 84

        c.setFont(FONT, 12)
        c.drawString(weeks_x, y - 57, "W = weekly overview    R = weekly log / reflection")
        c.setStrokeGray(0.75)
        c.line(MARGIN_X, y - 72, PAGE_WIDTH - MARGIN_X, y - 72)
        c.setStrokeGray(0)

    c.setFont(FONT, 14)
    c.drawString(
        MARGIN_X,
        MARGIN_BOTTOM - 5,
        "Daily Logs are reached from month calendars, monthly logs, or weekly pages.",
    )
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

    _draw_footer(c, year)
    _finish_page(c)


def _draw_monthly_log(c: canvas.Canvas, year: int, month: int) -> None:
    _new_page(c, _monthly_log_destination(year, month))
    _draw_header(c, f"{MONTH_NAMES[month]} log", str(year))

    nav_y = PAGE_HEIGHT - 160
    c.setFont(FONT, 18)
    c.drawString(MARGIN_X, nav_y, "< CALENDAR")
    c.linkRect("", _month_destination(year, month), (MARGIN_X - 8, nav_y - 8, MARGIN_X + 150, nav_y + 24), relative=0, thickness=0)
    c.drawRightString(PAGE_WIDTH - MARGIN_X, nav_y, "REFLECTION >")
    c.linkRect("", _reflection_destination(year, month), (PAGE_WIDTH - MARGIN_X - 150, nav_y - 8, PAGE_WIDTH - MARGIN_X + 8, nav_y + 24), relative=0, thickness=0)

    split_x = PAGE_WIDTH * 0.46
    top = PAGE_HEIGHT - 225
    bottom = 185
    c.line(split_x, bottom, split_x, top)

    c.setFont(FONT_BOLD, 22)
    c.drawString(MARGIN_X, top, "CALENDAR")
    c.drawString(split_x + 34, top, "TASKS")

    _, days_in_month = calendar.monthrange(year, month)
    y = top - 48
    row = (top - bottom - 60) / 31
    c.setFont(FONT, 17)
    for day_num in range(1, days_in_month + 1):
        d = date(year, month, day_num)
        c.drawString(MARGIN_X, y, f"{day_num:02d} {WEEKDAY_NAMES[d.weekday()]}")
        c.line(MARGIN_X + 95, y - 4, split_x - 20, y - 4)
        c.linkRect("", _day_destination(d), (MARGIN_X - 6, y - 10, split_x - 10, y + 20), relative=0, thickness=0)
        y -= row

    _draw_dot_grid(c, top=top - 42, bottom=bottom, left=split_x + 34)
    c.setFont(FONT_BOLD, 18)
    c.drawString(split_x + 34, 185, "MIGRATE  >   SCHEDULE  <   DROP  /")
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
    c.linkRect("", key.destination, (MARGIN_X - 8, nav_y - 8, MARGIN_X + 100, nav_y + 24), relative=0, thickness=0)

    top = PAGE_HEIGHT - 225
    mid = 720
    c.setFont(FONT_BOLD, 22)
    c.drawString(MARGIN_X, top, "LOG / NOTES")
    _draw_dot_grid(c, top=top - 44, bottom=mid + 35)

    c.line(MARGIN_X, mid, PAGE_WIDTH - MARGIN_X, mid)
    c.setFont(FONT_BOLD, 22)
    c.drawString(MARGIN_X, mid - 48, "REFLECTION / MIGRATION")
    c.setFont(FONT, 18)
    c.drawString(MARGIN_X, mid - 92, "What mattered?  What changes?  What moves forward?")
    _draw_dot_grid(c, top=mid - 132, bottom=190)
    c.setFont(FONT_BOLD, 18)
    c.drawString(MARGIN_X, 188, "MIGRATE  >   SCHEDULE  <   DROP  /")
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

    _draw_dot_grid(c, top=PAGE_HEIGHT - 225)
    _draw_footer(c, year)
    _finish_page(c)


def _draw_reflection(c: canvas.Canvas, year: int, month: int) -> None:
    _new_page(c, _reflection_destination(year, month))
    _draw_header(c, f"{MONTH_NAMES[month]} reflection", str(year))

    c.setFont(FONT, 18)
    c.drawString(MARGIN_X, PAGE_HEIGHT - 160, "< MONTHLY LOG")
    c.linkRect("", _monthly_log_destination(year, month), (MARGIN_X - 8, PAGE_HEIGHT - 178, MARGIN_X + 170, PAGE_HEIGHT - 136), relative=0, thickness=0)

    sections = [
        ("WHAT HAPPENED", 1450, 1120),
        ("WHAT MATTERED / LEARNED", 1060, 730),
        ("MIGRATE / SCHEDULE / DROP", 670, 340),
    ]
    for title, top, bottom in sections:
        c.setFont(FONT_BOLD, 20)
        c.drawString(MARGIN_X, top, title)
        _draw_dot_grid(c, top=top - 42, bottom=bottom)
    _draw_footer(c, year)
    _finish_page(c)


def _draw_index_page(
    c: canvas.Canvas,
    year: int,
    *,
    title: str,
    destination: str,
    page: int = 1,
) -> None:
    page_destination = destination if page == 1 else f"{destination}-{page}"
    _new_page(c, page_destination)

    first = 1 if page == 1 else 21
    last = 20 if page == 1 else 40
    _draw_header(c, title, f"{year} · {first:02d}-{last:02d}")

    kind = "project" if destination == "projects" else "collection"
    y = PAGE_HEIGHT - 210
    c.setFont(FONT, 20)
    for number in range(first, last + 1):
        c.drawString(MARGIN_X, y, f"{number:02d}")
        c.line(MARGIN_X + 55, y - 4, PAGE_WIDTH - MARGIN_X, y - 4)
        c.linkRect(
            "",
            f"{kind}-{number:02d}",
            (MARGIN_X - 8, y - 12, PAGE_WIDTH - MARGIN_X + 8, y + 26),
            relative=0,
            thickness=0,
        )
        y -= 70

    # Direct switch between the two index pages, without PREV/NEXT controls.
    c.setFont(FONT_BOLD, 16)
    if page == 1:
        label = "21-40"
        target = f"{destination}-2"
    else:
        label = "01-20"
        target = destination

    switch_w = 110
    switch_h = 34
    switch_x = PAGE_WIDTH / 2 - switch_w / 2
    switch_y = 105
    c.roundRect(switch_x, switch_y, switch_w, switch_h, 5, stroke=1, fill=0)
    c.drawCentredString(switch_x + switch_w / 2, switch_y + 10, label)
    c.linkRect(
        "",
        target,
        (switch_x, switch_y, switch_x + switch_w, switch_y + switch_h),
        relative=0,
        thickness=0,
    )

    _draw_footer(c, year)
    _finish_page(c)


def _draw_annual_reflection(c: canvas.Canvas, year: int) -> None:
    _new_page(c, f"annual-reflection-{year}")
    _draw_header(c, "Annual reflection", str(year))
    sections = [
        ("WHAT HAPPENED", 1510, 1210),
        ("WHAT MATTERED / LEARNED", 1150, 850),
        ("WHAT TO CARRY FORWARD", 790, 490),
        ("WHAT TO LET GO", 430, 180),
    ]
    for title, top, bottom in sections:
        c.setFont(FONT_BOLD, 20)
        c.drawString(MARGIN_X, top, title)
        _draw_dot_grid(c, top=top - 42, bottom=bottom)
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
    _draw_key(c, year)
    _draw_free_page(c, year, title="Goals / Intentions", destination="goals")
    _draw_free_page(c, year, title="Someday / Maybe", destination="someday")
    _draw_year(c, year)

    for page in range(1, 7):
        _draw_future_log(c, year, page)

    _draw_index_page(c, year, title="Projects", destination="projects", page=1)
    _draw_index_page(c, year, title="Projects", destination="projects", page=2)
    for number in range(1, 41):
        _draw_collection_or_project_page(c, year, kind="project", number=number)

    _draw_index_page(c, year, title="Collections", destination="collections", page=1)
    _draw_index_page(c, year, title="Collections", destination="collections", page=2)
    for number in range(1, 41):
        _draw_collection_or_project_page(c, year, kind="collection", number=number)

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
