"""Interactive Dark-Mode Mini Calendar Widget using Python standard library calendar and PySide6."""
import calendar
import datetime
from typing import Callable, Set, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel
from src.config import COLORS


class MiniCalendar(QWidget):
    dateSelected = Signal(object)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        on_date_selected: Optional[Callable[[datetime.date], None]] = None,
    ):
        super().__init__(parent)
        self.on_date_selected = on_date_selected
        if on_date_selected:
            self.dateSelected.connect(on_date_selected)

        today = datetime.date.today()
        self.current_year: int = today.year
        self.current_month: int = today.month
        self.selected_date: datetime.date = today
        self.event_dates: Set[datetime.date] = set()

        self._cal = calendar.Calendar(firstweekday=6)  # Sunday first
        self._build_ui()
        self.render_calendar()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # Quick relative date chips
        chip_row = QHBoxLayout()
        chip_row.setSpacing(4)
        for label, cmd in [
            ("Today", self._select_today),
            ("Tmrw", self._select_tomorrow),
            ("Fri", self._select_friday),
            ("Mon", self._select_next_monday),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(22)
            btn.clicked.connect(cmd)
            chip_row.addWidget(btn)
        main_layout.addLayout(chip_row)

        # Month navigation bar
        nav_row = QHBoxLayout()
        nav_row.setSpacing(4)

        btn_prev = QPushButton("◀")
        btn_prev.setFixedSize(28, 22)
        btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_prev.clicked.connect(self._prev_month)

        self.lbl_month_year = QLabel("")
        self.lbl_month_year.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_month_year.setStyleSheet(f"font-weight: bold; color: {COLORS['text']};")

        btn_next = QPushButton("▶")
        btn_next.setFixedSize(28, 22)
        btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_next.clicked.connect(self._next_month)

        nav_row.addWidget(btn_prev)
        nav_row.addWidget(self.lbl_month_year, 1)
        nav_row.addWidget(btn_next)
        main_layout.addLayout(nav_row)

        # Calendar grid
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(2)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        day_names = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
        for col_idx, d_name in enumerate(day_names):
            color = COLORS["accent_warning"] if col_idx in (0, 6) else COLORS["text_muted"]
            lbl = QLabel(d_name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {color};")
            self.grid_layout.addWidget(lbl, 0, col_idx)

        main_layout.addLayout(self.grid_layout)
        self._day_buttons: list[QPushButton] = []

    def set_event_dates(self, dates: Set[datetime.date]) -> None:
        """Highlight dates on the calendar that contain scheduled rendez-vous."""
        self.event_dates = dates
        self.render_calendar()

    def render_calendar(self) -> None:
        month_name = calendar.month_abbr[self.current_month]
        self.lbl_month_year.setText(f"{month_name} {self.current_year}")

        for btn in self._day_buttons:
            self.grid_layout.removeWidget(btn)
            btn.deleteLater()
        self._day_buttons.clear()

        today = datetime.date.today()
        month_days = self._cal.monthdatescalendar(self.current_year, self.current_month)

        for row_idx, week in enumerate(month_days, start=1):
            for col_idx, day_date in enumerate(week):
                is_current_month = day_date.month == self.current_month
                is_today = day_date == today
                is_selected = day_date == self.selected_date
                has_event = day_date in self.event_dates

                if is_selected:
                    bg_color = COLORS["accent"]
                    fg_color = "#ffffff"
                    weight = "bold"
                elif is_today:
                    bg_color = COLORS["surface_light"]
                    fg_color = COLORS["accent_warning"]
                    weight = "bold"
                elif not is_current_month:
                    bg_color = COLORS["bg_dark"]
                    fg_color = "#52525b"
                    weight = "normal"
                else:
                    bg_color = COLORS["surface"]
                    fg_color = COLORS["text"]
                    weight = "normal"

                day_text = str(day_date.day)
                if has_event and not is_selected:
                    day_text += "•"

                btn = QPushButton(day_text)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setFixedHeight(22)
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {bg_color}; color: {fg_color}; "
                    f"font-weight: {weight}; font-size: 11px; padding: 1px; border-radius: 3px; }}"
                    f"QPushButton:hover {{ background-color: {COLORS['accent_hover']}; color: #ffffff; }}"
                )
                btn.clicked.connect(lambda _checked=False, d=day_date: self._on_day_clicked(d))
                self.grid_layout.addWidget(btn, row_idx, col_idx)
                self._day_buttons.append(btn)

    def _on_day_clicked(self, date_val: datetime.date) -> None:
        self.selected_date = date_val
        self.current_year = date_val.year
        self.current_month = date_val.month
        self.render_calendar()
        self.dateSelected.emit(date_val)

    def _prev_month(self) -> None:
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.render_calendar()

    def _next_month(self) -> None:
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.render_calendar()

    def _select_today(self) -> None:
        self._on_day_clicked(datetime.date.today())

    def _select_tomorrow(self) -> None:
        self._on_day_clicked(datetime.date.today() + datetime.timedelta(days=1))

    def _select_friday(self) -> None:
        today = datetime.date.today()
        days_ahead = (4 - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        self._on_day_clicked(today + datetime.timedelta(days=days_ahead))

    def _select_next_monday(self) -> None:
        today = datetime.date.today()
        days_ahead = (0 - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        self._on_day_clicked(today + datetime.timedelta(days=days_ahead))
