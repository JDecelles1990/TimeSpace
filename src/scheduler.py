"""Thread-safe Timer & Rendez-vous scheduler with pause/resume, categories, and repeating rules."""
import time
import uuid
import datetime
import threading
from typing import List, Callable, Dict, Any, Optional
from src.storage import Storage

class ScheduledItem:
    def __init__(
        self,
        item_id: str,
        kind: str,
        name: str,
        target_time: float,
        repeat_sec: int = 0,
        original_duration: float = 0.0,
        repeat_rule: str = "none",
        is_paused: bool = False,
        remaining_paused: float = 0.0,
        category: str = "General",
        lead_time_min: int = 0
    ):
        self.id = item_id
        self.kind = kind  # 'timer' or 'rendez-vous'
        self.name = name
        self.target_time = target_time
        self.repeat_sec = repeat_sec
        self.original_duration = original_duration or (target_time - time.time())
        self.repeat_rule = repeat_rule  # "none", "daily", "weekly", "monthly"
        self.is_paused = is_paused
        self.remaining_paused = remaining_paused
        self.category = category
        self.lead_time_min = lead_time_min

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "name": self.name,
            "target_time": self.target_time,
            "repeat_sec": self.repeat_sec,
            "original_duration": self.original_duration,
            "repeat_rule": self.repeat_rule,
            "is_paused": self.is_paused,
            "remaining_paused": self.remaining_paused,
            "category": self.category,
            "lead_time_min": self.lead_time_min
        }

    @staticmethod
    def from_dict(d: dict):
        return ScheduledItem(
            item_id=d["id"],
            kind=d["kind"],
            name=d["name"],
            target_time=d["target_time"],
            repeat_sec=d.get("repeat_sec", 0),
            original_duration=d.get("original_duration", 0.0),
            repeat_rule=d.get("repeat_rule", "none"),
            is_paused=d.get("is_paused", False),
            remaining_paused=d.get("remaining_paused", 0.0),
            category=d.get("category", "General"),
            lead_time_min=d.get("lead_time_min", 0)
        )

class ReminderScheduler:
    def __init__(
        self,
        on_trigger_callback: Callable[[ScheduledItem], None],
        on_wake_missed_callback: Optional[Callable[[List[ScheduledItem]], None]] = None
    ):
        self.items: List[ScheduledItem] = []
        self.missed_items: List[ScheduledItem] = []
        self.callback = on_trigger_callback
        self.on_wake_missed_callback = on_wake_missed_callback
        self._running = True
        self._lock = threading.Lock()

        # Load persisted reminders and detect any missed alarms while closed
        now = time.time()
        for item_data in Storage.load_reminders():
            it = ScheduledItem.from_dict(item_data)
            if not it.is_paused and it.target_time < now - 10:
                self.missed_items.append(it)
            else:
                self.items.append(it)

        self._worker = threading.Thread(target=self._run_loop, daemon=True)
        self._worker.start()

    def _persist(self):
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
        lead_time_min: int = 0
    ) -> str:
        item_id = str(uuid.uuid4())
        # If an early reminder lead-time is specified, advance alarm
        effective_seconds = max(0.0, seconds_from_now - (lead_time_min * 60))
        target = time.time() + effective_seconds
        dur = original_duration if original_duration > 0 else seconds_from_now

        annotated_name = name or "Untitled Reminder"
        if lead_time_min > 0:
            annotated_name = f"[{lead_time_min}m Early] {annotated_name}"

        item = ScheduledItem(
            item_id=item_id,
            kind=kind,
            name=annotated_name,
            target_time=target,
            repeat_sec=repeat_sec,
            original_duration=dur,
            repeat_rule=repeat_rule,
            category=category,
            lead_time_min=lead_time_min
        )
        with self._lock:
            self.items.append(item)
            self._persist()
        return item_id

    def remove_item(self, item_id: str):
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
        matching = []
        with self._lock:
            for it in self.items:
                if it.kind == "rendez-vous":
                    item_date = datetime.datetime.fromtimestamp(it.target_time).date()
                    if item_date == target_date:
                        matching.append(it)
        return matching

    def get_all_event_dates(self) -> set:
        """Return a set of datetime.date objects that currently have scheduled rendez-vous."""
        dates = set()
        with self._lock:
            for it in self.items:
                if it.kind == "rendez-vous":
                    d = datetime.datetime.fromtimestamp(it.target_time).date()
                    dates.add(d)
        return dates

    def _advance_repeat(self, it: ScheduledItem, now: float):
        if it.repeat_sec > 0:
            it.target_time = now + it.repeat_sec
            return True
        rule = it.repeat_rule.lower()
        if rule == "daily":
            it.target_time += 86400
            return True
        elif rule == "weekly":
            it.target_time += 86400 * 7
            return True
        elif rule == "monthly":
            it.target_time += 86400 * 30
            return True
        return False

    def _run_loop(self):
        last_tick = time.time()
        while self._running:
            time.sleep(0.5)
            now = time.time()

            gap = now - last_tick
            if gap > 6.0:
                missed_during_sleep = []
                with self._lock:
                    for it in self.items:
                        if not it.is_paused and it.target_time < now:
                            missed_during_sleep.append(it)
                if missed_during_sleep and self.on_wake_missed_callback:
                    self.on_wake_missed_callback(missed_during_sleep)

            last_tick = now
            triggered = []

            with self._lock:
                remaining = []
                for it in self.items:
                    if it.is_paused:
                        remaining.append(it)
                        continue

                    if now >= it.target_time:
                        triggered.append(it)
                        if self._advance_repeat(it, now):
                            remaining.append(it)
                    else:
                        remaining.append(it)
                self.items = remaining
                if triggered:
                    self._persist()

            for item in triggered:
                self.callback(item)
