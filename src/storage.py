"""Persistence layer for AppConfig, reminders, history, scratchpad, and diagnostic reports."""
import datetime
import json
import os
import platform
import re
import sys
from typing import Dict, Any, List, Optional, Union
from src.config import AppConfig, HistoryEntry, ScratchpadState

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
REPORTS_DIR = r"C:\Temp" if sys.platform == "win32" else "/tmp"
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
    def delete_history_indices(cls, indices: List[int]) -> int:
        """Remove history entries at the specified 0-based indices and persist."""
        cls._ensure_dir()
        history = cls.load_history()
        drop_set = {i for i in indices if 0 <= i < len(history)}
        if not drop_set:
            return 0
        updated = [item for idx, item in enumerate(history) if idx not in drop_set]
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(updated, f, indent=2)
        except Exception:
            pass
        return len(drop_set)

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

    @classmethod
    def export_scratchpad_note(
        cls,
        title: str,
        content: str,
        filepath: Optional[str] = None,
    ) -> str:
        """Export a Scratchpad pane's notes directly to C:\\Temp (created if missing) and return its absolute filepath."""
        clean_title = re.sub(r"^[^\w]+", "", title).strip() or "Scratchpad"
        slug = re.sub(r"[^A-Za-z0-9._-]+", "_", clean_title).strip("_") or "Notes"
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"TimeSpace_Scratchpad_{slug}_{stamp}.md"

        now_local = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body = (
            f"# TimeSpace — {clean_title}\n\n"
            f"- **Exported**: `{now_local}`\n\n"
            "---\n\n"
            f"{content.strip()}\n"
        )

        if filepath and filepath.strip():
            raw_dest = filepath.strip()
            dest = raw_dest if os.path.isabs(raw_dest) or os.path.dirname(raw_dest) else os.path.join(REPORTS_DIR, raw_dest)
            parent = os.path.dirname(os.path.abspath(dest))
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(body)
            return os.path.abspath(dest)

        try:
            os.makedirs(REPORTS_DIR, exist_ok=True)
            dest = os.path.join(REPORTS_DIR, fname)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(body)
            return os.path.abspath(dest)
        except OSError:
            cls._ensure_dir()
            dest = os.path.join(DATA_DIR, fname)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(body)
            return os.path.abspath(dest)

    # ── Diagnostic Incident Reports (.md / .txt / .json) ─────────────────────

    @classmethod
    def default_report_path(cls, target: str, fmt: str = "md") -> str:
        """Build a default timestamped diagnostic report filepath inside C:\\Temp (created if missing)."""
        os.makedirs(REPORTS_DIR, exist_ok=True)
        ext = fmt.lower().lstrip(".")
        if ext not in ("md", "txt", "json"):
            ext = "md"
        safe_tgt = re.sub(r"[^A-Za-z0-9._-]+", "_", target.strip() or "1.1.1.1").strip("_") or "target"
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(REPORTS_DIR, f"TimeSpace_Diag_{safe_tgt}_{stamp}.{ext}")

    @classmethod
    def export_diagnostic_report(
        cls,
        output_text: str,
        target: str,
        filepath: Optional[str] = None,
        fmt: str = "md",
    ) -> str:
        """Format and save a diagnostic report (.md, .txt, or .json) in C:\\Temp and return its absolute filepath."""
        os.makedirs(REPORTS_DIR, exist_ok=True)
        clean_out = output_text.strip()
        clean_tgt = target.strip() or "1.1.1.1"
        if filepath and filepath.strip():
            raw_dest = filepath.strip()
            dest = raw_dest if os.path.isabs(raw_dest) or os.path.dirname(raw_dest) else os.path.join(REPORTS_DIR, raw_dest)
        else:
            dest = cls.default_report_path(clean_tgt, fmt)
        parent = os.path.dirname(os.path.abspath(dest))
        if parent:
            os.makedirs(parent, exist_ok=True)

        ext = os.path.splitext(dest)[1].lower().lstrip(".") or fmt.lower().lstrip(".")
        now_local = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        goos = "windows" if sys.platform == "win32" else ("darwin" if sys.platform == "darwin" else "linux")
        arch = platform.machine().lower() or "amd64"

        if ext == "json":
            payload = {
                "report": "TimeSpace Diagnostic Report",
                "timestamp": now_utc,
                "local_time": now_local,
                "os": goos,
                "arch": arch,
                "target": clean_tgt,
                "output": clean_out,
            }
            body = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        elif ext == "txt":
            body = (
                "===================================================================\n"
                "  TimeSpace Diagnostic Incident Report\n"
                f"  Generated : {now_local}\n"
                f"  Target    : {clean_tgt}\n"
                f"  Platform  : {goos}/{arch}\n"
                "===================================================================\n\n"
                f"{clean_out}\n"
            )
        else:
            body = (
                "# TimeSpace Diagnostic Incident Report\n\n"
                f"- **Generated**: `{now_local}`\n"
                f"- **Target**: `{clean_tgt}`\n"
                f"- **Platform**: `{goos}/{arch}`\n\n"
                "## Console Output\n\n"
                "```text\n"
                f"{clean_out}\n"
                "```\n"
            )

        with open(dest, "w", encoding="utf-8") as f:
            f.write(body)
        return os.path.abspath(dest)
