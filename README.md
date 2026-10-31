# Timer & Rendez-vous ⏰

A lightweight, distraction-free desktop application for countdown timers and calendar-based appointments (Rendez-vous), featuring natural language scheduling, audio alarms, Pomodoro focus cycles, Windows system tray residency, and global hotkey control.

![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-blue?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-informational?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Dependencies](https://img.shields.io/badge/Dependencies-Standard%20Library%20First-purple?style=flat-square)

---

## ✨ Features at a Glance

- **⚡ Quick Natural Language Input**:
  Schedule timers and appointments by typing in natural English:
  - `"Ring in 15 min"` ➔ 15-minute countdown.
  - `"RDV at 4PM"` ➔ Calendar appointment for 16:00 today (or tomorrow if past).
  - `"Call Linda at 7:15 tomorrow morning"` ➔ Scheduled appointment for tomorrow at 07:15.
  - `"Check oven in 25 mins"` ➔ 25-minute timer named *"Check oven"*.
  - `"Remind me in 10 minutes to call John"` ➔ 10-minute timer named *"call John"*.

- **⭕ Radial Circular Progress Ring**:
  - Live animated Tkinter `Canvas` ring depleting clockwise as remaining time counts down.
  - Dynamic color transitions: **Indigo** (>25%) ➔ **Amber** (<25%) ➔ **Red** (<10%).
  - Integrated **`⏯️ Pause`** and **`⏹️ Stop`** controls directly beneath the ring.

- **🍅 Pomodoro Technique Mode**:
  - One-click triggers for **25m Focus**, **5m Short Break**, and **15m Long Break**.
  - Daily session streak counter (`Completed today: 🍅 x 3`).
  - Auto-prompts for a 5-minute break upon focus completion.

- **🔊 Multi-Pattern Sound Alarm & Windows MCI**:
  - **Zero-Dependency Presets**: Gentle Chime (C-Major arpeggio), Digital Watch (double chirp), Urgent Siren (two-tone).
  - **Custom Media Playback**: Native Windows Multimedia API (`winmm.dll`) plays `.mp3` and `.wav` with **zero external C-library audio dependencies**.
  - **Master Volume Slider (0-100%)**: True hardware-level volume control.
  - **Gradual Fade-In Escalation**: Starts soft and gentle, ramping up intensity and volume over 15 seconds.
  - **Audio Preview Button**: Test sound and volume directly in Settings.

- **🪟 Windows System Integration & System Tray**:
  - **Global Hotkey (`Ctrl + F7`)**: Instantly toggle window visibility from anywhere in Windows.
  - **System Tray Residency (`pystray`)**: Minimizing or clicking `[X]` hides to the notification area with a live countdown tooltip (e.g., `Next: check laundry (12m 45s)`).
  - **Tray Right-Click Menu**: Quick access to start Pomodoro sessions, trigger breaks, pause/resume, or exit.
  - **Auto-Launch on Boot**: Toggle *"Launch at Windows startup (minimized)"* via standard library `winreg`.
  - **Action Center Native Toasts**: Delivers Windows 10/11 banner notifications.
  - **Clock Drift & Sleep Wake-up Detector**: Warns you if the PC was asleep when an appointment was scheduled.

- **📅 Rendez-vous & Interactive Calendar Grid**:
  - **Interactive Dark Calendar Grid**: Monthly view with `◀` / `▶` navigation and event dots (`•`) on scheduled days.
  - **Day Inspector**: Click any calendar day to inspect and preview all events scheduled for that date.
  - **Quick Relative Date Chips**: One-click shortcuts for `[ Today ]`, `[ Tomorrow ]`, `[ This Friday ]`, and `[ Next Monday ]`.
  - **Ergonomic Big-Buttons Time Picker**: Bold readout `[ 14 ] : [ 30 ]` with large `+` / `–` steppers, quick minute chips (`:00`, `:15`, `:30`, `:45`), and presets (`09:00`, `12:00`, `15:00`, `18:00`).
  - **Early Warning Lead-Time**: Get notified `5m before`, `10m before`, or `15m before` so you are never late.
  - **Category Badges**: Categorize events with `💼 Work`, `🩺 Health`, `📞 Call`, `🏠 Personal`, `🎉 Social`.
  - **RFC 5545 iCalendar (`.ics`)**: Recurring rules (Daily, Weekly, Monthly) with one-click Import & Export.

---

## 🚀 Quick Start

### 1. Requirements
- Python 3.10 or higher on Windows.
- Standard library modules handle core functionality (`tkinter`, `winsound`, `ctypes`, `threading`, `json`, `winreg`).

Optional enhancement packages:
```powershell
pip install -r requirements.txt
```
*(Includes `keyboard` for global hotkey hooks, and `pystray` + `pillow` for system tray residency).*

### 2. Launch
```powershell
python run.py
```

---

## ⌨️ Global Shortcuts & Controls

| Shortcut / Control | Action |
|---|---|
| **`Ctrl + F7`** | Show window / Hide to system tray from anywhere in Windows |
| **`[X]` Close Button** | Minimizes to Windows System Tray (keeps timers running) |
| **Enter (Smart Input)** | Parses and schedules natural language query |
| **Tray Hover** | Live tooltip showing the nearest upcoming countdown |
| **Tray Right-Click** | Context menu with 🍅 Pomodoro, ☕ Break, and Pause controls |

---

## 🗣️ Natural Language Input Cheatsheet

| Query | What It Does |
|---|---|
| `Ring in 15 min` | Starts a 15-minute countdown |
| `in 45m check laundry` | 45-minute timer named *"check laundry"* |
| `Check pasta in 8 mins` | 8-minute timer named *"Check pasta"* |
| `Timer for 30m meditation` | 30-minute timer named *"meditation"* |
| `RDV at 4PM` | Rendez-vous for 16:00 |
| `Call Linda at 7:15 tomorrow morning` | Rendez-vous for tomorrow at 07:15 |
| `Meeting tomorrow at 3:30pm with Bob` | Rendez-vous for tomorrow at 15:30 named *"Meeting with Bob"* |
| `at 18:30 dinner` | Rendez-vous for 18:30 today (or tomorrow if 18:30 has passed) |
| `at 8 tonight movie` | Rendez-vous for tonight at 20:00 named *"movie"* |

---

## 📂 Project Structure

```
Timer & Rendez-vous/
├── README.md                  # This file (Project overview & guide)
├── AGENTS.md                  # Development roadmap and instructions for AI agents
├── requirements.txt           # Dependencies (keyboard, pystray, pillow)
├── run.py                     # Entry point & CLI launcher
├── data/                      # Auto-created persistence directory
│   ├── reminders.json         # Active timers, rendez-vous, pause states, repeats
│   └── settings.json          # Preferences (sounds, volume, snooze, escalation, startup)
├── Docs/
│   ├── ARCHITECTURE.md        # Technical specs, threading model & MCI audio engine
│   ├── COMPONENT_MAP.md       # Modules breakdown and interactions
│   └── USER_GUIDE.md          # User manual, hotkey reference, and features
└── src/
    ├── __init__.py
    ├── config.py              # Theme tokens (#18181b), typography, hotkey constants
    ├── circular_ring.py       # Radial Circular Progress Ring (Tkinter Canvas)
    ├── natural_parser.py      # Expanded natural language grammar parser
    ├── startup.py             # Windows startup registry manager (winreg)
    ├── calendar_export.py     # iCalendar (.ics) RFC 5545 exporter and importer
    ├── notifications.py       # Windows 10/11 Action Center toast notifications
    ├── sound.py               # Sound synthesizer + Windows MCI player with volume slider & fade-in
    ├── storage.py             # JSON persistence layer for state & settings
    ├── scheduler.py           # Thread-safe scheduler with Pause/Resume & sleep drift detection
    ├── alarm_dialog.py        # Top-most alert popup (Dismiss, 5m/15m Snooze)
    ├── tray.py                # System tray icon with live hover tooltip & quick Pomodoro triggers
    └── gui.py                 # Tkinter Dark Mode interface and event orchestration
```

---

## 📖 Detailed Documentation

For in-depth technical specifications, refer to the documentation inside `Docs/`:
- **[Docs/ARCHITECTURE.md](Docs/ARCHITECTURE.md)**: Concurrency model, clock drift detection algorithm, and Windows MCI audio subsystem.
- **[Docs/USER_GUIDE.md](Docs/USER_GUIDE.md)**: Full guide to Pomodoro workflow, calendar import/export, and audio settings.
- **[Docs/COMPONENT_MAP.md](Docs/COMPONENT_MAP.md)**: Comprehensive mapping of modules and component relationships.
- **[AGENTS.md](AGENTS.md)**: Roadmap tracking and engineering rules for AI Coding Agents.

---

## 📄 License
This project is open-source and released under the [MIT License](LICENSE).

