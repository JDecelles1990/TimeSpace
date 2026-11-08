"""Thread-safe Timer & Rendez-vous scheduler with pause/resume, inline editing, categories, attachments, and repeating rules."""
import time
import uuid
import calendar
import datetime
import threading
from dataclasses import dataclass, asdict, replace
from typing import List, Callable, Dict, Any, Optional, Set
from src.storage import Storage


@dataclass
class ScheduledItem:
    id: str
    kind: str  # 'timer' or 'rendez-vous'
    name: str
    target_time: float
    repeat_sec: int = 0
    original_duration: float = 0.0
    repeat_rule: str = "none"  # "none", "daily", "weekly", "monthly"
    is_paused: bool = False
    remaining_paused: float = 0.0
    category: str = "General"
    lead_time_min: int = 0
    url: str = ""
    note: str = ""
    anchor_day: int = 0

    def __post_init__(self) -> None:
        if not self.original_duration or self.original_duration <= 0:
            self.original_duration = max(1.0, self.target_time - time.time())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ScheduledItem":
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            kind=d.get("kind", "timer"),
            name=d.get("name", "Reminder"),
            target_time=float(d.get("target_time", time.time())),
            repeat_sec=int(d.get("repeat_sec", 0)),
            original_duration=float(d.get("original_duration", 0.0)),
            repeat_rule=d.get("repeat_rule", "none"),
            is_paused=bool(d.get("is_paused", False)),
            remaining_paused=float(d.get("remaining_paused", 0.0)),
            category=d.get("category", "General"),
            lead_time_min=int(d.get("lead_time_min", 0)),
            url=str(d.get("url", "") or ""),
            note=str(d.get("note", "") or ""),
            anchor_day=int(d.get("anchor_day", 0) or 0),
        )


