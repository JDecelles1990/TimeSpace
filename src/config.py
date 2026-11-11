"""Unified application configuration, theme palette, QSS stylesheet, UI dimensions, and typed state models."""
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Tuple, List

# ---------------------------------------------------------------------------
# Application Metadata & Global Shortcuts
# ---------------------------------------------------------------------------
APP_TITLE = "TimeSpace"
APP_REGISTRY_NAME = "TimeSpace"
HOTKEY = "ctrl+f8"
MEETING_HOTKEY = "ctrl+shift+m"
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
    "accent_link": "#38bdf8",
    "accent_danger": "#ef4444",
    "accent_warning": "#f59e0b",
    "accent_success": "#10b981",
    "text": "#f4f4f5",
    "text_muted": "#9ca3af",
    "border": "#2e2e3d",
    "glow_violet": "#8b5cf6",
    "glow_violet_light": "#a78bfa",
    "glow_cyan": "#22d3ee",
    "glow_green": "#34d399",
}

# ---------------------------------------------------------------------------
# Compact UI Layout Dimensions
# ---------------------------------------------------------------------------
UI_DIMENSIONS: Dict[str, Any] = {
    "window_width": 650,
    "window_height": 800,
    "min_window_width": 480,
    "min_window_height": 540,
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
    ("15m", 15),
    ("30m", 30),
    ("1h", 60),
    ("2h", 120),
]

SNOOZE_OPTIONS: List[int] = [5, 10, 15, 30]

SCRATCHPAD_TEXT_COLORS: List[Tuple[str, str]] = [
    ("Default (White)", "#f4f4f5"),
    ("Indigo Accent", "#818cf8"),
    ("Sky Cyan", "#38bdf8"),
    ("Emerald Green", "#34d399"),
    ("Amber Gold", "#fbbf24"),
    ("Coral Orange", "#fb923c"),
    ("Crimson Red", "#f87171"),
    ("Violet Purple", "#c084fc"),
]

GO_DIAG_ACTIONS: List[Tuple[str, str]] = [
    ("🌐 Ping & TCP Reach", "ping"),
    ("🔍 Port Scan", "port-scan"),
    ("🔒 TLS Cert Check", "tls-check"),
    ("🌍 HTTP/S Probe", "http-check"),
    ("🧭 DNS Lookup", "dns-lookup"),
    ("🧹 Flush DNS", "flush-dns"),
    ("🖧 Net Stack Triage", "net-status"),
    ("📊 Uptime & Sockets", "sys-info"),
]

GO_TARGET_PRESETS: List[Tuple[str, str]] = [
    ("Cloudflare DNS (1.1.1.1)", "1.1.1.1"),
    ("Google DNS (8.8.8.8)", "8.8.8.8"),
    ("GitHub (github.com)", "github.com"),
    ("Google (google.com)", "google.com"),
    ("Microsoft (microsoft.com)", "microsoft.com"),
    ("Localhost (127.0.0.1)", "127.0.0.1"),
]


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
    padding: 8px 6px 6px 6px;
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
    padding: 4px 5px;
    margin-right: 1px;
    font-size: 11px;
    font-weight: bold;
}}

QTabBar::tab:selected {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {COLORS["glow_cyan"]}, stop:1 {COLORS["glow_green"]});
    color: #0b0b10;
    border-color: {COLORS["glow_green"]};
}}

QTabBar::tab:hover {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {COLORS["glow_violet"]}, stop:1 {COLORS["glow_cyan"]});
    border: 1px solid {COLORS["glow_violet_light"]};
    border-bottom: none;
    color: #ffffff;
}}

QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QComboBox {{
    background-color: {COLORS["surface_light"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 3px 5px;
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
    padding: 3px 6px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {COLORS["glow_violet"]}, stop:1 {COLORS["glow_cyan"]});
    border: 1px solid {COLORS["glow_violet_light"]};
    color: #ffffff;
}}

QPushButton:pressed {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {COLORS["glow_cyan"]}, stop:1 {COLORS["glow_green"]});
    border: 1px solid {COLORS["glow_green"]};
    color: #0b0b10;
}}

QPushButton#primaryBtn {{
    background-color: {COLORS["accent"]};
    border-color: {COLORS["accent"]};
    color: #ffffff;
    font-weight: bold;
}}

QPushButton#primaryBtn:hover {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {COLORS["glow_violet"]}, stop:1 {COLORS["glow_cyan"]});
    border: 1px solid {COLORS["glow_violet_light"]};
}}

QPushButton#primaryBtn:pressed, QPushButton#successBtn:pressed, QPushButton#dangerBtn:pressed {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {COLORS["glow_cyan"]}, stop:1 {COLORS["glow_green"]});
    border: 1px solid {COLORS["glow_green"]};
    color: #0b0b10;
}}

QPushButton#successBtn {{
    background-color: {COLORS["accent_success"]};
    border-color: {COLORS["accent_success"]};
    color: #ffffff;
    font-weight: bold;
}}

QPushButton#successBtn:hover {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {COLORS["glow_violet"]}, stop:1 {COLORS["glow_cyan"]});
    border: 1px solid {COLORS["glow_violet_light"]};
}}

QPushButton#dangerBtn {{
    background-color: {COLORS["surface_light"]};
    border-color: {COLORS["border"]};
    color: {COLORS["accent_danger"]};
    font-weight: bold;
}}

