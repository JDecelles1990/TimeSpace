"""Unified application configuration, theme palette, QSS stylesheet, UI dimensions, and typed state models."""
from dataclasses import dataclass, asdict
from typing import Dict, Any, Tuple, List

# ---------------------------------------------------------------------------
# Application Metadata & Global Shortcuts
# ---------------------------------------------------------------------------
APP_TITLE = "Timer & Rendez-vous"
APP_REGISTRY_NAME = "TimerAndRendezVous"
HOTKEY = "ctrl+f7"
FONT_FAMILY = "Segoe UI"

# ---------------------------------------------------------------------------
# Color Palette (Modern Compact Dark IT Theme)
# ---------------------------------------------------------------------------
COLORS: Dict[str, str] = {
    "bg_dark": "#111116",
    "surface": "#1a1a22",
    "surface_light": "#262632",
    "accent": "#6366f1",
    "accent_hover": "#4f46e5",
    "accent_danger": "#ef4444",
    "accent_warning": "#f59e0b",
    "accent_success": "#10b981",
    "text": "#f4f4f5",
    "text_muted": "#9ca3af",
    "border": "#2e2e3d",
}

# ---------------------------------------------------------------------------
# Compact UI Layout Dimensions
# ---------------------------------------------------------------------------
UI_DIMENSIONS: Dict[str, Any] = {
    "window_width": 650,
    "window_height": 800,
    "ring_size": 124,
    "ring_width": 8,
    "hud_width": 276,
    "hud_height": 40,
    "toast_width": 350,
    "toast_height": 132,
    "toast_height_rich": 162,
    "toast_margin_right": 18,
    "toast_margin_bottom": 48,
}

# ---------------------------------------------------------------------------
# Domain Presets & Categories
# ---------------------------------------------------------------------------
SOUND_PRESETS: Dict[str, str] = {
    "gentle": "Gentle Chime (C-Major Arpeggio)",
    "digital": "Digital Watch (Double Beep)",
    "urgent": "Urgent Siren (Two-Tone)",
    "custom": "Custom Audio File (MP3 / WAV)",
}

CATEGORIES: List[str] = [
    "📌 General",
    "💼 Work",
    "📞 Callback",
    "🔄 Follow-up",
    "🎫 Ticket",
    "🩺 Health",
    "🏠 Personal",
]

SLA_PRESETS: List[Tuple[str, int, str]] = []

QUICK_TIMER_PRESETS: List[Tuple[str, int]] = [
    ("15 Minutes", 15),
    ("30 Minutes", 30),
    ("1 Hour", 60),
    ("2 Hours", 120),
]

SNOOZE_OPTIONS: List[int] = [5, 10, 15, 30]


# ---------------------------------------------------------------------------
# Professional Dark-Mode PySide6 QSS Stylesheet
# ---------------------------------------------------------------------------
DARK_QSS = f"""
QWidget {{
    background-color: {COLORS["bg_dark"]};
    color: {COLORS["text"]};
    font-family: "{FONT_FAMILY}", sans-serif;
    font-size: 12px;
}}

QGroupBox {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    margin-top: 8px;
    padding: 8px 8px 6px 8px;
    font-weight: bold;
    color: {COLORS["accent"]};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 4px;
    background-color: {COLORS["bg_dark"]};
    color: {COLORS["accent"]};
}}

QTabWidget::pane {{
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    background-color: {COLORS["bg_dark"]};
    top: -1px;
}}

QTabBar::tab {{
    background-color: {COLORS["surface"]};
    color: {COLORS["text_muted"]};
    border: 1px solid {COLORS["border"]};
    border-bottom: none;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    padding: 5px 9px;
    margin-right: 2px;
    font-size: 11px;
    font-weight: bold;
}}

QTabBar::tab:selected {{
    background-color: {COLORS["accent"]};
    color: #ffffff;
    border-color: {COLORS["accent"]};
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLORS["surface_light"]};
    color: {COLORS["text"]};
}}

QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QComboBox {{
    background-color: {COLORS["surface_light"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 4px 6px;
    selection-background-color: {COLORS["accent"]};
}}

QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {COLORS["accent"]};
}}

QListWidget {{
    background-color: {COLORS["surface"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 5px;
    padding: 2px;
    font-size: 11px;
    outline: none;
}}

QListWidget::item {{
    padding: 2px 6px;
    border-radius: 3px;
}}

QListWidget::item:selected {{
    background-color: {COLORS["accent"]};
    color: #ffffff;
}}

QListWidget::item:hover:!selected {{
    background-color: {COLORS["surface_light"]};
}}

QPushButton {{
    background-color: {COLORS["surface_light"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 4px 10px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {COLORS["accent"]};
    border-color: {COLORS["accent"]};
    color: #ffffff;
}}

QPushButton#primaryBtn {{
    background-color: {COLORS["accent"]};
    border-color: {COLORS["accent"]};
    color: #ffffff;
    font-weight: bold;
}}

QPushButton#primaryBtn:hover {{
    background-color: {COLORS["accent_hover"]};
}}

QPushButton#successBtn {{
    background-color: {COLORS["accent_success"]};
    border-color: {COLORS["accent_success"]};
    color: #ffffff;
    font-weight: bold;
}}

QPushButton#dangerBtn {{
    background-color: {COLORS["surface_light"]};
    border-color: {COLORS["border"]};
    color: {COLORS["accent_danger"]};
    font-weight: bold;
}}

QPushButton#dangerBtn:hover {{
    background-color: {COLORS["accent_danger"]};
    border-color: {COLORS["accent_danger"]};
    color: #ffffff;
}}

QSlider::groove:horizontal {{
    border: 1px solid {COLORS["border"]};
    height: 6px;
    background: {COLORS["surface_light"]};
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background: {COLORS["accent"]};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: #ffffff;
    border: 2px solid {COLORS["accent"]};
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}

QCheckBox {{
    spacing: 6px;
    color: {COLORS["text"]};
}}
"""


# ---------------------------------------------------------------------------
# Unified Typed Configuration & State Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class AppConfig:
    """Unified, strongly-typed configuration object shared between backend services and PySide6 UI."""
    sound_type: str = "gentle"
    custom_sound_path: str = ""
    volume: int = 85
    default_snooze_minutes: int = 5
    gradual_escalation: bool = True
    start_on_boot: bool = False
    hud_enabled: bool = False
    hud_x: int = 120
    hud_y: int = 80
    popup_corner: str = "bottom_right"
    overlay_opacity: int = 90

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        if "overlay_opacity" in filtered:
            try:
                filtered["overlay_opacity"] = max(60, min(100, int(filtered["overlay_opacity"])))
            except (TypeError, ValueError):
                filtered["overlay_opacity"] = 90
        return cls(**filtered)


@dataclass
class HistoryEntry:
    """Typed record for completed, triggered, or snoozed reminders."""
    name: str
    kind: str
    category: str = "General"
    completed_at: str = ""
    status: str = "Triggered"
    url: str = ""
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoryEntry":
        return cls(
            name=data.get("name", "Event"),
            kind=data.get("kind", "timer"),
            category=data.get("category", "General"),
            completed_at=data.get("completed_at", ""),
            status=data.get("status", "Triggered"),
            url=str(data.get("url", "") or ""),
            note=str(data.get("note", "") or ""),
        )


@dataclass
class ScratchpadState:
    """Persistent state for the Time Notes Scratchpad (Tab 4)."""
    content: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScratchpadState":
        return cls(
            content=data.get("content", ""),
            updated_at=data.get("updated_at", ""),
        )
