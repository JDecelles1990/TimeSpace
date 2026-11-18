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
# Color Palette (Cyber-Aurora Neon Glass Theme)
# ---------------------------------------------------------------------------
COLORS: Dict[str, str] = {
    "bg_dark": "#0c0d16",
    "surface": "#141625",
    "surface_light": "#1e2238",
    "accent": "#6366f1",
    "accent_hover": "#818cf8",
    "accent_link": "#38bdf8",
    "accent_danger": "#f43f5e",
    "accent_warning": "#f59e0b",
    "accent_success": "#10b981",
    "text": "#f8fafc",
    "text_muted": "#94a3b8",
    "border": "#2e355b",
    "border_shine": "#4f5b9e",
    "glow_violet": "#8b5cf6",
    "glow_violet_light": "#c084fc",
    "glow_cyan": "#22d3ee",
    "glow_green": "#34d399",
    "glow_magenta": "#f43f5e",
    "glow_gold": "#fbbf24",
    "glow_specular": "#e0f2fe",
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

RDV_LEAD_OPTIONS: List[Tuple[str, int]] = [
    ("At time (0m)", 0),
    ("5m before", 5),
    ("10m before", 10),
    ("15m before", 15),
    ("45m before", 45),
    ("1 hour before", 60),
    ("2 hours before", 120),
    ("1 day before", 1440),
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
# Cyber-Aurora Neon Glass PySide6 QSS Stylesheet
# ---------------------------------------------------------------------------
DARK_QSS = f"""
QWidget {{
    background-color: {COLORS["bg_dark"]};
    color: {COLORS["text"]};
    font-family: "{FONT_FAMILY}", sans-serif;
    font-size: 12px;
}}

QLabel {{
    background-color: transparent;
}}

QGroupBox {{
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #1d213a, stop:0.12 #141625, stop:1 #0f111d);
    border: 1px solid {COLORS["border"]};
    border-top: 1px solid {COLORS["border_shine"]};
    border-radius: 6px;
    margin-top: 8px;
    padding: 8px 6px 6px 6px;
    font-weight: bold;
    color: {COLORS["glow_cyan"]};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
    background-color: {COLORS["bg_dark"]};
    color: {COLORS["glow_cyan"]};
}}

QTabWidget::pane {{
    border: 1px solid {COLORS["border"]};
    border-top: 1px solid {COLORS["border_shine"]};
    border-radius: 6px;
    background-color: {COLORS["bg_dark"]};
    top: -1px;
}}

QTabBar::tab {{
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #262b4d, stop:0.45 #1a1d33, stop:1 #131524);
    color: {COLORS["text_muted"]};
    border: 1px solid {COLORS["border"]};
    border-top: 1px solid {COLORS["border_shine"]};
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
        stop:0 {COLORS["glow_cyan"]}, stop:0.55 {COLORS["glow_green"]}, stop:1 #6ee7b7);
    color: #090a12;
    border: 1px solid {COLORS["glow_specular"]};
    border-bottom: none;
}}

QTabBar::tab:hover:!selected {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {COLORS["glow_violet"]}, stop:0.5 {COLORS["accent"]}, stop:1 {COLORS["glow_cyan"]});
    border: 1px solid {COLORS["glow_violet_light"]};
    border-bottom: none;
    color: #ffffff;
}}

QTabBar::tab:focus {{
    border: 1.5px solid {COLORS["glow_specular"]};
    border-bottom: none;
    outline: none;
}}

QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QComboBox {{
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #171a2e, stop:0.25 #1e2238, stop:1 #141728);
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-top: 1px solid {COLORS["border_shine"]};
    border-radius: 4px;
    padding: 3px 5px;
    selection-background-color: {COLORS["glow_violet"]};
    selection-color: #ffffff;
}}

QLineEdit:hover, QPlainTextEdit:hover, QTextEdit:hover, QSpinBox:hover, QComboBox:hover {{
    border: 1px solid {COLORS["glow_violet_light"]};
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #201e3d, stop:1 #182038);
}}

QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {COLORS["glow_cyan"]};
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #152538, stop:1 #14192e);
}}

QComboBox::drop-down {{
    border: none;
    width: 18px;
    background: transparent;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS["surface"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["glow_cyan"]};
    border-radius: 4px;
    selection-background-color: {COLORS["glow_violet"]};
    selection-color: #ffffff;
    outline: none;
}}

QListWidget {{
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #16192c, stop:1 #0e101c);
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-top: 1px solid {COLORS["border_shine"]};
    border-radius: 5px;
    padding: 2px;
    font-size: 11px;
    outline: none;
}}

QListWidget:focus {{
    border: 1px solid {COLORS["glow_cyan"]};
}}

QListWidget::item {{
    padding: 2px 6px;
    border-radius: 3px;
}}

QListWidget::item:selected {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS["accent"]}, stop:0.55 {COLORS["glow_violet"]}, stop:1 {COLORS["glow_cyan"]});
    color: #ffffff;
    font-weight: bold;
}}

QListWidget::item:hover:!selected {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #28244d, stop:1 #1b2f45);
    color: {COLORS["glow_specular"]};
}}

QPushButton {{
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #323962, stop:0.45 #232846, stop:1 #191c33);
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-top: 1px solid {COLORS["border_shine"]};
    border-radius: 4px;
    padding: 3px 6px;
    font-weight: 600;
    outline: none;
}}

QPushButton:focus {{
    border: 1px solid {COLORS["glow_cyan"]};
}}

QPushButton:hover {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #9333ea, stop:0.5 {COLORS["glow_violet"]}, stop:1 {COLORS["glow_cyan"]});
    border: 1px solid {COLORS["glow_cyan"]};
    border-top: 1px solid {COLORS["glow_specular"]};
    color: #ffffff;
}}

QPushButton:pressed {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {COLORS["glow_specular"]}, stop:0.35 {COLORS["glow_cyan"]}, stop:1 {COLORS["glow_green"]});
    border: 1px solid {COLORS["glow_green"]};
    color: #090a12;
}}

QPushButton#primaryBtn {{
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #818cf8, stop:0.45 #6366f1, stop:1 #4f46e5);
    border: 1px solid {COLORS["accent"]};
    border-top: 1px solid #a5b4fc;
    color: #ffffff;
    font-weight: bold;
}}

QPushButton#primaryBtn:hover {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {COLORS["glow_cyan"]}, stop:0.5 {COLORS["accent"]}, stop:1 {COLORS["glow_violet"]});
    border: 1px solid {COLORS["glow_specular"]};
}}

QPushButton#primaryBtn:pressed, QPushButton#successBtn:pressed {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {COLORS["glow_specular"]}, stop:0.4 {COLORS["glow_cyan"]}, stop:1 {COLORS["glow_green"]});
    border: 1px solid {COLORS["glow_specular"]};
    color: #090a12;
}}

QPushButton#successBtn {{
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #34d399, stop:0.45 #10b981, stop:1 #059669);
    border: 1px solid {COLORS["accent_success"]};
    border-top: 1px solid #6ee7b7;
    color: #ffffff;
    font-weight: bold;
}}

QPushButton#successBtn:hover {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {COLORS["glow_green"]}, stop:1 {COLORS["glow_cyan"]});
    border: 1px solid {COLORS["glow_specular"]};
    color: #090a12;
}}

QPushButton#dangerBtn {{
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #351b2b, stop:0.5 #271523, stop:1 #1d101b);
    border: 1px solid #9f1239;
    border-top: 1px solid #e11d48;
    color: #fda4af;
    font-weight: bold;
}}

QPushButton#dangerBtn:hover {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {COLORS["glow_magenta"]}, stop:1 #fb7185);
    border: 1px solid #fecdd3;
    color: #ffffff;
}}

QPushButton#dangerBtn:pressed {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #fda4af, stop:1 {COLORS["glow_magenta"]});
    border: 1px solid #ffffff;
    color: #090a12;
}}

QPushButton#dangerBtn:focus {{
    border: 1px solid #fecdd3;
}}

QPushButton#primaryBtn:focus, QPushButton#successBtn:focus {{
    border: 1px solid {COLORS["glow_specular"]};
}}

QSplitter::handle {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #262b4d, stop:0.5 #3b447a, stop:1 #262b4d);
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
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS["glow_violet"]}, stop:0.5 {COLORS["glow_cyan"]}, stop:1 {COLORS["glow_green"]});
}}

QMenu {{
    background-color: {COLORS["surface"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["glow_violet_light"]};
    border-radius: 5px;
    padding: 4px;
}}

QMenu::item {{
    padding: 5px 14px 5px 10px;
    border-radius: 3px;
}}

QMenu::item:selected {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS["glow_violet"]}, stop:1 {COLORS["glow_cyan"]});
    color: #ffffff;
}}

QMenu::separator {{
    height: 1px;
    background: {COLORS["border_shine"]};
    margin: 4px 6px;
}}

QSlider::groove:horizontal {{
    border: 1px solid {COLORS["border"]};
    height: 6px;
    background: #101220;
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS["glow_violet"]}, stop:0.55 {COLORS["glow_cyan"]}, stop:1 {COLORS["glow_green"]});
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.55, fx:0.4, fy:0.4,
        stop:0 #ffffff, stop:0.65 {COLORS["glow_cyan"]}, stop:1 {COLORS["glow_violet"]});
    border: 2px solid {COLORS["glow_specular"]};
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}

QSlider::handle:horizontal:hover {{
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.55, fx:0.4, fy:0.4,
        stop:0 #ffffff, stop:0.6 {COLORS["glow_green"]}, stop:1 {COLORS["glow_cyan"]});
    border: 2px solid #ffffff;
}}

QSlider::handle:horizontal:pressed {{
    background: {COLORS["glow_specular"]};
    border: 2px solid {COLORS["glow_green"]};
}}

QProgressBar {{
    background-color: #121526;
    border: 1px solid {COLORS["border_shine"]};
    border-radius: 4px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS["glow_violet"]}, stop:0.5 {COLORS["glow_cyan"]}, stop:1 {COLORS["glow_green"]});
    border-radius: 3px;
}}

QScrollBar:vertical {{
    background: #0e101d;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #4f5b9e, stop:1 #2e355b);
    min-height: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {COLORS["glow_violet"]}, stop:1 {COLORS["glow_cyan"]});
}}

QScrollBar::handle:vertical:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {COLORS["glow_cyan"]}, stop:1 {COLORS["glow_green"]});
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    height: 0px;
    background: none;
}}

QScrollBar:horizontal {{
    background: #0e101d;
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4f5b9e, stop:1 #2e355b);
    min-width: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS["glow_violet"]}, stop:1 {COLORS["glow_cyan"]});
}}

QScrollBar::handle:horizontal:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS["glow_cyan"]}, stop:1 {COLORS["glow_green"]});
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    width: 0px;
    background: none;
}}

QCheckBox {{
    spacing: 5px;
    color: {COLORS["text"]};
    outline: none;
}}

QCheckBox:focus {{
    color: {COLORS["glow_specular"]};
}}

QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 1px solid {COLORS["border_shine"]};
    background-color: #141625;
}}

QCheckBox::indicator:hover, QCheckBox::indicator:focus {{
    border: 1px solid {COLORS["glow_cyan"]};
}}

QCheckBox::indicator:checked {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {COLORS["glow_cyan"]}, stop:1 {COLORS["glow_green"]});
    border: 1px solid {COLORS["glow_specular"]};
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

