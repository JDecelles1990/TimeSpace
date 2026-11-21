# User Guide — TimeSpace (`Docs/USER_GUIDE.md`)

> **Canonical Scope**: End-user operational manual covering all controls, the 7 module tabs, natural-language scheduling grammar, notifications, Floating Mini HUD, and keyboard shortcuts.
> *(For technical architecture and F7Hub embedding, see [ARCHITECTURE.md](ARCHITECTURE.md). For file/state schemas, see [STATE_AND_CONFIG.md](STATE_AND_CONFIG.md).)*

---

## 1. Header & Fixed-Height Top Deck

- **Uniform Tabs Bar Placement**: The top deck stays at a fixed height above the `1`–`7` tabs bar across every section so the tabs bar never shifts up or down when switching tabs:
  - **Tabs `1`, `2`, `3`, `6`**: Displays the **Hero Deck** (Radial Countdown Ring + Quick Natural Schedule).
  - **Tab `4. Scratchpad 📝`**: Displays **`📝 Scratchpad 1 (Upper)`** above the tabs bar and **`📝 Scratchpad 2 (Lower)`** below.
  - **Tab `5. Go ⏱️`**: Displays the compact **`⚡ Go Diagnostic & Remediation Engine`** controls and action buttons above the tabs bar.
  - **Tab `7. Settings ⚙️`**: Displays the compact **`🔊 Sound, Transparency & System Preferences`** controls above the tabs bar.
- **Cyber-Aurora Neon Glass Design & Animated Transitions**:
  - **Dynamic Aurora Glass Backdrop & Mouse Spotlight**: The entire TimeSpace canvas glows with a gently breathing Cyber-Aurora gradient backdrop seen through frosted translucent glass panels, shifting with active urgency/Meeting status and smoothly illuminating beneath your cursor with an interactive aurora spotlight and glass shimmer sweep on window enter.
  - **Shiny 3D Buttons & Role-Matched Halos**: All buttons feature glossy top-shine gradients at rest and smoothly animate role-matched outer neon glows on hover and specular click bursts (`Violet/Cyan` standard, `Cyan` primary actions, `Emerald` save/open actions, `Rose-Magenta` stop/delete actions, `Gold` Admin CLI).
  - **Glowing Inputs, Bars & Lists**: Text fields, spinboxes, dropdowns, and Scratchpad/Console editors glow violet on hover and electric cyan while focused; tabs, iridescent sliders, progress bars, scrollbars, splitter handles, and active list rows all illuminate with animated gradients.
  - **Radial Ring Halo & Tab Shimmer**: The countdown ring glows with a multi-stop neon gradient and specular leading tip orb, and switching tabs plays a smooth ~150ms glass shimmer fade (`TabTransitionOverlay`).
  - **Animated Neon Glass Tooltips**: Hovering over buttons, reminder/activity list items, tabs, or controls reveals a translucent Cyber-Aurora tooltip card with crisp specular text, role-matched neon outer glow, iridescent border, glowing left accent bar, subtle light shimmer sweep, and smooth fade/glide-in & fade-out transitions.
- **Header Bar**: Displays the application title, keyboard shortcut hint (`Ctrl+F8 | Keys 1-7`), the **`🔔 Normal` / `🤫 Meeting` Mode button** (left-click to toggle, right-click for timed mutes, `Ctrl+Shift+M`), the **App Window Opacity Slider (`🔆 45%–100%`, default `90%`)** immediately on the left of the **`📌 HUD`** button, and the **`📌 HUD`** toggle button.
- **Left — ⭕ Radial Circular Progress Ring** *(visible above tabs bar on Tabs 1, 2, 3, and 6)*:
  - Smoothly depletes clockwise for your active timer (or nearest upcoming Rendez-vous when no timer is active).
  - **Urgency Colors**: Neon Violet ➔ Cyan ➔ Emerald (`>25%` remaining) ➔ Gold/Amber (`<25%`) ➔ Rose/Crimson (`<10%`) with glowing leading tip orb and inline `⏸ PAUSED` / `🔁 Repeat` badges.
  - **`⏸️` / `▶️`** & **`⏹️`**: Compact emoji controls to directly pause/resume or cancel the active countdown.
- **Right — ⚡ Quick Natural Schedule**:
  - Type an everyday English expression and press **`Enter`** or click **`⚡`**:

| Input Category | Example Expressions | Result |
|---|---|---|
| **Countdown Timers** | `Ring in 15 min` · `Check backups in 45m` · `Remind me in half an hour to check backup` · `Timer for 30m review` | Starts a countdown timer immediately (supports `in an hour`, `in a minute`, `in half an hour`) |
| **Same / Next Day RDV** | `RDV at 4PM` · `Set an alarm at 7am to stretch` · `Call Linda at 7:15 tomorrow morning` · `at noon lunch` · `at 18:30 dinner` | Schedules a calendar Rendez-vous (auto-advances to tomorrow if today's time has passed) |
| **Relative Days / Weeks** | `Call Sam in 2 days` · `Call Sam in 2 days at 3pm` · `RDV in 5 days and 3 hours` · `RDV in 1 week, 2 days and 30 mins` · `Call client day after tomorrow at 14h30` · `Follow up in 1 week at 10am` | Schedules a Rendez-vous `N` days/weeks ahead (supports compound sub-day offsets like `and 3 hours`, or defaults to `12:00` if no time specified) |
| **Weekday + Ordinal Day** | `Set an alarm for Friday the 13th at 2:15 PM` · `Set an alarm for Friday the 13th at2:15 PM` · `Meeting on Monday the 16th at 10am` | Finds the next calendar date matching both the target weekday and ordinal day of the month |
| **Ordinal Day / Calendar Dates** | `Set an alarm for the 13th at 2:15 PM` · `Pay rent on the 1st at 9am` · `Dentist on Nov 20th at 2:15 PM` · `13th of December at 10am` · `Dentist on 2026-12-05 at 14:00` · `Call client on 11/20 at 3pm` | Resolves exact ISO (`YYYY-MM-DD`), numeric (`MM/DD`), Month+Day, or next upcoming ordinal day of the month |
| **Weekday Phrases** | `Dentist next Friday at 14:00` · `Set an alarm for Friday at 2:15 PM` · `this Friday at 3pm` · `Meeting on Wednesday at 3pm` | Schedules a Rendez-vous on the upcoming target weekday (supports conversational prefixes and `at2:15 PM` / `14h30` time notation) |

---

## 2. The 7 Module Tabs

### Tab 1 — `1. Timers ⏳` (Daily Task & Reminder Timer)
- **⚡ Quick Start Presets & Inline Edit (`✏️`)**: Compact one-click buttons for **`15m`**, **`30m`**, **`1h`**, and **`2h`**, plus **`✏️`** to immediately edit the active or last-started timer in place.
  - *Tip*: Any text entered into **Task**, **Ref**, or **🔗 / 📝** is automatically attached when you click a preset!
- **⏱️ Daily Task & Reminder Timer**:
  - **Task (`What to do`)**: Reminder description (e.g., `Check server backup`, `Call back`, `Send invoice`).
  - **Ref (`Client / Ticket #`)** *(Optional)*: Quick reference field for a client name or ticket number (e.g., `Acme Corp` or `#4821`). Automatically formats the reminder as `[Acme Corp] Check server backup` and tags it with `🎫 Ticket`.
  - **🔗 Link / 📝 Note** *(Optional)*: Side-by-side compact inputs to attach a **Link / URL / File Path** and a **Short Note**.
  - **Countdown, Repeat & Inline Update**: Set `h`, `m`, `s`, optionally check **`🔁`** (Repeat), and click **`▶️`** (or press **`Enter`**). Double-clicking any active timer (or clicking **`✏️`**) loads its live details into the form and switches **`▶️`** to **`💾`** (with **`✖`** to cancel) so you can update an active timer without recreating it.

### Tab 2 — `2. RDV 📅` (Calendar & Appointments)
- **📅 Calendar (Left Column)**:
  - Navigate months with **`◀`** / **`▶`** or jump instantly with **`Today`**, **`Tmrw`**, **`Fri`**, and **`Mon`**.
  - Dates with scheduled appointments display a dot (`•`); clicking any date previews its events in the Day Agenda bar below the grid.
- **⏰ Appointment Details (Right Column — Responsive Layout)**:
  - **Event**: Subject, client name, or ticket reference.
  - **Time Picker**: Responsive grid with **`−1h`** / **`+1h`** steppers, minute chips (`:00`, `:15`, `:30`, `:45`), and hour presets (`09:00`, `12:00`, `14:00`, `17:00`, `18:00`) that never overlap when the window is resized down to `480×540`.
  - **🔗 Link & 📝 Short Note** *(Optional)*: Attach a meeting link (Teams/Zoom/Meet), ticket URL, or local file/folder path plus a brief note.
  - **Cat, Alert & Repeat**: Tag with a category, set an early lead-time (`At time (0m)`, `5m`, `10m`, `15m`, `45m`, `1 hour`, `2 hours`, or `1 day before`), and optionally repeat (`None`, `Daily`, `Weekly`, `Monthly`).
  - **Compact Actions & Inline RDV Editing**: Click **`📤 .ics`** (Export), **`📥 .ics`** (Import), **`✏️`** (Edit active RDV), or **`➕ RDV`** (switches to **`💾 RDV`** when editing an existing appointment).

### Tab 3 — `3. Activity 📋` (Live Dual-Column Dashboard)
- Automatically hides the bottom `Active Reminders Queue` so **`⏳ All Timers`** and **`📅 All Rendez-vous`** expand to 100% of the vertical space.
- Double-click any timer or RDV (or click **`✏️`**) to jump straight into inline edit mode, or use **`⏸️`**, **`🗑️`**, and **`🔗`**.

### Tab 4 — `4. Scratchpad 📝` (Upper Over-Tabs & Lower Rich-Text Scratchpads + Power Tools)
- Hides the bottom `Active Reminders Queue` and splits the two rich-text scratchpads across the fixed tabs bar:
  1. **`📝 Scratchpad 1 (Upper)`** *(above the tabs bar)*: Pin priority notes, commands, client numbers, or URLs in the top deck.
  2. **`📝 Scratchpad 2 (Lower)`** *(below the tabs bar)*: Expands full-height for ongoing time notes, call logs, or diagnostic snippets.
- Each Scratchpad (including the 3rd Scratchpad in `5. Go ⏱️`) features a compact power toolbar:
  - **`𝐁`** (`Ctrl+B`): Toggle Bold on highlighted text.
  - **`🎨`**: Apply foreground colors from the 8-color dark palette or custom color picker.
  - **`🕒`** (`Ctrl+T`): Insert `[YYYY-MM-DD HH:MM:SS] ` timestamp at cursor.
  - **`🔍`** (`Ctrl+F`): Toggle the inline **Find Bar** (`Find in scratchpad...` + **`▲`** / **`▼`** wrap-around match navigation + **`✖`** or `Escape` to close).
  - **`⏰`** *(or Right-Click ➔ `⏰ Schedule Highlighted / Line as Timer or RDV...`)*: Instantly schedule the highlighted text (or current line) as a **`15m`**, **`30m`**, **`1h`**, or **`2h`** timer, auto-parse natural-language expressions (`Call John in 20m`, `RDV tomorrow at 14:00`), or send the text directly to Tab 1 (`1. Timers ⏳`) or Tab 2 (`2. RDV 📅`). Any URL inside the selection is automatically extracted into the reminder's clickable **`🔗`** attachment field!
  - **`💾`** (`Ctrl+S`): 1-click export of the Scratchpad pane's notes directly to `C:\Temp\TimeSpace_Scratchpad_<name>_<timestamp>.md`.
  - **`📋`** (Copy) & **`🧹`** (Clear), plus real-time detectable & clickable web links (`https://`, `http://`, `www.`).

### Tab 5 — `5. Go ⏱️` (Cross-Platform Diagnostics & Remediation)
- Non-blocking diagnostic and OS remediation console powered by `PySide6.QtCore.QProcess` so active timers and Rendez-vous alerts keep ticking without interruption.
- **Engine Mode Selector & `🔨 Build Binaries`**:
  - **`Compiled Binary Mode (Zero-Dependency)`**: Launches `bin/diag_windows.exe`, `bin/diag_linux`, or `bin/diag_mac_arm64`.
  - **`Go Script Mode (go run)`**: Runs `go run .` inside `go_engine/` when the Go toolchain is installed.
  - **`🔨 Build Binaries`**: One-click non-blocking cross-compilation of Windows, Linux, and macOS binaries via `go_engine/build_all.ps1` (`CGO_ENABLED=0`), streaming progress into the console and refreshing the engine badge automatically.
  - **Automatic Fallback**: If neither the compiled binary nor `go` on `PATH` is present yet, automatically runs the built-in asynchronous `QProcess` fallback worker so all 8 actions work immediately out of the box.
- **Target Host/IP, Custom Bookmarks (`⭐` / `✕`), Quick Target Presets & CLI Args**:
  - Enter an IP, hostname, or URL (default `1.1.1.1`), or pick from **`⚡ Presets...`** (user-saved **`⭐`** bookmarks appear at the top above built-in presets `Cloudflare 1.1.1.1`, `Google 8.8.8.8`, `github.com`, `google.com`, `microsoft.com`, `127.0.0.1`).
  - Click **`⭐`** to bookmark the current Target (supports optional `Label | host` syntax such as `Client VPN | 10.20.30.40` to save a friendly display label), or select a saved bookmark and click **`✕`** to remove it. Bookmarks persist in `data/settings.json` and sync with the Interactive Go CLI (`bm` command).
- **8 One-Click Diagnostic & Remediation Actions (`2×4` Grid)**:
  1. **`🌐 Ping & TCP`** (`--action=ping`): DNS lookup + TCP latency probe across ports `443`, `80`, and `53`.
  2. **`🔍 Port Scan`** (`--action=port-scan`): Concurrent scan of ports `22, 53, 80, 443, 3389, 8080` with 2-second timeout.
  3. **`🔒 TLS Cert`** (`--action=tls-check`): Inspects X.509 certificate subject, issuer, SANs, and expiration countdown.
  4. **`🌍 HTTP/S Probe`** (`--action=http-check`): Measures HTTP/HTTPS status code (`200 OK`, etc.), response latency, redirect destination, and `Server` header.
  5. **`🧭 DNS Lookup`** (`--action=dns-lookup`): Queries `A`, `AAAA`, `CNAME`, `MX`, `NS`, and `TXT` records for the target domain/IP.
  6. **`🧹 Flush DNS`** (`--action=flush-dns`): Executes OS DNS cache flush (`ipconfig /flushdns` on Windows, `resolvectl flush-caches` on Linux, `dscacheutil -flushcache` on macOS).
  7. **`🖧 Net Triage`** (`--action=net-status`): Displays active interface IP/gateway/DNS configuration.
  8. **`📊 Sys & Sockets`** (`--action=sys-info`): Summarizes active network sockets and system statistics.
- **Two Dedicated Interactive Go CLI Launch Buttons (`🛡️ Admin Go CLI` & `🚀 Standard Go CLI`)**:
  - **`🚀 Standard Go CLI` (`--cli-mode=user`, Prompt: `TimeSpace-User> `)**:
    - Directly launches the non-elevated user diagnostic REPL in a **TimeSpace Purple (`#6366f1`)** menu (`[1] Ping & TCP`, `[2] Port Scan`, `[3] TLS Cert`, `[4] HTTP/S Probe`, `[5] DNS Lookup`, `[6] IP Config`, `[7] Socket & Uptime`, `[8] Standard User Playbook`).
  - **`🛡️ Admin Go CLI` (`--cli-mode=admin`, Prompt: `TimeSpace-Admin⚡> `)**:
    - Directly launches the elevated Administrator / `sudo` remediation & deep audit REPL (`[1] Flush DNS`, `[2] Clear ARP/NetBIOS`, `[3] Restart DNS Client`, `[4] Reset Winsock`, `[5] Reset TCP/IP Stack`, `[6] Elevated Port & Process Owner Audit`, `[7] Firewall Profiles Audit`, `[8] Routing Table Audit`, `[9] Automated Admin Playbook`).
  - **Shared REPL Commands (`Multi-Select`, `Ranges`, `bm`, `copy`, `save`, `clr`, `target`, `exit`)**: Both CLIs support multiple numbers (`1,3,4`), number ranges (`1-4, 6`), `target <host>`, `bm` (`bm` to list saved bookmarks, `bm <n>` to switch target to bookmark `#n`, `bm add [label]` to bookmark current target, `bm del <n>` to delete), `copy` (or `cp`) to clipboard, `save [md|txt|json]` (or `export`) into `C:\Temp`, `clr`, and `exit`.
- **Live Console + 3rd Rich-Text Go Scratchpad**:
  - Hosts the compact **Engine, Target/Bookmarks, `2×4` Action Grid, and Dual CLI Launchers** in the fixed top deck above the tabs bar, and hides the bottom `Active Reminders Queue` so the Live Console + Go Scratchpad fill the tab area below.
  - Beneath the live color-highlighted console (`📋` Copy, `📝` +Scratchpad, `💾` Export, `⏹️` Stop, `🧹` Clear), a vertical `QSplitter` hosts the **3rd Rich-Text Scratchpad** (`📝 Go Scratchpad`) with Bold (`𝐁`), Color (`🎨`), Timestamp (`🕒`), Find (`🔍` `Ctrl+F`), Schedule Selection (`⏰`), Export (`💾` `Ctrl+S`), Copy (`📋`), Clear (`🧹`), and clickable URLs.

### Tab 6 — `6. History 📜` (Completed & Triggered Log)
- Automatically hides the bottom `Active Reminders Queue` so the Completed & Triggered Reminders History list expands to full vertical height.
- Press the **`Delete`** key (or click **`🗑️`**) to remove selected individual history entries, or use **`🔗`** (Open Link), **`📋`** (Copy Selected), and **`🧹`** (Clear All History).

### Tab 7 — `7. Settings ⚙️` (Audio, Transparency, System Preferences & AHK v2 Expanders)
- Hosts the compact **Sound, Transparency & System Preferences** controls in the fixed top deck above the tabs bar, while **`🤫 Discreet & Meeting Mode`** and **`⌨️ AutoHotkey v2 Text Expanders`** sit below the tabs bar above the **`Active Reminders Queue`**.
- **Alarm Tone & `🔊`**: Audition built-in synthesized patterns or click **`📂`** to browse for a custom `.mp3` / `.wav` file.
- **Master Volume (`0–100%`)**: Hardware-scaled alarm loudness.
- **App Transparency (`45–100%`, default `90%`)**: Controls overall TimeSpace main window opacity, synchronized live with the **`🔆` Opacity Slider** in the top header bar.
- **Popup & HUD Opacity (`60–100%`, default `90%`)**: Controls transparency of the **Floating Mini HUD** and **Bottom-Right Alarm Popups**.
- **System Options**: Toggle **Gradual volume escalation**, **Launch at Windows boot** (enabled by default), choose your **Default Snooze**, and click **`💾`**.
- **🤫 Discreet & Meeting Mode Preferences**:
  - **Auto-mute when microphone is in use**: Automatically silences alarm audio whenever Microsoft Teams, Zoom, Webex, Google Meet, or a browser call is actively capturing the microphone.
  - **Mute alarm sound in Meeting Mode**: Bottom-right alarm popups and Windows toasts still appear visually with a discreet `🤫 MUTED` badge, but audio chimes are suppressed.
  - **Live Status & Quick Toggle**: Displays active call / microphone status with 1-click **`Toggle Meeting Mode`** and keyboard shortcut **`Ctrl+Shift+M`**.
- **⌨️ AutoHotkey v2 Text Expanders (Hotstrings)**:
  - Click **`⚡ Set Up & Edit AHK v2 Hotstrings...`** to open the dedicated pop-up manager.
  - **Quick Controls**: **`▶️ Run`** / **`⏹️ Stop`** active hotstrings directly from Settings, and check **`☑️ Auto-run hotstrings script on TimeSpace launch`**.
  - **Pop-up Window Features**:
    - **Visual Hotstrings Table**: Add, edit, duplicate, reorder, search/filter, and enable/disable hotstrings.
    - **Options**: `[*]` Instant expansion (no space/enter needed), `[?]` Trigger inside words, `[c]` Case-sensitive, `[T]` Raw text mode, `[X]` AutoHotkey v2 function/expression execution, `[O]` Omit ending character.
    - **Templates (`⚡ Presets`)**: 1-click insertion of dynamic timestamps (`:X:dts -> YYYY-MM-DD HH:mm:ss`), dynamic dates (`:X:ds`), email signatures, localhost prefixes, and ticket replies.
    - **AHK v2 Script Editor (`data/hotstrings.ahk`)**: Strict v2 code preview with `#Requires AutoHotkey v2.0+` and `#SingleInstance Force`, with **`🔄 Regenerate from Table`**, **`💾 Save Script File`**, and **`📋 Copy Script`**.

---

## 3. Persistent Queue, Notifications, HUD & Shortcuts

- **Active Reminders Queue (Bottom Panel)**: Visible on Tabs 1 (`Timers`), 2 (`RDV`), and 7 (`Settings`), and automatically hidden on Tabs 3 (`Activity`), 4 (`Scratchpad`), 5 (`Go`), and 6 (`History`) to maximize workspace height. On Tabs 1 and 2, the form area hugs its natural content height so the Active Reminders Queue expands into the remaining vertical space while preserving your exact scroll position across 1-second live countdown updates. Displays each reminder's live countdown alongside the exact day of the week, date, and time it will ring (`🔔 Day, Mon DD • HH:MM:SS`). Double-click any item (or click **`✏️`**) to edit its live details inline.
- **Bottom-Right Alarm Popup**: Triggers as a compact frameless card above the Windows system tray alongside a Windows Action Center toast.
- **Missed & Sleep-Wake Alerts**: Automatically notifies you on startup or PC wake-up if reminders elapsed while the app was closed or the PC was asleep.
- **📌 Floating Mini HUD**: Draggable translucent Cyber-Aurora always-on-top pill (`330×62`) featuring a breathing neon aura, shifting iridescent border, hover shimmer + cursor spotlight, live countdown micro-progress bar, symmetric **`⏸` / `▶`** Play/Pause for both Timers and Rendez-vous, and a **`📋`** button that opens a glowing upcoming-alarms popover card for ~4.5 seconds (hover over the popover to keep it open while inspecting queued countdowns, ring times, and notes).

| Shortcut / Action | Behavior |
|---|---|
| **`Ctrl + F8`** *(Global)* | Minimize main window if visible, or restore & focus when minimized/hidden |
| **`Ctrl + Shift + M`** *(Global)* | Toggle Meeting Mode ON/OFF (discreet silent alarms for calls & meetings) |
| **`Tab` / `Shift + Tab`** | Navigate forward / backward across every visible button, input, slider, tab bar, Scratchpad, Go Console, and queue |
| **`Ctrl + PgDn` / `Ctrl + PgUp`** *(or **`Ctrl+Tab` / `Ctrl+Shift+Tab`**)* | Switch to Next / Previous section tab (with wrap-around `7 ➔ 1` and `1 ➔ 7`) |
| **`1` – `7`** *(or **`Alt+1` – `Alt+7`**)* | Jump directly to section tabs `1. Timers` through `7. Settings` |
| **`Ctrl + K`** | Focus **✨ Quick Natural Schedule** input bar from any tab |
| **`Ctrl + Q`** | Focus **Active Reminders Queue** list (switches to Tab 1 if hidden) |
| **`Ctrl + P`** *(or **`Ctrl + Space`**)* | Pause / Resume selected reminder (when focused in Queue/Activity) or active timer |
| **`Ctrl + E`** | Edit selected or active Timer / RDV inline |
| **`Ctrl + H`** | Toggle **📌 Floating Mini HUD** |
| **`Ctrl + S`** *(Context-Aware)* | Export Scratchpad to `C:\Temp` (inside Scratchpad), Save Settings (Tab 7), Save Edit (Tab 1/2), or Export Go report (Tab 5) |
| **`F5`** *(in `5. Go ⏱️`)* | Run quick **Ping & TCP** diagnostic on current Target |
| **`Enter` / `Space`** | Activate focused button or load selected Queue / Activity item into inline edit |
| **`Delete`** *(Queue / Activity / History)* | Remove selected reminder or history entry |
| **`Escape`** | Close open Scratchpad **Find Bar** first, or clear input focus back to Tabs Bar |
| **`F1`** *(or **`?`** outside inputs)* | Open **⌨️ Keyboard Shortcuts Quick Reference** dialog |
| **`Ctrl + T`** *(Scratchpads 1, 2, 3)* | Insert `[YYYY-MM-DD HH:MM:SS] ` timestamp at cursor |
| **`Ctrl + B`** *(Scratchpads 1, 2, 3)* | Toggle **Bold** on highlighted text |
| **`Ctrl + F`** *(Scratchpads 1, 2, 3)* | Toggle inline **Find Bar** (`Enter` / `▼` next match, `▲` previous match, `Escape` close) |
| **`⏰` / Right-Click** *(Scratchpads 1, 2, 3)* | Schedule highlighted text (or current line) as a Timer or RDV with auto URL extraction |
| **Left-Click URL** *(Scratchpads 1, 2, 3)* | Open any detected web link (`https://`, `www.`) in default browser |
| **Window `[X]` Button** | Hide window to Windows System Tray (timers keep running) |