class ReminderScheduler:
    def __init__(
        self,
        on_trigger_callback: Callable[[ScheduledItem], None],
        on_wake_missed_callback: Optional[Callable[[List[ScheduledItem]], None]] = None,
    ):
        self.items: List[ScheduledItem] = []
        self.missed_items: List[ScheduledItem] = []
        self.callback = on_trigger_callback
        self.on_wake_missed_callback = on_wake_missed_callback
        self._running: bool = True
        self._lock = threading.Lock()

        now = time.time()
        dirty = False
        for item_data in Storage.load_reminders():
            it = ScheduledItem.from_dict(item_data)
            if not it.is_paused and it.target_time < now - 10:
                self.missed_items.append(replace(it))
                if self._advance_repeat(it, now):
                    self.items.append(it)
                dirty = True
            else:
                self.items.append(it)

        if dirty:
            self._persist()

        self._worker = threading.Thread(target=self._run_loop, daemon=True)
        self._worker.start()

    def _persist(self) -> None:
        Storage.save_reminders([it.to_dict() for it in self.items])

    def add_item(
        self,
        kind: str,
        name: str,
        seconds_from_now: float,
        repeat_sec: int = 0,
        original_duration: float = 0.0,
        repeat_rule: str = "none",
        category: str = "General",
        lead_time_min: int = 0,
        url: str = "",
        note: str = "",
        anchor_day: int = 0,
    ) -> str:
        item_id = str(uuid.uuid4())
        now_ts = time.time()
        intended_event_ts = now_ts + seconds_from_now
        effective_seconds = max(0.0, seconds_from_now - (lead_time_min * 60))
        target = now_ts + effective_seconds
        dur = original_duration if original_duration > 0 else max(1.0, effective_seconds)

        annotated_name = name or "Untitled Reminder"
        if lead_time_min > 0 and not annotated_name.startswith(f"[{lead_time_min}m Early]"):
            annotated_name = f"[{lead_time_min}m Early] {annotated_name}"

        computed_anchor = anchor_day
        if computed_anchor <= 0 and repeat_rule.lower() == "monthly":
            computed_anchor = datetime.datetime.fromtimestamp(intended_event_ts).day

        item = ScheduledItem(
            id=item_id,
            kind=kind,
            name=annotated_name,
            target_time=target,
            repeat_sec=repeat_sec,
            original_duration=dur,
            repeat_rule=repeat_rule,
            category=category,
            lead_time_min=lead_time_min,
            url=url.strip(),
            note=note.strip(),
            anchor_day=computed_anchor,
        )
        with self._lock:
            self.items.append(item)
            self._persist()
        return item_id

    def get_item(self, item_id: str) -> Optional[ScheduledItem]:
        """Lookup an active ScheduledItem by ID."""
        with self._lock:
            for it in self.items:
                if it.id == item_id:
                    return it
        return None

    def update_item(
        self,
        item_id: str,
        name: Optional[str] = None,
        seconds_from_now: Optional[float] = None,
        repeat_sec: Optional[int] = None,
        repeat_rule: Optional[str] = None,
        category: Optional[str] = None,
        lead_time_min: Optional[int] = None,
        url: Optional[str] = None,
        note: Optional[str] = None,
        anchor_day: Optional[int] = None,
    ) -> Optional[ScheduledItem]:
        """Update an active timer or rendez-vous in-place and persist changes."""
        now_ts = time.time()
        with self._lock:
            for it in self.items:
                if it.id == item_id:
                    if lead_time_min is not None:
                        it.lead_time_min = max(0, int(lead_time_min))
                    if name is not None:
                        import re
                        base_name = re.sub(r"^\[\d+m Early\]\s*", "", name.strip()) or "Untitled Reminder"
                        if it.lead_time_min > 0:
                            it.name = f"[{it.lead_time_min}m Early] {base_name}"
                        else:
                            it.name = base_name
                    if seconds_from_now is not None and seconds_from_now > 0:
                        eff = max(1.0, float(seconds_from_now) - (it.lead_time_min * 60))
                        if it.is_paused:
                            it.remaining_paused = eff
                        else:
                            it.target_time = now_ts + eff
                        it.original_duration = max(1.0, eff)
                    if repeat_sec is not None:
                        it.repeat_sec = max(0, int(repeat_sec))
                    if repeat_rule is not None:
                        it.repeat_rule = repeat_rule.lower()
                    if category is not None:
                        it.category = category
                    if url is not None:
                        it.url = url.strip()
                    if note is not None:
                        it.note = note.strip()
                    if anchor_day is not None:
                        it.anchor_day = int(anchor_day)
                    self._persist()
                    return it
        return None

    def remove_item(self, item_id: str) -> None:
        with self._lock:
            self.items = [it for it in self.items if it.id != item_id]
            self._persist()

    def toggle_pause(self, item_id: str) -> bool:
        """Pause a running timer or resume a paused one."""
        now = time.time()
        with self._lock:
            for it in self.items:
                if it.id == item_id:
                    if it.is_paused:
                        it.target_time = now + it.remaining_paused
                        it.is_paused = False
                        it.remaining_paused = 0.0
                        self._persist()
                        return False
                    else:
                        it.remaining_paused = max(0.0, it.target_time - now)
                        it.is_paused = True
                        self._persist()
                        return True
        return False

    def get_nearest_item(self) -> Optional[ScheduledItem]:
        with self._lock:
            active = [it for it in self.items if not it.is_paused]
            if not active:
                return None
            return min(active, key=lambda x: x.target_time)

    def get_active_timer(self) -> Optional[ScheduledItem]:
        with self._lock:
            for it in self.items:
                if it.kind == "timer":
                    return it
        return None

    def get_events_for_date(self, target_date: datetime.date) -> List[ScheduledItem]:
        """Return all scheduled rendez-vous falling on a specific calendar date."""
        matching: List[ScheduledItem] = []
        with self._lock:
            for it in self.items:
                if it.kind == "rendez-vous":
                    event_ts = it.target_time + max(0, it.lead_time_min) * 60
                    item_date = datetime.datetime.fromtimestamp(event_ts).date()
                    if item_date == target_date:
                        matching.append(it)
        return matching

    def get_all_event_dates(self) -> Set[datetime.date]:
        """Return a set of datetime.date objects that currently have scheduled rendez-vous."""
        dates: Set[datetime.date] = set()
        with self._lock:
            for it in self.items:
                if it.kind == "rendez-vous":
                    event_ts = it.target_time + max(0, it.lead_time_min) * 60
                    d = datetime.datetime.fromtimestamp(event_ts).date()
                    dates.add(d)
        return dates

    def _advance_repeat(self, it: ScheduledItem, now: float) -> bool:
        """Advance a repeating timer or calendar RDV past `now`, preserving anchored monthly days and DST wall-clock."""
        if it.repeat_sec > 0:
            it.target_time = now + it.repeat_sec
            it.original_duration = float(it.repeat_sec)
            return True

        rule = (it.repeat_rule or "none").lower()
        if rule not in ("daily", "weekly", "monthly"):
            return False

        lead_delta = datetime.timedelta(minutes=max(0, it.lead_time_min))
        event_dt = datetime.datetime.fromtimestamp(it.target_time) + lead_delta

        if rule == "monthly" and it.anchor_day <= 0:
            it.anchor_day = event_dt.day

        while True:
            if rule == "daily":
                next_date = event_dt.date() + datetime.timedelta(days=1)
                event_dt = datetime.datetime.combine(next_date, event_dt.time())
            elif rule == "weekly":
                next_date = event_dt.date() + datetime.timedelta(days=7)
                event_dt = datetime.datetime.combine(next_date, event_dt.time())
            elif rule == "monthly":
                year = event_dt.year + (event_dt.month // 12)
                month = (event_dt.month % 12) + 1
                max_day = calendar.monthrange(year, month)[1]
                day = min(it.anchor_day, max_day)
                event_dt = event_dt.replace(year=year, month=month, day=day)

            next_trigger_ts = (event_dt - lead_delta).timestamp()
            if next_trigger_ts > now:
                it.target_time = next_trigger_ts
                it.original_duration = max(1.0, next_trigger_ts - now)
                return True

    def _run_loop(self) -> None:
        last_tick = time.time()
        while self._running:
            time.sleep(0.5)
            now = time.time()

            gap = now - last_tick
            if gap > 6.0:
                missed_during_sleep: List[ScheduledItem] = []
                with self._lock:
                    for it in self.items:
                        if not it.is_paused and it.target_time < now:
                            missed_during_sleep.append(replace(it))
                if missed_during_sleep and self.on_wake_missed_callback:
                    self.on_wake_missed_callback(missed_during_sleep)

            last_tick = now
            triggered: List[ScheduledItem] = []

            with self._lock:
                remaining: List[ScheduledItem] = []
                for it in self.items:
                    if it.is_paused:
                        remaining.append(it)
                        continue

                    if now >= it.target_time:
                        triggered.append(replace(it))
                        if self._advance_repeat(it, now):
                            remaining.append(it)
                    else:
                        remaining.append(it)
                self.items = remaining
                if triggered:
                    self._persist()

            for item in triggered:
                self.callback(item)
