"""Persistence layer for AppConfig, reminders, history, and scratchpad using JSON."""
import json
import os
from typing import Dict, Any, List, Union
from src.config import AppConfig, HistoryEntry, ScratchpadState

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
REMINDERS_FILE = os.path.join(DATA_DIR, "reminders.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
SCRATCHPAD_FILE = os.path.join(DATA_DIR, "scratchpad.json")


class Storage:
    @staticmethod
    def _ensure_dir() -> None:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)

    # ── AppConfig (Settings) ─────────────────────────────────────────────────

    @classmethod
    def load_config(cls) -> AppConfig:
        """Load strongly-typed AppConfig from disk, migrating defaults automatically."""
        cls._ensure_dir()
        if not os.path.exists(SETTINGS_FILE):
            default_cfg = AppConfig()
            cls.save_config(default_cfg)
            return default_cfg
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return AppConfig.from_dict(data)
        except Exception:
            return AppConfig()

    @classmethod
    def save_config(cls, config: Union[AppConfig, Dict[str, Any]]) -> None:
        """Persist AppConfig (or dict) to disk."""
        cls._ensure_dir()
        payload = config.to_dict() if isinstance(config, AppConfig) else config
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            pass

    @classmethod
    def load_settings(cls) -> Dict[str, Any]:
        """Legacy dictionary compatibility wrapper around load_config()."""
        return cls.load_config().to_dict()

    @classmethod
    def save_settings(cls, settings: Union[AppConfig, Dict[str, Any]]) -> None:
        """Legacy dictionary compatibility wrapper around save_config()."""
        cls.save_config(settings)

    # ── Scheduled Reminders ──────────────────────────────────────────────────

    @classmethod
    def load_reminders(cls) -> List[Dict[str, Any]]:
        cls._ensure_dir()
        if not os.path.exists(REMINDERS_FILE):
            return []
        try:
            with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @classmethod
    def save_reminders(cls, reminders: List[Dict[str, Any]]) -> None:
        cls._ensure_dir()
        try:
            with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
                json.dump(reminders, f, indent=2)
        except Exception:
            pass

    # ── Completed / Triggered History ────────────────────────────────────────

    @classmethod
    def load_history(cls) -> List[Dict[str, Any]]:
        """Load list of completed/dismissed events."""
        cls._ensure_dir()
        if not os.path.exists(HISTORY_FILE):
            return []
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @classmethod
    def add_history_entry(cls, entry: Union[HistoryEntry, Dict[str, Any]]) -> None:
        """Append a HistoryEntry (or dict) to history and limit to latest 100 entries."""
        cls._ensure_dir()
        history = cls.load_history()
        record = entry.to_dict() if isinstance(entry, HistoryEntry) else entry
        history.insert(0, record)
        if len(history) > 100:
            history = history[:100]
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception:
            pass

    @classmethod
    def clear_history(cls) -> None:
        """Clear the history log."""
        cls._ensure_dir()
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
        except Exception:
            pass

    # ── Scratchpad (Time Notes) ──────────────────────────────────────────────

    @classmethod
    def load_scratchpad(cls) -> ScratchpadState:
        """Load persistent time notes scratchpad state."""
        cls._ensure_dir()
        if not os.path.exists(SCRATCHPAD_FILE):
            return ScratchpadState()
        try:
            with open(SCRATCHPAD_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return ScratchpadState.from_dict(data)
        except Exception:
            return ScratchpadState()

    @classmethod
    def save_scratchpad(cls, state: Union[ScratchpadState, Dict[str, Any]]) -> None:
        """Save time notes scratchpad state to disk."""
        cls._ensure_dir()
        payload = state.to_dict() if isinstance(state, ScratchpadState) else state
        try:
            with open(SCRATCHPAD_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            pass
