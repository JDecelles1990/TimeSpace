# State Models, Configuration Tokens & Persistence (`Docs/STATE_AND_CONFIG.md`)

> **Canonical Scope**: This document is the single source of truth for all `@dataclass` state models, theme & geometry constants in `src/config.py`, `DARK_QSS` styling conventions, and JSON persistence contracts in `src/storage.py`.
> *(For runtime threading and OS subsystems, see [ARCHITECTURE.md](ARCHITECTURE.md). For module imports and signatures, see [COMPONENT_MAP.md](COMPONENT_MAP.md).)*

---

## 1. Typed Dataclass State Models

All data exchanged between the PySide6 UI and backend services uses `@dataclass` models with `.to_dict()` and `.from_dict()` serialization methods. Unknown or deprecated JSON keys are automatically filtered out on load so schema upgrades never crash startup.

### 1.1 `AppConfig` (`src/config.py`)
Persisted to `data/settings.json` via `Storage.load_config() -> AppConfig` and `Storage.save_config(config)`. Passed directly to `SoundPlayer(config=...)` and `AlarmDialog(..., config=...)`, and synchronized live via `SoundPlayer.update_config(config)`.

| Field | Type | Default | Purpose |
|---|---|---|---|
| `sound_type` | `str` | `"gentle"` | Active preset key from `SOUND_PRESETS` (`"gentle"`, `"digital"`, `"urgent"`, `"custom"`). |
| `custom_sound_path` | `str` | `""` | Absolute path to a user-selected `.mp3` or `.wav` file when `sound_type == "custom"`. |
| `volume` | `int` | `85` | Master hardware alarm volume percentage (`0`–`100`), scaled to `0`–`1000` for Windows MCI. |
| `default_snooze_minutes` | `int` | `5` | Pre-selected snooze duration in `AlarmDialog` (`5`, `10`, `15`, or `30`). |
| `gradual_escalation` | `bool` | `True` | Enables 15-second volume ramp-up (MCI) or tempo acceleration (`winsound`). |
| `start_on_boot` | `bool` | `False` | Mirrors Windows `HKCU\...\Run` startup registration state. |
| `hud_enabled` | `bool` | `False` | Restores `FloatingMiniHUD` visibility automatically on launch. |
| `hud_x` | `int` | `120` | Last saved screen X coordinate of `FloatingMiniHUD`. |
| `hud_y` | `int` | `80` | Last saved screen Y coordinate of `FloatingMiniHUD`. |
| `popup_corner` | `str` | `"bottom_right"` | Anchor corner preference for `AlarmDialog`. |
| `overlay_opacity` | `int` | `90` | Window opacity percentage (`60`–`100`, clamped on load) applied to `FloatingMiniHUD` and `AlarmDialog` cards. |
| `app_opacity` | `int` | `90` | Main application window opacity percentage (`45`–`100`, default `90`, clamped on load) controlled by the synchronized Top Header opacity slider (`slider_header_opacity`) and Settings App Transparency slider (`slider_app_opacity`). |
| `custom_go_targets` | `List[Dict[str, str]]` | `[]` | User-saved favorite diagnostic target bookmarks (`{"label": ..., "host": ...}`) displayed at the top of the `5. Go ⏱️` presets dropdown (`⭐ Label (host)`) and accessible in the Interactive Go CLI via `bm`. |

### 1.2 `ScheduledItem` (`src/scheduler.py`)
Persisted as a JSON array in `data/reminders.json` via `Storage.load_reminders()` / `Storage.save_reminders()`. Protected in memory by `ReminderScheduler._lock`.

| Field | Type | Default | Purpose |
|---|---|---|---|
| `id` | `str` | UUID4 | Unique identifier used for pause/resume and deletion. |
| `kind` | `str` | — | `"timer"` or `"rendez-vous"`. |
| `name` | `str` | — | Display label (auto-prefixed with `[Client/Ticket]` for referenced timers or `[Nm Early]` when `lead_time_min > 0`). |
| `target_time` | `float` | — | Unix epoch timestamp (`time.time()`) when the item triggers next. |
| `repeat_sec` | `int` | `0` | Fixed interval in seconds for auto-repeating countdown timers (`0` = one-shot). |
| `original_duration` | `float` | `0.0` | Total initial countdown seconds (used to compute `CircularProgressRing` arc ratio; auto-initialized in `__post_init__` if `<= 0`). |
| `repeat_rule` | `str` | `"none"` | Calendar recurrence rule for Rendez-vous (`"none"`, `"daily"`, `"weekly"`, `"monthly"`). |
| `is_paused` | `bool` | `False` | Whether countdown progression is currently frozen. |
| `remaining_paused` | `float` | `0.0` | Remaining seconds captured at pause time; restores `target_time = now + remaining_paused` on resume. |
| `category` | `str` | `"General"` | Category badge string from `CATEGORIES`. |
| `lead_time_min` | `int` | `0` | Early warning offset in minutes (`0`, `5`, `10`, `15`) subtracted from initial `target_time`. |
| `url` | `str` | `""` | Optional web URL, bare domain, custom protocol URI, or local Windows file/folder path for 1-click launching. |
| `note` | `str` | `""` | Optional short text note surfaced on `AlarmDialog`, `Activity`, `History`, and `.ics` `DESCRIPTION`. |
| `anchor_day` | `int` | `0` | Original calendar day-of-month (`1`–`31`) preserved across shorter months for `"monthly"` recurrence (`Jan 31 -> Feb 28/29 -> Mar 31`). |

