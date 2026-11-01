# User Guide — TimeSpace (`Docs/USER_GUIDE.md`)

> **Canonical Scope**: End-user operational manual covering all controls, the 7 module tabs, natural-language scheduling grammar, notifications, Floating Mini HUD, and keyboard shortcuts.
> *(For technical architecture and F7Hub embedding, see [ARCHITECTURE.md](ARCHITECTURE.md). For file/state schemas, see [STATE_AND_CONFIG.md](STATE_AND_CONFIG.md).)*

---

## 1. Header & Hero Deck (Top Section)

- **Header Bar**: Displays the application title, the **`📌 HUD: ON / OFF`** toggle button, and the active global hotkey badge (`CTRL+F7`).
- **Left — ⭕ Radial Circular Progress Ring**:
  - Smoothly depletes clockwise for your active timer (or nearest upcoming Rendez-vous when no timer is active).
  - **Urgency Colors**: Indigo (`>25%` remaining) ➔ Amber (`<25%`) ➔ Crimson Red (`<10%`), with inline `⏸ PAUSED` and `🔁 Repeat` status badges.
  - **`⏯ Pause / ▶ Resume`** & **`⏹ Stop`**: Directly pause/resume or cancel the active countdown.
- **Right — ⚡ Quick Natural Schedule**:
  - Type an everyday English expression and press **`Enter`** or click **`Create ⚡`**:

| Input Category | Example Expressions | Result |
|---|---|---|
| **Countdown Timers** | `Ring in 15 min` · `Check backups in 45m` · `Remind me in 10 minutes to call John` · `Timer for 30m review` | Starts a countdown timer immediately |
| **Same / Next Day RDV** | `RDV at 4PM` · `Call Linda at 7:15 tomorrow morning` · `at 18:30 dinner` · `at 8 tonight backup check` | Schedules a calendar Rendez-vous (auto-advances to tomorrow if today's time has passed) |
| **Relative Days / Weeks** | `Call Sam in 2 days` · `Call Sam in 2 days at 3pm` · `Follow up in 1 week at 10am` | Schedules a Rendez-vous `N` days/weeks ahead (defaults to `12:00` if no time specified) |
| **Next Weekday RDV** | `Dentist next Friday` · `Dentist next Friday at 14:00` · `Meeting on Wednesday at 3pm` | Schedules a Rendez-vous on the upcoming target weekday |

---

## 2. The 7 Module Tabs

### Tab 1 — `1. Timers ⏳` (Daily Task & Reminder Timer)
- **⚡ Quick Start Presets**: One-click buttons for **`15 Minutes`**, **`30 Minutes`**, **`1 Hour`**, and **`2 Hours`**.
  - *Tip*: Any text entered into **What to do**, **Client / Ticket #**, or **Link / Note** is automatically attached when you click a preset!
- **⏱️ Daily Task & Reminder Timer**:
  - **What to do**: Reminder description (e.g., `Check server backup`, `Call back`, `Send invoice`).
  - **Client / Ticket #** *(Optional)*: Quick reference field for a client name or ticket number (e.g., `Acme Corp` or `#4821`). Automatically formats the reminder as `[Acme Corp] Check server backup` and tags it with `🎫 Ticket`.
  - **Link / Note** *(Optional)*: Side-by-side compact inputs to attach a **Link / URL / File Path** (web URLs, bare domains like `teams.microsoft.com/...`, `mailto:`, or local Windows files/folders) and a **Short Note**.
  - **Countdown & Repeat**: Set `h`, `min`, `sec`, optionally check **Repeat automatically**, and click **`Start Timer ▶`** (or press **`Enter`** in any text box).

### Tab 2 — `2. RDV 📅` (Calendar & Appointments)
- **📅 Calendar (Left Column)**:
  - Navigate months with **`◀`** / **`▶`** or jump instantly with **`Today`**, **`Tmrw`**, **`Fri`**, and **`Mon`**.
  - Dates with scheduled appointments display a dot (`•`); clicking any date previews its events in the Day Agenda bar below the grid.
- **⏰ Appointment Details (Right Column)**:
  - **Event / Client**: Subject, client name, or ticket reference.
  - **Time Picker**: Adjust hours/minutes with **`+`** / **`−`** steppers, minute chips (`:00`, `:15`, `:30`, `:45`), or presets (`09:00`, `12:00`, `15:00`, `18:00`).
  - **Link & Short Note** *(Optional)*: Attach a meeting link (Teams/Zoom/Meet), ticket URL, or local file/folder path plus a brief note—ready to launch in 1 click when the popup fires.
  - **Category, Alert & Repeat**: Tag with a category (`📌 General`, `💼 Work`, `📞 Callback`, `🔄 Follow-up`, `🎫 Ticket`, `🩺 Health`, `🏠 Personal`), set an early lead-time (`At time (0m)`, `5m`, `10m`, or `15m before`), and optionally repeat (`None`, `Daily`, `Weekly`, `Monthly`—monthly RDVs anchor to your original day-of-month such as `Jan 31 → Feb 28/29 → Mar 31` and auto-advance if missed while closed).
  - **`.ics` Import / Export**: Sync appointments (including `URL` and `DESCRIPTION` notes, plus embedded Teams/Zoom links from calendar invites) with Outlook, Google Calendar, or Apple Calendar.

### Tab 3 — `3. Activity 📋` (Live Dual-Column Dashboard)
- Full-height side-by-side lists for **`⏳ All Timers`** and **`📅 All Rendez-vous`** (~15+ visible rows per column).
- Click any item to inspect its fire timestamp, category, lead-time, repeat rule, note, and link; act immediately with **`⏯ Pause/Resume`**, **`🗑️ Delete`**, or the contextual **`🔗 Open Link`** button (shown whenever the selected item has a link).

### Tab 4 — `4. Scratchpad 📝` (Rich-Text Time Notes & Clickable Links)
- Monospace rich-text notepad (`Consolas`) for quick time notes, call logs, client references, or web links, auto-saved continuously (`500ms` debounce) with full formatting persistence (`data/scratchpad.json`).
- **`𝐁 Bold (Ctrl+B)`**: Toggles bold formatting on highlighted text (or for upcoming typed text when nothing is selected).
- **`🎨 Color`**: Opens a quick color palette (`Default White`, `Indigo Accent`, `Sky Cyan`, `Emerald Green`, `Amber Gold`, `Coral Orange`, `Crimson Red`, `Violet Purple`) plus **`🎨 Custom Color...`** to apply any color to highlighted text.
- **Detectable & Clickable Web Links**: Any web link (`https://...`, `http://...`, `www....`, or bare domains like `github.com/...`) is automatically underlined and highlighted in real time. Hovering over a link switches the cursor to a pointing hand (`👆`), and left-clicking it opens the URL directly in your default web browser (while clicking and dragging still lets you highlight/select the link text normally).
- **`🕒 +Timestamp (Ctrl+T)`**: Inserts `[YYYY-MM-DD HH:MM:SS] ` at the cursor.
- **`📋 Copy All`** / **`🧹 Clear`**: Copy the entire scratchpad to clipboard or clear after confirmation.

### Tab 5 — `5. Go ⏱️` (Cross-Platform Diagnostics & Remediation)
- Non-blocking diagnostic and OS remediation console powered by `PySide6.QtCore.QProcess` so active timers and Rendez-vous alerts keep ticking without interruption.
- **Engine Mode Selector & `🔨 Build Binaries`**:
  - **`Compiled Binary Mode (Zero-Dependency)`**: Launches `bin/diag_windows.exe`, `bin/diag_linux`, or `bin/diag_mac_arm64`.
  - **`Go Script Mode (go run)`**: Runs `go run .` inside `go_engine/` when the Go toolchain is installed.
  - **`🔨 Build Binaries`**: One-click non-blocking cross-compilation of Windows, Linux, and macOS binaries via `go_engine/build_all.ps1` (`CGO_ENABLED=0`), streaming progress into the console and refreshing the engine badge automatically.
  - **Automatic Fallback**: If neither the compiled binary nor `go` on `PATH` is present yet, automatically runs the built-in asynchronous `QProcess` fallback worker so all 8 actions work immediately out of the box.
- **Target Host/IP, Quick Target Presets & CLI Args**: Enter an IP, hostname, or URL (default `1.1.1.1`), pick instantly from **`⚡ Presets...`** (`Cloudflare 1.1.1.1`, `Google 8.8.8.8`, `github.com`, `google.com`, `microsoft.com`, `127.0.0.1`), and optionally pass custom CLI flags.
- **8 One-Click Diagnostic & Remediation Actions (`2×4` Grid)**:
  1. **`🌐 Ping & TCP`** (`--action=ping`): DNS lookup + TCP latency probe across ports `443`, `80`, and `53`.
  2. **`🔍 Port Scan`** (`--action=port-scan`): Concurrent scan of ports `22, 53, 80, 443, 3389, 8080` with 2-second timeout.
  3. **`🔒 TLS Cert`** (`--action=tls-check`): Inspects X.509 certificate subject, issuer, SANs, and expiration countdown.
  4. **`🌍 HTTP/S Probe`** (`--action=http-check`): Measures HTTP/HTTPS status code (`200 OK`, etc.), response latency, redirect destination, and `Server` header.
  5. **`🧭 DNS Lookup`** (`--action=dns-lookup`): Queries `A`, `AAAA`, `CNAME`, `MX`, `NS`, and `TXT` records for the target domain/IP.
  6. **`🧹 Flush DNS`** (`--action=flush-dns`): Executes OS DNS cache flush (`ipconfig /flushdns` on Windows, `resolvectl flush-caches` on Linux, `dscacheutil -flushcache` on macOS).
  7. **`🖧 Net Triage`** (`--action=net-status`): Displays active interface IP/gateway/DNS configuration.
  8. **`📊 Sys & Sockets`** (`--action=sys-info`): Summarizes active network sockets and system statistics.
- **External Interactive Go CLI & Privilege Elevation (`⚡ Run as Admin / sudo` + `🚀 Launch Interactive Go CLI`)**:
  - Click **`🚀 Launch Interactive Go CLI (External Terminal)`** to spawn a standalone terminal session featuring a **TimeSpace Purple (`#6366f1`)** main menu (`[1]`–`[7]`, including **`[7] Automated Network Triage Playbook`**) with `[ADMIN / ROOT]` vs `[STANDARD USER]` token detection.
  - **Multi-Select, Ranges & Screen Clear**: Enter multiple option numbers (`1,3,4`), number ranges (`1-4, 6`), `target <host>` to switch targets dynamically, `clr` (or `clear`/`cls`) to clear the terminal screen, or `exit` to close.
  - Check **`⚡ Run as Admin / sudo (Elevated Fixes)`** before launching to trigger native OS privilege elevation (Win32 `ShellExecuteW("runas")` Windows UAC prompt with UTF-16LE `-EncodedCommand`, `sudo` on Linux, or `osascript` on macOS).
- **Color-Coded Console, Clipboard & Scratchpad Bridge**:
  - Automatically hides the bottom `Active Reminders Queue` while on **`5. Go ⏱️`** so the console expands to full vertical height.
  - Real-time syntax highlighting (`GoConsoleHighlighter`) colors `[PASS]` / `OPEN` / `200 OK` in emerald green, `[FAIL]` / `[ERROR]` / `UNREACHABLE` in crimson red, `CLOSED/FILTERED` / `[WARN]` / `ELEVATED` in amber, and action banners in sky cyan, while completed runs log automatically into **`6. History 📜`**.
  - Click **`📋 Copy`** to copy console output to the clipboard, or click **`📝 +Scratchpad`** to append a timestamped diagnostic report directly into **`4. Scratchpad 📝`** for ticket/call documentation.

### Tab 6 — `6. History 📜` (Completed & Triggered Log)
- Dedicated full-height audit log recording every **`Triggered`**, **`Dismissed`**, **`Opened Link`**, **`Snoozed`**, and **`Diag PASS / FAIL`** entry (up to the latest 100 entries).
- **`🔗 Open Link`**: Appears automatically in the header when selecting a history entry with an attached URL/path.
- **`📋 Copy Selected`**: Copies `[timestamp] Name (Status)` (plus any attached note and link) to the clipboard in one click.
- **`🧹 Clear History`**: Empties the persisted history log.

### Tab 7 — `7. Settings ⚙️` (Audio, Opacity & System Preferences)
- **Alarm Tone & `🔊 Preview`**: Audition built-in synthesized patterns (*Gentle Chime*, *Digital Watch*, *Urgent Siren*) or **`Browse...`** for a custom `.mp3` / `.wav` file.
- **Master Volume (`0–100%`)**: Hardware-scaled alarm loudness.
- **Popup & HUD Opacity (`60–100%`, default `90%`)**: Controls transparency of the **Floating Mini HUD** and **Bottom-Right Alarm Popups** with live preview while dragging (keeping the Main Window `100%` solid).
- **System Options**: Toggle **Gradual volume escalation**, **Launch at Windows boot** (starts minimized in tray), choose your **Default Snooze** (`5`, `10`, `15`, or `30` min), and click **`Save Settings ✓`**.

---

## 3. Persistent Queue, Notifications, HUD & Shortcuts

- **Active Reminders Queue (Bottom Panel)**: Always visible beneath Tabs 1–4 and 6–7 (and automatically hidden on **`5. Go ⏱️`** to maximize console height), displaying 7–9+ visible rows. Items highlight **Amber** under 5 minutes and **Crimson Red** under 1 minute, and display `🔗` / `📝` indicators (with hover tooltips) when links or notes are attached.
- **Bottom-Right Alarm Popup**: Triggers as a compact frameless card above the Windows system tray (stacking vertically if multiple alarms fire) alongside a Windows Action Center toast—without forcing the main window open over your work. Displays any attached note and lets you click **`🔗 Open Link`** (which opens the URL/file, stops alarm audio, logs `Opened Link`, and dismisses the popup), **`✓ Dismiss`**, or **`💤 Snooze`** (`5m`/`10m`/`15m`/`30m`, preserving notes & links).
- **Missed & Sleep-Wake Alerts**: Automatically notifies you on startup or PC wake-up if reminders elapsed while the app was closed or the PC was asleep.
- **📌 Floating Mini HUD**: Draggable always-on-top desktop pill showing the nearest countdown with urgency border colors and quick pause (`⏯`). Double-click the HUD to bring the main window forward.

| Shortcut / Action | Behavior |
|---|---|
| **`Ctrl + F7`** *(Global)* | Toggle main window visibility from any application in Windows |
| **`Ctrl + T`** *(Scratchpad)* | Insert `[YYYY-MM-DD HH:MM:SS] ` timestamp at cursor |
| **`Ctrl + B`** *(Scratchpad)* | Toggle **Bold** on highlighted text |
| **Left-Click URL** *(Scratchpad)* | Open any detected web link (`https://`, `www.`, or domain) in default browser |
| **`Enter`** *(Inputs)* | Submit Quick Natural Schedule or Daily Task Timer form |
| **Window `[X]` Button** | Hide window to Windows System Tray (timers keep running) |
| **Tray Icon Hover / Right-Click** | View live next-reminder countdown tooltip; Pause/Resume, Toggle HUD, or Exit |
