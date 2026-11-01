# AGENTS.md - Timer & Rendez-vous

## Overview
A lightweight desktop Python application for timers and calendar-based appointments (Rendez-vous) with audio alarms, snooze/dismiss actions, Windows system tray residency, and global hotkey triggering (`Ctrl+F7`).

## Technical Philosophy
1. **Zero Mandatory Dependencies**: Built on standard library (`tkinter`, `winsound`, `ctypes`, `threading`, `json`, `winreg`, `calendar`).
2. **Graceful Progressive Enhancement**:
   - Global hotkey: uses `keyboard` if installed, falls back to Tkinter event binding.
   - System Tray: uses `pystray` + `Pillow` if installed, falls back to window minimization if not.
   - Audio: Native Windows MCI via `ctypes.windll.winmm` handles `.mp3` and `.wav` with zero external audio packages.
   - Toast Notifications: Uses PowerShell / `win11toast` for native Windows 10/11 Action Center alerts.
3. **Threading Safety**: All UI updates from background threads must be posted via `root.after()`.
4. **Documentation Rule**: Do not duplicate architecture or user manual details here. Refer to `Docs/ARCHITECTURE.md` and `Docs/USER_GUIDE.md`.

## Features Implemented
- [x] **Slice 1**: Core scheduler, dark theme UI, preset timers (30m, 1h, 2h), custom timers with task names & repeats.
- [x] **Slice 2**: Rendez-vous calendar date/time picker, JSON persistence (`reminders.json` & `settings.json`).
- [x] **Slice 3**: Sound alarm system (`winsound.Beep` presets + Windows MCI for custom `.mp3` / `.wav`).
- [x] **Slice 4**: Alarm Dialog with Dismiss, 5m / 15m Snooze selector, and Windows Action Center toasts.
- [x] **Slice 5**: System Tray integration (`pystray`) with live dynamic hover tooltip, and global hotkey (`Ctrl+F7`).
- [x] **Slice 6**: Radial Circular Progress Ring (Tkinter Canvas) showing remaining time depletion and center bold typography.
- [x] **Slice 7**: Quick Natural Language Input parser (`"in 45m check laundry"`, `"tomorrow 3pm dentist"`, `"at 18:30 dinner"`).
- [x] **Slice 8**: Audio preview player with built-in presets (Gentle Chime, Digital Watch, Urgent Siren) and gradual escalation.
- [x] **Slice 9**: Recurring Rendez-vous (Daily, Weekly, Monthly) and RFC 5545 iCalendar (`.ics`) Import/Export.
- [x] **Slice 10**: Auto-launch on Windows startup toggle in Settings via `winreg`.
- [x] **Slice 11**: Catch-up alert for missed alarms when starting up or waking from sleep.
- [ ] **Slice 12**: ~~Pomodoro Focus Mode~~ (removed by user request).
- [x] **Slice 13**: Play / Pause / Resume controls for running countdowns directly on the Circular Ring and List.
- [x] **Slice 14**: Master Audio Volume Slider (0-100%) with true Windows MCI hardware level control and audio fade-in.
- [x] **Slice 15**: Sleep & PC Wake-up Clock Drift Detector with overdue alarm notification banner.
- [ ] **Slice 16**: ~~Enhanced System Tray Quick Actions (`🍅 25m Focus`, `☕ 5m Break`, `⏯️ Pause/Resume`)~~ — Pomodoro tray shortcuts removed; `⏯️ Pause/Resume` remains.
- [x] **Slice 17**: Interactive Dark-Mode Mini-Calendar Grid with month navigation, event dots, and Day Inspector.
- [x] **Slice 18**: Ergonomic Big-Buttons Time Picker (`+`/`–` steppers, minute chips `:00`, `:15`, `:30`, `:45`, and time presets).
- [x] **Slice 19**: Relative Date Chips (`Today`, `Tomorrow`, `This Friday`, `Next Monday`).
- [x] **Slice 20**: Early Warning Lead-Time Reminders (`5m`, `10m`, `15m` before).
- [x] **Slice 21**: Category Badges (`💼 Work`, `🩺 Health`, `📞 Call`, `🏠 Personal`, `🎉 Social`).
- [x] **Slice 22**: Activity Tab — live two-column dashboard showing All Timers and All Rendez-vous with detail cards and delete/pause actions.
- [x] **Slice 23**: Floating Mini HUD (compact draggable always-on-top multi-monitor widget with SLA urgency states and live countdown).
- [x] **Slice 24**: IT Support & Helpdesk Module (SLA presets `15m`/`30m`/`45m`/`2h`/`4h`, ticket & SLA categories, and in-app Completed History log).