### 1.3 `HistoryEntry` (`src/config.py`)
Persisted to `data/history.json` (newest first, capped at **100** entries) via `Storage.add_history_entry(entry)`.

| Field | Type | Default | Purpose |
|---|---|---|---|
| `name` | `str` | — | Reminder title (prefixed with `[Snooze Nm]` on snooze actions). |
| `kind` | `str` | — | `"timer"` or `"rendez-vous"`. |
| `category` | `str` | `"General"` | Category badge at trigger time. |
| `completed_at` | `str` | `""` | Formatted timestamp (`"%b %d, %H:%M:%S"`). |
| `status` | `str` | `"Triggered"` | Lifecycle event (`"Triggered"`, `"Dismissed"`, `"Opened Link"`, `"Snoozed Nm"`). |
| `url` | `str` | `""` | Optional attached URL/path preserved for 1-click re-opening from Tab 5 (`5. History 📜`). |
| `note` | `str` | `""` | Optional attached short note preserved in audit details and clipboard copy. |

### 1.4 `ScratchpadState` (`src/config.py`)
Persisted to `data/scratchpad.json` via `Storage.load_scratchpad()` / `Storage.save_scratchpad(state)`.

| Field | Type | Default | Purpose |
|---|---|---|---|
| `content` | `str` | `""` | Plain-text body of the Lower Scratchpad in Tab 4 (`4. Scratchpad 📝`). |
| `html` | `str` | `""` | Rich-text HTML of the Lower Scratchpad in Tab 4 (`4. Scratchpad 📝`). |
| `upper_content` | `str` | `""` | Plain-text body of the Upper Scratchpad in Tab 4 (`4. Scratchpad 📝`). |
| `upper_html` | `str` | `""` | Rich-text HTML of the Upper Scratchpad in Tab 4 (`4. Scratchpad 📝`). |
| `go_content` | `str` | `""` | Plain-text body of the 3rd Go Scratchpad in Tab 5 (`5. Go ⏱️`). |
| `go_html` | `str` | `""` | Rich-text HTML of the 3rd Go Scratchpad in Tab 5 (`5. Go ⏱️`). |
| `updated_at` | `str` | `""` | Last auto-save time (`"%H:%M:%S"`) displayed in the Scratchpad toolbars. |

---

## 2. Application Constants, Geometry & Domain Presets (`src/config.py`)

