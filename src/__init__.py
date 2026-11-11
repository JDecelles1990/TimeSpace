"""TimeSpace application package (PySide6 F7Hub Module & Standalone App)."""
from src.config import (
    APP_TITLE,
    APP_REGISTRY_NAME,
    HOTKEY,
    FONT_FAMILY,
    COLORS,
    DARK_QSS,
    UI_DIMENSIONS,
    SOUND_PRESETS,
    CATEGORIES,
    SLA_PRESETS,
    QUICK_TIMER_PRESETS,
    SNOOZE_OPTIONS,
    SCRATCHPAD_TEXT_COLORS,
    GO_DIAG_ACTIONS,
    GO_TARGET_PRESETS,
    AppConfig,
    HistoryEntry,
    ScratchpadState,
    AHKHotstringItem,
    DEFAULT_AHK_HOTSTRINGS,
    MEETING_HOTKEY,
)
from src.storage import Storage
from src.scheduler import ReminderScheduler, ScheduledItem
from src.hotkey_manager import GlobalHotkeyListener
from src.meeting_detector import is_microphone_in_use, get_active_microphone_apps
from src.go_tab import GoTroubleshootingTab
from src.ahk_manager import AHKProcessManager, find_ahk_v2_exe, generate_ahk_v2_script
from src.ahk_dialog import AHKHotstringsDialog, AHKItemEditDialog
from src.gui import TimerRendezVousWidget, TimeSpaceWidget, MainApp

__all__ = [
    "APP_TITLE",
    "APP_REGISTRY_NAME",
    "HOTKEY",
    "FONT_FAMILY",
    "COLORS",
    "DARK_QSS",
    "UI_DIMENSIONS",
    "SOUND_PRESETS",
    "CATEGORIES",
    "SLA_PRESETS",
    "QUICK_TIMER_PRESETS",
    "SNOOZE_OPTIONS",
    "SCRATCHPAD_TEXT_COLORS",
    "GO_DIAG_ACTIONS",
    "GO_TARGET_PRESETS",
    "AppConfig",
    "HistoryEntry",
    "ScratchpadState",
    "Storage",
    "ReminderScheduler",
    "ScheduledItem",
    "GlobalHotkeyListener",
    "GoTroubleshootingTab",
    "AHKHotstringItem",
    "DEFAULT_AHK_HOTSTRINGS",
    "MEETING_HOTKEY",
    "is_microphone_in_use",
    "get_active_microphone_apps",
    "AHKProcessManager",
    "find_ahk_v2_exe",
    "generate_ahk_v2_script",
    "AHKHotstringsDialog",
    "AHKItemEditDialog",
    "TimerRendezVousWidget",
    "TimeSpaceWidget",
    "MainApp",
]
