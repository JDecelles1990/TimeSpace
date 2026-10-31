"""Interactive Dark-Mode Mini Calendar Widget using Python standard library calendar and Tkinter."""
import calendar
import datetime
import tkinter as tk
from typing import Callable, Set, Optional
from src.config import COLORS, FONT_FAMILY

class MiniCalendar(tk.Frame):
    def __init__(self, parent, on_date_selected: Optional[Callable[[datetime.date], None]] = None, **kwargs):
        super().__init__(parent, bg=COLORS["bg_dark"], **kwargs)
        self.on_date_selected = on_date_selected

        today = datetime.date.today()
        self.current_year = today.year
        self.current_month = today.month
        self.selected_date = today
        self.event_dates: Set[datetime.date] = set()

        self._cal = calendar.Calendar(firstweekday=0)  # Monday first
        self._build_ui()
        self.render_calendar()

    def _build_ui(self):
        # Quick Relative Date Chips
        chip_frame = tk.Frame(self, bg=COLORS["bg_dark"])
        chip_frame.pack(fill="x", pady=(0, 6))

        tk.Label(chip_frame, text="Quick Date:", font=(FONT_FAMILY, 8, "bold"),
                 bg=COLORS["bg_dark"], fg=COLORS["text_muted"]).pack(side="left", padx=(0, 4))

        quick_buttons = [
            ("Today", self._select_today),
            ("Tomorrow", self._select_tomorrow),
            ("This Friday", self._select_friday),
            ("Next Monday", self._select_next_monday)
        ]

        for label, cmd in quick_buttons:
            tk.Button(
                chip_frame, text=label, font=(FONT_FAMILY, 8),
                bg=COLORS["surface"], fg=COLORS["text"], activebackground=COLORS["accent"],
                relief="flat", cursor="hand2", padx=6, pady=2, command=cmd
            ).pack(side="left", padx=2)

        # Month Navigation Header
        nav_frame = tk.Frame(self, bg=COLORS["surface"], padx=8, pady=4)
        nav_frame.pack(fill="x", pady=(0, 4))

        tk.Button(
            nav_frame, text="◀", font=(FONT_FAMILY, 9, "bold"),
            bg=COLORS["surface_light"], fg=COLORS["text"], relief="flat",
            cursor="hand2", padx=8, pady=1, command=self._prev_month
        ).pack(side="left")

        self.lbl_month_year = tk.Label(
            nav_frame, text="", font=(FONT_FAMILY, 10, "bold"),
            bg=COLORS["surface"], fg=COLORS["text"]
        )
        self.lbl_month_year.pack(side="left", expand=True)

        tk.Button(
            nav_frame, text="▶", font=(FONT_FAMILY, 9, "bold"),
            bg=COLORS["surface_light"], fg=COLORS["text"], relief="flat",
            cursor="hand2", padx=8, pady=1, command=self._next_month
        ).pack(side="right")

        # Calendar Grid Table
        self.grid_frame = tk.Frame(self, bg=COLORS["bg_dark"])
        self.grid_frame.pack(fill="x")

        # Weekday headers (Mo, Tu, We, Th, Fr, Sa, Su)
        day_names = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        for col_idx, d_name in enumerate(day_names):
            color = COLORS["accent_warning"] if col_idx >= 5 else COLORS["text_muted"]
            lbl = tk.Label(
                self.grid_frame, text=d_name, font=(FONT_FAMILY, 8, "bold"),
                bg=COLORS["bg_dark"], fg=color, width=4, pady=2
            )
            lbl.grid(row=0, column=col_idx, padx=1, pady=1)

    def set_event_dates(self, dates: Set[datetime.date]):
        """Highlight dates on the calendar that contain scheduled rendez-vous."""
        self.event_dates = dates
        self.render_calendar()

    def render_calendar(self):
        # Update header
        month_name = calendar.month_name[self.current_month]
        self.lbl_month_year.config(text=f"{month_name} {self.current_year}")

        # Clear existing day cells (from row 1 onward)
        for widget in self.grid_frame.grid_slaves():
            if int(widget.grid_info()["row"]) > 0:
                widget.destroy()

        today = datetime.date.today()
        month_days = self._cal.monthdatescalendar(self.current_year, self.current_month)

        for row_idx, week in enumerate(month_days, start=1):
            for col_idx, day_date in enumerate(week):
                is_current_month = (day_date.month == self.current_month)
                is_today = (day_date == today)
                is_selected = (day_date == self.selected_date)
                has_event = day_date in self.event_dates

                # Determine styles
                if is_selected:
                    bg_color = COLORS["accent"]
                    fg_color = "#ffffff"
                    font_style = (FONT_FAMILY, 8, "bold")
                elif is_today:
                    bg_color = COLORS["surface_light"]
                    fg_color = COLORS["accent_warning"]
                    font_style = (FONT_FAMILY, 8, "bold")
                elif not is_current_month:
                    bg_color = COLORS["bg_dark"]
                    fg_color = "#52525b"
                    font_style = (FONT_FAMILY, 8)
                else:
                    bg_color = COLORS["surface"]
                    fg_color = COLORS["text"]
                    font_style = (FONT_FAMILY, 8)

                # Day button label (e.g., "15" or "15•")
                day_text = str(day_date.day)
                if has_event and not is_selected:
                    day_text += "•"

                btn = tk.Button(
                    self.grid_frame,
                    text=day_text,
                    font=font_style,
                    bg=bg_color,
                    fg=fg_color,
                    activebackground=COLORS["accent_hover"],
                    relief="flat",
                    cursor="hand2",
                    width=4,
                    height=1,
                    command=lambda d=day_date: self._on_day_clicked(d)
                )
                btn.grid(row=row_idx, column=col_idx, padx=1, pady=1)

    def _on_day_clicked(self, date_val: datetime.date):
        self.selected_date = date_val
        self.current_year = date_val.year
        self.current_month = date_val.month
        self.render_calendar()
        if self.on_date_selected:
            self.on_date_selected(date_val)

    def _prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.render_calendar()

    def _next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.render_calendar()

    def _select_today(self):
        self._on_day_clicked(datetime.date.today())

    def _select_tomorrow(self):
        self._on_day_clicked(datetime.date.today() + datetime.timedelta(days=1))

    def _select_friday(self):
        today = datetime.date.today()
        # weekday(): Monday is 0, Friday is 4
        days_ahead = (4 - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        self._on_day_clicked(today + datetime.timedelta(days=days_ahead))

    def _select_next_monday(self):
        today = datetime.date.today()
        # Monday is 0
        days_ahead = (0 - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        self._on_day_clicked(today + datetime.timedelta(days=days_ahead))