### 2.1 Identity & Shortcut Constants
- `APP_TITLE = "TimeSpace"` — Window title, tray title, and Windows Action Center toast `app_id`.
- `APP_REGISTRY_NAME = "TimeSpace"` — Registry value name under `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
- `HOTKEY = "ctrl+f7"` — Global show/hide hotkey parsed by `GlobalHotkeyListener`.
- `FONT_FAMILY = "Segoe UI"` — Primary UI typeface (`Consolas` is used inside the Scratchpad editor).

### 2.2 `UI_DIMENSIONS` Pixel Specification
| Key | Value | Component |
|---|---|---|
| `window_width` / `window_height` | `650` × `800` | Default `MainApp` window geometry (minimum size `min_window_width` × `min_window_height` = `480` × `540`). |
| `ring_size` / `ring_width` | `124` / `8` | `CircularProgressRing` square canvas size and stroke width in pixels. |
| `hud_width` / `hud_height` | `276` × `40` | `FloatingMiniHUD` frameless desktop pill dimensions. |
| `toast_width` / `toast_height` | `350` × `132` | Standard `AlarmDialog` bottom-right notification card dimensions. |
| `toast_height_rich` | `162` | Expanded `AlarmDialog` height when displaying an attached `note` and/or `🔗 Open Link` button. |
| `toast_margin_right` / `toast_margin_bottom` | `18` / `48` | Screen-edge clearance from primary monitor work area. |

### 2.3 `COLORS` Dark Palette & `DARK_QSS` Selectors
- **Surfaces & Borders**: `bg_dark` (`#111116`), `surface` (`#1a1a22`), `surface_light` (`#262632`), `border` (`#2e2e3d`).
- **Button Glow Gradients**: `glow_violet` (`#8b5cf6`), `glow_violet_light` (`#a78bfa`), `glow_cyan` (`#22d3ee`), `glow_green` (`#34d399`) — all `QPushButton:hover` states fill violet ➔ cyan, `:pressed` states fill cyan ➔ green; `QTabBar::tab:hover` fills violet ➔ cyan and `QTabBar::tab:selected` fills cyan ➔ green.
- **Typography**: `text` (`#f4f4f5`), `text_muted` (`#9ca3af`).
- **Semantic Accents**: `accent` (`#6366f1`), `accent_hover` (`#4f46e5`), `accent_link` (`#38bdf8`), `accent_success` (`#10b981`), `accent_warning` (`#f59e0b`), `accent_danger` (`#ef4444`).
- **QSS Semantic `objectName` IDs & Popup Menus** (applied via `widget.setObjectName(...)` or `DARK_QSS`):
  - `#primaryBtn`: Indigo primary action button (`Create ⚡`, `Start Timer ▶`, `Add RDV 📅`, `+Timestamp`).
  - `#successBtn`: Emerald confirmation/action button (`Save Settings ✓`, `🔗 Open Link`).
  - `#dangerBtn`: Muted button with crimson text that fills crimson on hover (`⏹ Stop`, `🗑️ Delete`, `🧹 Clear`).
  - `QMenu`: Dark surface popup menu with indigo hover highlight for Scratchpad text color selection.
- **List Density**: `QListWidget` uses `11px` font and `2px 6px` item padding so the persistent Active Reminders Queue displays 7–9+ rows simultaneously and Activity lists display ~15+ rows.

### 2.4 Shared Domain Presets
- `QUICK_TIMER_PRESETS`: `[("15m", 15), ("30m", 30), ("1h", 60), ("2h", 120)]`
- `CATEGORIES`: `["📌 General", "💼 Work", "📞 Callback", "🔄 Follow-up", "🎫 Ticket", "🩺 Health", "🏠 Personal"]`
- `SNOOZE_OPTIONS`: `[5, 10, 15, 30]` (minutes)
- `SOUND_PRESETS`: `{"gentle": ..., "digital": ..., "urgent": ..., "custom": ...}`
- `SCRATCHPAD_TEXT_COLORS`: `[("Default (White)", "#f4f4f5"), ("Indigo Accent", "#818cf8"), ("Sky Cyan", "#38bdf8"), ("Emerald Green", "#34d399"), ("Amber Gold", "#fbbf24"), ("Coral Orange", "#fb923c"), ("Crimson Red", "#f87171"), ("Violet Purple", "#c084fc")]`
- `GO_DIAG_ACTIONS`: `[("🌐 Ping & TCP Reach", "ping"), ("🔍 Port Scan", "port-scan"), ("🔒 TLS Cert Check", "tls-check"), ("🌍 HTTP/S Probe", "http-check"), ("🧭 DNS Lookup", "dns-lookup"), ("🧹 Flush DNS", "flush-dns"), ("🖧 Net Stack Triage", "net-status"), ("📊 Uptime & Sockets", "sys-info")]`
- `GO_TARGET_PRESETS`: `[("Cloudflare DNS (1.1.1.1)", "1.1.1.1"), ("Google DNS (8.8.8.8)", "8.8.8.8"), ("GitHub (github.com)", "github.com"), ("Google (google.com)", "google.com"), ("Microsoft (microsoft.com)", "microsoft.com"), ("Localhost (127.0.0.1)", "127.0.0.1")]`
- `SLA_PRESETS`: `[]` *(emptied intentionally; kept as an exported symbol for package backward compatibility).*

---

## 3. JSON Files & Legacy Compatibility (`src/storage.py`)

All runtime state is stored locally in `data/` (auto-created on first call via `Storage._ensure_dir()`):
- `data/settings.json` — `AppConfig` object (`data/settings.example.json` provides a tracked reference template).
- `data/reminders.json` — Array of active `ScheduledItem` dicts.
- `data/history.json` — Array of `HistoryEntry` dicts (max 100).
- `data/scratchpad.json` — `ScratchpadState` object.

*Note*: `Storage.load_settings()` and `Storage.save_settings()` remain as thin compatibility wrappers around `load_config()` and `save_config()`, and `save_config` / `add_history_entry` / `save_scratchpad` accept either typed dataclasses or plain `dict` instances.
