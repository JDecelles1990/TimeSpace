# Architecture Specification (`Docs/ARCHITECTURE.md`)

> **Canonical Scope**: This document specifies runtime execution modes (F7Hub embedded vs. standalone), the PySide6 concurrency & signal-marshaling architecture, and native Windows OS subsystems.
> *(For dataclass schemas, QSS tokens, and JSON files, see [STATE_AND_CONFIG.md](STATE_AND_CONFIG.md). For file trees and class signatures, see [COMPONENT_MAP.md](COMPONENT_MAP.md).)*

---

## 1. Dual-Mode Execution & F7Hub Embedding

The UI layer in `src/gui.py` is split into two distinct classes to support both modular monolith hosting and standalone desktop operation:

1. **Embedded F7Hub Module (`TimerRendezVousWidget(QWidget)`)**:
   - Owns all 6 tabs, the Hero Deck (`CircularProgressRing` + Natural Input), the persistent Active Reminders Queue, `FloatingMiniHUD`, `AlarmDialog` popups, `SoundPlayer`, and `ReminderScheduler`.
   - Does **not** hijack the host window's `closeEvent`, system tray, or OS global hotkeys.
   - Embeds into any PySide6 container with zero boilerplate:
     ```python
     from src import TimerRendezVousWidget
     parent_stack_or_layout.addWidget(TimerRendezVousWidget(parent_window))
     ```

2. **Standalone Application Shell (`MainApp(QMainWindow)` & `run.py`)**:
   - Wraps `TimerRendezVousWidget` as its central widget (`650x800`, min `600x720`).
   - Adds `TrayManager` (`pystray`), `GlobalHotkeyListener` (`Ctrl+F7`), 1-second tray tooltip synchronization, `--minimized` startup flag support, and `closeEvent` interception (hides to tray instead of terminating).
   - **Virtualenv Auto-Relaunch (`run.py`)**: `_ensure_pyside6_interpreter()` checks `import PySide6` at startup; if launched from a global Python interpreter missing `PySide6`, it transparently re-executes the script with `.venv\Scripts\python.exe` while forwarding CLI arguments.

---

## 2. Concurrency & PySide6 Signal-Slot Model

PySide6 forbids touching `QWidget` instances from non-GUI threads. All background daemon threads communicate with the UI thread exclusively via `SchedulerBridge(QObject)` signals and non-blocking `QTimer` instances:

```
+---------------------------------------------------------------------------------------+
|                   PySide6 Main GUI Thread (TimerRendezVousWidget / MainApp)           |
|  - refresh_timer (QTimer, 1000ms): updates QPainter Ring, Active Queue, Activity, HUD |
|  - _scratchpad_save_timer (QTimer, 500ms single-shot): debounced scratchpad auto-save |
|  - _tray_timer (QTimer, 1000ms in MainApp): updates System Tray hover tooltip         |
+---------------------------------------------------------------------------------------+
      ^                         ^                         ^
      | itemTriggered(item)     | toggleVisibility...     | toggleVisibilityRequested()
      | wakeMissed(items)       | togglePauseRequested()  |
      | (SchedulerBridge)       | toggleHudRequested()    |
      |                         | quitRequested()         |
+--------------------+   +--------------------+   +-------------------------------------+
| ReminderScheduler  |   | TrayManager        |   | GlobalHotkeyListener                |
| (src/scheduler.py) |   | (src/tray.py)      |   | (src/hotkey_manager.py)             |
| - 500ms daemon     |   | - pystray daemon   |   | - Win32 RegisterHotKey / WM_HOTKEY  |
| - threading.Lock   |   +--------------------+   +-------------------------------------+
+--------------------+
                                | triggers on main thread -> spawns async workers:
                                v
      +-----------------------------------------------+---------------------------------+
      | SoundPlayer (src/sound.py)                    | show_toast (src/notifications.py)|
      | - Daemon thread for alarm / 2-cycle preview   | - Daemon thread for Win11toast  |
      | - winsound.Beep or winmm.dll MCI playback     |   or hidden PowerShell WinRT    |
      +-----------------------------------------------+---------------------------------+
```

---

## 3. Native Windows Subsystems