QPushButton#dangerBtn:hover {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {COLORS["glow_violet"]}, stop:1 {COLORS["glow_cyan"]});
    border: 1px solid {COLORS["glow_violet_light"]};
    color: #ffffff;
}}

QSplitter::handle {{
    background-color: {COLORS["border"]};
}}

QSplitter::handle:vertical {{
    height: 4px;
    margin: 2px 0;
    border-radius: 2px;
}}

QSplitter::handle:horizontal {{
    width: 4px;
    margin: 0 2px;
    border-radius: 2px;
}}

QSplitter::handle:hover {{
    background-color: {COLORS["accent"]};
}}

QMenu {{
    background-color: {COLORS["surface"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 5px;
    padding: 4px;
}}

QMenu::item {{
    padding: 5px 14px 5px 10px;
    border-radius: 3px;
}}

QMenu::item:selected {{
    background-color: {COLORS["accent"]};
    color: #ffffff;
}}

QMenu::separator {{
    height: 1px;
    background: {COLORS["border"]};
    margin: 4px 6px;
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
    spacing: 5px;
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
    start_on_boot: bool = True
    hud_enabled: bool = False
    hud_x: int = 120
    hud_y: int = 80
    popup_corner: str = "bottom_right"
    overlay_opacity: int = 90
    app_opacity: int = 90
    custom_go_targets: List[Dict[str, str]] = field(default_factory=list)
    ahk_v2_exe_path: str = ""
    ahk_script_path: str = ""
    ahk_auto_start: bool = False
    meeting_mode_enabled: bool = False
    meeting_mode_auto_mic: bool = True
    meeting_mode_mute_sound: bool = True
    meeting_mode_until: float = 0.0

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
        if "app_opacity" in filtered:
            try:
                filtered["app_opacity"] = max(45, min(100, int(filtered["app_opacity"])))
            except (TypeError, ValueError):
                filtered["app_opacity"] = 90
        if "custom_go_targets" in filtered:
            raw_targets = filtered["custom_go_targets"]
            clean_targets: List[Dict[str, str]] = []
            if isinstance(raw_targets, list):
                for entry in raw_targets:
                    if isinstance(entry, dict):
                        host = str(entry.get("host", "") or "").strip()
                        label = str(entry.get("label", "") or host).strip()
                        if host:
                            clean_targets.append({"label": label or host, "host": host})
                    elif isinstance(entry, str) and entry.strip():
                        h = entry.strip()
                        clean_targets.append({"label": h, "host": h})
            filtered["custom_go_targets"] = clean_targets
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
    """Persistent state for the multi-pane Time Notes Scratchpads (Tab 4 Upper/Lower & Tab 5 Go)."""
    content: str = ""
    html: str = ""
    upper_content: str = ""
    upper_html: str = ""
    go_content: str = ""
    go_html: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScratchpadState":
        return cls(
            content=str(data.get("content", "") or ""),
            html=str(data.get("html", "") or ""),
            upper_content=str(data.get("upper_content", "") or ""),
            upper_html=str(data.get("upper_html", "") or ""),
            go_content=str(data.get("go_content", "") or ""),
            go_html=str(data.get("go_html", "") or ""),
            updated_at=str(data.get("updated_at", "") or ""),
        )


@dataclass
class AHKHotstringItem:
    """Typed record for an AutoHotkey v2 hotstring text expander."""
    trigger: str
    replacement: str
    options: str = ""
    is_expression: bool = False
    enabled: bool = True
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AHKHotstringItem":
        return cls(
            trigger=str(data.get("trigger", "") or "").strip(),
            replacement=str(data.get("replacement", "") or ""),
            options=str(data.get("options", "") or "").strip(),
            is_expression=bool(data.get("is_expression", False)),
            enabled=bool(data.get("enabled", True)),
            description=str(data.get("description", "") or "").strip(),
        )


DEFAULT_AHK_HOTSTRINGS: List[Dict[str, Any]] = [
    {
        "trigger": "btw",
        "replacement": "by the way",
        "options": "",
        "is_expression": False,
        "enabled": True,
        "description": "Standard expansion",
    },
    {
        "trigger": "omw",
        "replacement": "on my way",
        "options": "*",
        "is_expression": False,
        "enabled": True,
        "description": "Instant trigger without space",
    },
    {
        "trigger": "dts",
        "replacement": 'SendText(FormatTime(, "yyyy-MM-dd HH:mm:ss"))',
        "options": "X",
        "is_expression": True,
        "enabled": True,
        "description": "Current dynamic timestamp (YYYY-MM-DD HH:mm:ss)",
    },
    {
        "trigger": "ds",
        "replacement": 'SendText(FormatTime(, "yyyy-MM-dd"))',
        "options": "X",
        "is_expression": True,
        "enabled": True,
        "description": "Current dynamic date (YYYY-MM-DD)",
    },
    {
        "trigger": "tyvm",
        "replacement": "thank you very much!",
        "options": "*",
        "is_expression": False,
        "enabled": True,
        "description": "Quick courtesy note",
    },
    {
        "trigger": "@m",
        "replacement": "user@company.com",
        "options": "?",
        "is_expression": False,
        "enabled": True,
        "description": "Email address (triggers inside words)",
    },
    {
        "trigger": "sig",
        "replacement": "Best regards,\nIT Support Team\nTimeSpace Workspace",
        "options": "T",
        "is_expression": False,
        "enabled": True,
        "description": "Multi-line email / message signature",
    },
]

