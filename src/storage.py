"""Persistence layer for settings and reminders using JSON."""
import json
import os
from typing import Dict, Any, List

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
REMINDERS_FILE = os.path.join(DATA_DIR, "reminders.json")

DEFAULT_SETTINGS = {
    "sound_type": "gentle",         # "gentle", "digital", "urgent", "custom"
    "custom_sound_path": "",
    "volume": 85,                   # 0 to 100%
    "default_snooze_minutes": 5,    # 5 or 15
    "gradual_escalation": True,     # Gentle pace/volume ramping to urgent
    "start_on_boot": False,
    "pomodoro_count": 0,            # Completed pomodoro sessions
    "auto_start_breaks": False
}

class Storage:
    @staticmethod
    def _ensure_dir():
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)

    @classmethod
    def load_settings(cls) -> Dict[str, Any]:
        cls._ensure_dir()
        if not os.path.exists(SETTINGS_FILE):
            cls.save_settings(DEFAULT_SETTINGS)
            return dict(DEFAULT_SETTINGS)
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_SETTINGS, **data}
        except Exception:
            return dict(DEFAULT_SETTINGS)

    @classmethod
    def save_settings(cls, settings: Dict[str, Any]):
        cls._ensure_dir()
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)

    @classmethod
    def load_reminders(cls) -> List[dict]:
        cls._ensure_dir()
        if not os.path.exists(REMINDERS_FILE):
            return []
        try:
            with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @classmethod
    def save_reminders(cls, reminders: List[dict]):
        cls._ensure_dir()
        with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(reminders, f, indent=2)
