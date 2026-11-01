# User Guide — Timer & Rendez-vous (`Docs/USER_GUIDE.md`)

> **Canonical Scope**: End-user operational manual covering all controls, the 6 module tabs, natural-language scheduling grammar, notifications, Floating Mini HUD, and keyboard shortcuts.
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

## 2. The 6 Module Tabs

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

### Tab 4 — `4. Scratchpad 📝` (Persistent Time Notes)
- Monospace notepad for quick time notes, call logs, or client references, auto-saved continuously (`500ms` debounce) with live save status in the toolbar.
- **`🕒 +Timestamp (Ctrl+T)`**: Inserts `[YYYY-MM-DD HH:MM:SS] ` at the cursor.
- **`📋 Copy All`** / **`🧹 Clear`**: Copy the entire scratchpad to clipboard or clear after confirmation.

### Tab 5 — `5. History 📜` (Completed & Triggered Log)
- Dedicated full-height audit log recording every **`Triggered`**, **`Dismissed`**, **`Opened Link`**, and **`Snoozed`** reminder (up to the latest 100 entries).
- **`🔗 Open Link`**: Appears automatically in the header when selecting a history entry with an attached URL/path.
- **`📋 Copy Selected`**: Copies `[timestamp] Name (Status)` (plus any attached note and link) to the clipboard in one click.
- **`🧹 Clear History`**: Empties the persisted history log.

### Tab 6 — `6. Settings ⚙️` (Audio, Opacity & System Preferences)
- **Alarm Tone & `🔊 Preview`**: Audition built-in synthesized patterns (*Gentle Chime*, *Digital Watch*, *Urgent Siren*) or **`Browse...`** for a custom `.mp3` / `.wav` file.
- **Master Volume (`0–100%`)**: Hardware-scaled alarm loudness.
- **Popup & HUD Opacity (`60–100%`, default `90%`)**: Controls transparency of the **Floating Mini HUD** and **Bottom-Right Alarm Popups** with live preview while dragging (keeping the Main Window `100%` solid).
- **System Options**: Toggle **Gradual volume escalation**, **Launch at Windows boot** (starts minimized in tray), choose your **Default Snooze** (`5`, `10`, `15`, or `30` min), and click **`Save Settings ✓`**.

---

## 3. Persistent Queue, Notifications, HUD & Shortcuts

- **Active Reminders Queue (Bottom Panel)**: Always visible beneath all 6 tabs (7–9+ visible rows). Items highlight **Amber** under 5 minutes and **Crimson Red** under 1 minute, and display `🔗` / `📝` indicators (with hover tooltips) when links or notes are attached.
- **Bottom-Right Alarm Popup**: Triggers as a compact frameless card above the Windows system tray (stacking vertically if multiple alarms fire) alongside a Windows Action Center toast—without forcing the main window open over your work. Displays any attached note and lets you click **`🔗 Open Link`** (which opens the URL/file, stops alarm audio, logs `Opened Link`, and dismisses the popup), **`✓ Dismiss`**, or **`💤 Snooze`** (`5m`/`10m`/`15m`/`30m`, preserving notes & links).
- **Missed & Sleep-Wake Alerts**: Automatically notifies you on startup or PC wake-up if reminders elapsed while the app was closed or the PC was asleep.
- **📌 Floating Mini HUD**: Draggable always-on-top desktop pill showing the nearest countdown with urgency border colors and quick pause (`⏯`). Double-click the HUD to bring the main window forward.

| Shortcut / Action | Behavior |
|---|---|
| **`Ctrl + F7`** *(Global)* | Toggle main window visibility from any application in Windows |
| **`Ctrl + T`** *(Scratchpad)* | Insert `[YYYY-MM-DD HH:MM:SS] ` timestamp at cursor |
| **`Enter`** *(Inputs)* | Submit Quick Natural Schedule or Daily Task Timer form |
| **Window `[X]` Button** | Hide window to Windows System Tray (timers keep running) |
| **Tray Icon Hover / Right-Click** | View live next-reminder countdown tooltip; Pause/Resume, Toggle HUD, or Exit |
