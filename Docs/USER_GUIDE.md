# User Guide — TimeSpace (`Docs/USER_GUIDE.md`)

> **Canonical Scope**: End-user operational manual covering all controls, the 7 module tabs, natural-language scheduling grammar, notifications, Floating Mini HUD, and keyboard shortcuts.
> *(For technical architecture and F7Hub embedding, see [ARCHITECTURE.md](ARCHITECTURE.md). For file/state schemas, see [STATE_AND_CONFIG.md](STATE_AND_CONFIG.md).)*

---

## 1. Header & Hero Deck (Top Section)

- **Neon Button Glow**: Every button glows with a violet ➔ cyan gradient while hovered and flashes a cyan ➔ green gradient while clicked. The 7 tab buttons use the same gradients (violet ➔ cyan on hover, cyan ➔ green for the active tab).
- **Header Bar**: Displays the application title, keyboard shortcut hint (`Ctrl+F7 | Keys 1-7`), the **App Window Opacity Slider (`🔆 45%–100%`, default `90%`)** immediately on the left of the **`📌 HUD`** button, and the **`📌 HUD`** toggle button.
- **Left — ⭕ Radial Circular Progress Ring** *(visible on Tabs 1, 2, 3, and 6; hidden on Tabs 4, 5, and 7 for maximum vertical workspace)*:
  - Smoothly depletes clockwise for your active timer (or nearest upcoming Rendez-vous when no timer is active).
  - **Urgency Colors**: Indigo (`>25%` remaining) ➔ Amber (`<25%`) ➔ Crimson Red (`<10%`), with inline `⏸ PAUSED` and `🔁 Repeat` status badges.
  - **`⏸️` / `▶️`** & **`⏹️`**: Compact emoji controls to directly pause/resume or cancel the active countdown.
- **Right — ⚡ Quick Natural Schedule**:
  - Type an everyday English expression and press **`Enter`** or click **`⚡`**:

| Input Category | Example Expressions | Result |
|---|---|---|
| **Countdown Timers** | `Ring in 15 min` · `Check backups in 45m` · `Remind me in 10 minutes to call John` · `Timer for 30m review` | Starts a countdown timer immediately |
| **Same / Next Day RDV** | `RDV at 4PM` · `Call Linda at 7:15 tomorrow morning` · `at 18:30 dinner` · `at 8 tonight backup check` | Schedules a calendar Rendez-vous (auto-advances to tomorrow if today's time has passed) |
| **Relative Days / Weeks** | `Call Sam in 2 days` · `Call Sam in 2 days at 3pm` · `Follow up in 1 week at 10am` | Schedules a Rendez-vous `N` days/weeks ahead (defaults to `12:00` if no time specified) |
| **Next Weekday RDV** | `Dentist next Friday` · `Dentist next Friday at 14:00` · `Meeting on Wednesday at 3pm` | Schedules a Rendez-vous on the upcoming target weekday |

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
  - **Cat, Alert & Repeat**: Tag with a category, set an early lead-time (`At time (0m)`, `5m`, `10m`, or `15m before`), and optionally repeat (`None`, `Daily`, `Weekly`, `Monthly`).
  - **Compact Actions & Inline RDV Editing**: Click **`📤 .ics`** (Export), **`📥 .ics`** (Import), **`✏️`** (Edit active RDV), or **`➕ RDV`** (switches to **`💾 RDV`** when editing an existing appointment).

### Tab 3 — `3. Activity 📋` (Live Dual-Column Dashboard)
- Automatically hides the bottom `Active Reminders Queue` so **`⏳ All Timers`** and **`📅 All Rendez-vous`** expand to 100% of the vertical space.
- Double-click any timer or RDV (or click **`✏️`**) to jump straight into inline edit mode, or use **`⏸️`**, **`🗑️`**, and **`🔗`**.

### Tab 4 — `4. Scratchpad 📝` (Dual Upper & Lower Rich-Text Scratchpads + Power Tools)
- Automatically hides both the top Hero Deck and the bottom `Active Reminders Queue`, providing a vertical `QSplitter` with **two independent rich-text Scratchpads**:
  1. **`📝 Scratchpad 1 (Upper)`**: Pin priority notes, commands, client numbers, or URLs at the top.
  2. **`📝 Scratchpad 2 (Lower)`**: Jot down ongoing time notes, call logs, or diagnostic snippets below.
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
  - Automatically hides both the top Hero Deck and the bottom `Active Reminders Queue` on **`5. Go ⏱️`**.
  - Beneath the live color-highlighted console (`📋` Copy, `📝` +Scratchpad, `💾` Export, `⏹️` Stop, `🧹` Clear), a vertical `QSplitter` hosts the **3rd Rich-Text Scratchpad** (`📝 Go Scratchpad`) with Bold (`𝐁`), Color (`🎨`), Timestamp (`🕒`), Find (`🔍` `Ctrl+F`), Schedule Selection (`⏰`), Export (`💾` `Ctrl+S`), Copy (`📋`), Clear (`🧹`), and clickable URLs.

### Tab 6 — `6. History 📜` (Completed & Triggered Log)
- Automatically hides the bottom `Active Reminders Queue` so the Completed & Triggered Reminders History list expands to full vertical height.
- Press the **`Delete`** key (or click **`🗑️`**) to remove selected individual history entries, or use **`🔗`** (Open Link), **`📋`** (Copy Selected), and **`🧹`** (Clear All History).

### Tab 7 — `7. Settings ⚙️` (Audio, Transparency, System Preferences & AHK v2 Expanders)
- Automatically hides the top Hero Deck to provide extra vertical room for settings.
- **Alarm Tone & `🔊`**: Audition built-in synthesized patterns or click **`📂`** to browse for a custom `.mp3` / `.wav` file.
- **Master Volume (`0–100%`)**: Hardware-scaled alarm loudness.
- **App Transparency (`45–100%`, default `90%`)**: Controls overall TimeSpace main window opacity, synchronized live with the **`🔆` Opacity Slider** in the top header bar.
- **Popup & HUD Opacity (`60–100%`, default `90%`)**: Controls transparency of the **Floating Mini HUD** and **Bottom-Right Alarm Popups**.
- **System Options**: Toggle **Gradual volume escalation**, **Launch at Windows boot**, choose your **Default Snooze**, and click **`💾`**.
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

- **Active Reminders Queue (Bottom Panel)**: Visible on Tabs 1 (`Timers`), 2 (`RDV`), and 7 (`Settings`), and automatically hidden on Tabs 3 (`Activity`), 4 (`Scratchpad`), 5 (`Go`), and 6 (`History`) to maximize workspace height. Double-click any item (or click **`✏️`**) to edit its live details inline.
- **Bottom-Right Alarm Popup**: Triggers as a compact frameless card above the Windows system tray alongside a Windows Action Center toast.
- **Missed & Sleep-Wake Alerts**: Automatically notifies you on startup or PC wake-up if reminders elapsed while the app was closed or the PC was asleep.
- **📌 Floating Mini HUD**: Draggable always-on-top desktop pill showing the nearest countdown.

| Shortcut / Action | Behavior |
|---|---|
| **`Ctrl + F7`** *(Global)* | Minimize main window if visible, or restore & focus when minimized/hidden |
| **`1` – `7`** *(or **`Alt+1` – `Alt+7`**)* | Jump directly to section tabs `1. Timers` through `7. Settings` (`Escape` clears input focus) |
| **`Delete`** *(in `6. History 📜`)* | Delete selected individual entry/entries from the History list |
| **`Double-Click` / `✏️`** *(Queue / Activity)* | Load active Timer or RDV into Tab 1 / Tab 2 for inline editing (`💾`) |
| **`Ctrl + T`** *(Scratchpads 1, 2, 3)* | Insert `[YYYY-MM-DD HH:MM:SS] ` timestamp at cursor |
| **`Ctrl + B`** *(Scratchpads 1, 2, 3)* | Toggle **Bold** on highlighted text |
| **`Ctrl + F`** *(Scratchpads 1, 2, 3)* | Toggle inline **Find Bar** (`Enter` / `▼` next match, `▲` previous match, `Escape` close) |
| **`Ctrl + S`** *(Scratchpads 1, 2, 3)* | Export Scratchpad notes to `C:\Temp\TimeSpace_Scratchpad_<name>_<timestamp>.md` |
| **`⏰` / Right-Click** *(Scratchpads 1, 2, 3)* | Schedule highlighted text (or current line) as a Timer or RDV with auto URL extraction |
| **Left-Click URL** *(Scratchpads 1, 2, 3)* | Open any detected web link (`https://`, `www.`) in default browser |
| **`Enter`** *(Inputs)* | Submit Quick Natural Schedule or Daily Task Timer form |
| **Window `[X]` Button** | Hide window to Windows System Tray (timers keep running) |