### 3.1 OS-Wide Global Hotkey (`src/hotkey_manager.py`)
- Uses `ctypes.windll.user32.RegisterHotKey` with `MOD_CONTROL | MOD_NOREPEAT` (`0x4002`) and `VK_F7` (`0x76`) inside a dedicated Win32 `GetMessageW` thread.
- **Why Win32 API first**: Unlike low-level keyboard hooks (`keyboard` package), `RegisterHotKey` works reliably across all Windows applications **without Administrator privileges** and incurs zero per-keystroke hook overhead.
- **Graceful Fallbacks**: If another process already holds the hotkey, it falls back to `keyboard.add_hotkey`, while `MainApp` also binds an in-window `QShortcut("Ctrl+F7")`. Clean shutdown posts `WM_QUIT` (`PostThreadMessageW`) and calls `UnregisterHotKey`.

### 3.2 Bottom-Right Notification Cards (`src/alarm_dialog.py`), OS Link Dispatch & Action Center (`src/notifications.py`)
- When an item fires, `_popup_alarm` does **not** force-open or focus-steal `MainApp`.
- Instead, it creates a frameless `AlarmDialog(QDialog)` (`Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool`) anchored to `QGuiApplication.primaryScreen().availableGeometry()` at the bottom-right corner above the taskbar.
- **Dynamic Height & Vertical Stacking**: Plain cards use `toast_height` (`132px`) while cards carrying an attached `note` and/or `🔗 Open Link` button use `toast_height_rich` (`162px`). Active popups register in `AlarmDialog._active_popups` and compute their Y-offset by summing `(p.height_px + 10)` across all preceding visible cards so mixed-height cards never overlap.
- **Overlay Opacity Isolation**: `AppConfig.overlay_opacity` (`60%–100%`, default `90%`) governs `FloatingMiniHUD` and `AlarmDialog` window opacity (updating live via `setWindowOpacity`), while `MainApp` (and any F7Hub host window) stays `100%` opaque.
- **OS Link & Path Dispatcher (`open_attachment_link`)**: Normalizes bare domains (`teams.microsoft.com/...` -> `https://...`), explicit URI schemes (`https://`, `mailto:`, `msteams:`), and local Windows paths (`C:\...`, `\\server\...`), launching them non-blockingly via `os.startfile` (`ShellExecuteW`) with `webbrowser.open` fallback.
- **Native Toast**: Simultaneously dispatches a Windows 10/11 Action Center toast via `win11toast` (if installed) or a zero-dependency hidden PowerShell WinRT `ToastNotificationManager` script.

### 3.3 Hardware Volume & Escalating Audio (`src/sound.py`)
- **Custom MP3/WAV**: Uses Windows Multimedia `ctypes.windll.winmm.mciSendStringW` (`open ... type mpegvideo alias AlarmMedia` and `setaudio AlarmMedia volume to <0-1000>`).
- **Synthesized Presets**: Uses `winsound.Beep` patterns (`gentle` C-Major arpeggio, `digital` double-beep, `urgent` two-tone siren).
- **Gradual Escalation**: When enabled in `AppConfig`, MCI volume ramps linearly from `25%` to `100%` of target volume over 15 seconds, while synthesized presets step speed multipliers (`0.7x` -> `1.0x` -> `1.4x` at 8s and 16s).

### 3.4 Anchored Calendar Recurrence, Cold-Start Recovery & Sleep Drift (`src/scheduler.py`)
- **Anchored Recurrence & DST Preservation (`_advance_repeat`)**: Reconstructs the true appointment datetime (`target_time + lead_time_min * 60`) and advances past `now` in a loop. `daily` and `weekly` step via `datetime.combine` to preserve local wall-clock `(hour, minute)` across DST transitions; `monthly` clamps to `calendar.monthrange(year, month)[1]` against `ScheduledItem.anchor_day` (`Jan 31 -> Feb 28/29 -> Mar 31`).
- **Cold-Start Catch-Up**: On initialization, non-paused persisted reminders with `target_time < now - 10` record a snapshot in `scheduler.missed_items` (surfaced 500ms after UI launch via `AlarmDialog`); if `_advance_repeat(it, now)` succeeds for a repeating item, its next future occurrence is retained in `scheduler.items` and persisted immediately.
- **Sleep / Hibernation Drift Detector**: `_run_loop()` compares `gap = now - last_tick` every `500ms`. If `gap > 6.0` seconds (indicating OS suspend/hibernate), any non-paused item with `target_time < now` triggers `on_wake_missed_callback` -> `SchedulerBridge.wakeMissed`.

### 3.5 Windows Boot Auto-Start (`src/startup.py`)
- Writes or removes `"<pythonw.exe>" "<run.py>" --minimized` under `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` (`TimeSpace`), preferring `pythonw.exe` inside `.venv\Scripts` so boot startup never flashes a console window.
