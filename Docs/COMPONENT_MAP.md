# Component Map - Timer & Rendez-vous

This document outlines each module in the project and how they interact.

```
Timer & Rendez-vous/
├── AGENTS.md                  # Project roadmap and instructions for AI agents
├── requirements.txt           # Dependencies (keyboard, pystray, pillow)
├── run.py                     # CLI launcher & --minimized startup handling
├── data/                      # Auto-created state directory
│   ├── reminders.json         # Active timers, rendez-vous, pause states, repeats
│   └── settings.json          # Preferences (sounds, volume, snooze, escalation, startup, pomodoros)
├── Docs/
│   ├── ARCHITECTURE.md        # Concurrency model, audio subsystem, storage schema
│   ├── COMPONENT_MAP.md       # Module breakdown and interactions (this file)
│   └── USER_GUIDE.md          # User documentation and shortcut reference
└── src/
    ├── __init__.py
    ├── config.py              # Dark mode palette, fonts, hotkey definition
    ├── circular_ring.py       # Radial Circular Progress Ring component with paused state
    ├── calendar_widget.py     # Interactive dark-mode mini calendar grid with day inspection
    ├── time_picker.py         # Ergonomic big-buttons time picker with steppers & presets
    ├── natural_parser.py      # Quick natural language grammar parser
    ├── startup.py             # Windows startup registry manager (winreg)
    ├── calendar_export.py     # iCalendar (.ics) RFC 5545 exporter and importer
    ├── notifications.py       # Windows 10/11 Action Center toast notifications
    ├── sound.py               # Winsound chime presets + Windows MCI player with volume slider & fade-in
    ├── storage.py             # Persistence layer for JSON state
    ├── scheduler.py           # Thread-safe scheduler with Pause/Resume and sleep drift detector
    ├── alarm_dialog.py        # Top-most alert popup (Dismiss, 5m/15m Snooze)
    ├── tray.py                # System tray icon with live hover tooltip & quick Pomodoro triggers
    └── gui.py                 # Tkinter Dark Mode interface and event wiring
```

## Module Interactions

| Module | Interacts With | Description |
|---|---|---|
| `gui.py` | `circular_ring.py`, `calendar_widget.py`, `time_picker.py`, `natural_parser.py`, `scheduler.py`, `tray.py` | Main UI orchestrating Pomodoro intervals, calendar, time picker, and smart input. |
| `calendar_widget.py` | `gui.py`, `scheduler.py` | Monthly calendar grid, date selection chips, and event day indicator dots. |
| `time_picker.py` | `gui.py` | Ergonomic hour/minute steppers, minute interval chips, and time presets. |
| `circular_ring.py` | `gui.py`, `config.py` | Renders circular canvas progress bar, handles active depletion, and displays paused state. |
| `natural_parser.py` | `gui.py` | Translates natural language queries into scheduled items. |
| `startup.py` | `gui.py` | Manages auto-start entries in `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`. |
| `calendar_export.py` | `gui.py`, `scheduler.py` | Exports and imports rendez-vous to and from `.ics` calendar files. |
| `notifications.py` | `alarm_dialog.py`, `gui.py` | Dispatches Windows Action Center native toast notifications. |
| `sound.py` | `gui.py`, `alarm_dialog.py`, `storage.py` | Audio playback engine with volume slider (0-100%) and 15-second gradual fade-in. |
| `scheduler.py` | `gui.py`, `storage.py` | Background timer loop with Pause/Resume methods and clock drift sleep detection. |
| `tray.py` | `gui.py` | System tray icon with quick Pomodoro triggers, active timer pause, and live hover tooltip. |
