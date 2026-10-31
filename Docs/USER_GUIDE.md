# User Guide - Timer & Rendez-vous ⏰

Welcome to **Timer & Rendez-vous**! This guide details all features, controls, and shortcuts.

---

## ⚡ Quick Natural Language Input Bar
At the top of the window, schedule timers and appointments in plain English:
- **`Ring in 15 min`** -> Starts a 15-minute countdown alert.
- **`RDV at 4PM`** -> Schedules a rendez-vous appointment at 16:00 today (or tomorrow if 16:00 has already passed).
- **`Call Linda at 7:15 tomorrow morning`** -> Schedules a morning rendez-vous for tomorrow at 07:15.
- **`Call Linda at 7:15 tomorrow evening`** -> Schedules an evening rendez-vous for tomorrow at 19:15.
- **`Check oven in 25 mins`** -> Creates a 25-minute timer named *"Check oven"*.
- **`Remind me in 10 minutes to call John`** -> 10-minute timer named *"call John"*.
- **`Timer for 30m meditation`** -> 30-minute timer named *"meditation"*.
- **`RDV tomorrow at 10am dentist`** -> Schedules a dentist appointment for tomorrow at 10:00.
- **`at 8 tonight netflix`** -> Schedules for tonight at 20:00.

Press **Enter** or click **Create ⚡**.

---

## ⭕ Radial Circular Progress Ring & Controls
- **Live Visual Ring**: Sweeps clockwise and depletes smoothly as elapsed time advances.
- **Color Progression**: Indigo (>25%) ➔ Amber (<25%) ➔ Red (<10%).
- **Playback Controls**:
  - **`⏯️ Pause / Resume`**: Freeze the active countdown in place. The ring displays `⏸️ PAUSED`.
  - **`⏹️ Stop`**: Clears the active countdown.

---

## ⏳ Timers & Quick Presets
- **Quick Presets**: Single click on **30 Minutes**, **1 Hour**, or **2 Hours**.
- **Custom Timer**: Enter task name, hours, minutes, seconds, check **Repeat automatically** if desired, and click **Start Timer**.

---

## 📅 Rendez-vous Tab & Interactive Calendar
- **Interactive Dark Calendar Grid**:
  - Browse months using `◀` and `▶`.
  - Click any day cell to select that date.
  - Days with scheduled events feature a glowing dot (`•`).
  - **Day Inspector**: Underneath the calendar, view appointments scheduled for the selected day.
- **Quick Date Shortcuts**:
  - Click `[ Today ]`, `[ Tomorrow ]`, `[ This Friday ]`, or `[ Next Monday ]` for instant selection.
- **Big-Buttons Time Picker**:
  - Large digital time display (`14 : 30`).
  - Click `+` and `–` to adjust hours and minutes.
  - Minute chips: click `[ :00 ]`, `[ :15 ]`, `[ :30 ]`, or `[ :45 ]`.
  - Presets: click `🌅 09:00`, `☀️ 12:00`, `☕ 15:00`, or `🌙 18:00`.
- **Early Warning Lead-Time**:
  - Configure early reminders: `At time of event (0m)`, `5m before`, `10m before`, or `15m before`.
- **Category Badges**:
  - Tag events with `💼 Work`, `🩺 Health`, `📞 Call`, `🏠 Personal`, `🎉 Social`, or `📌 General`.
- **Repeating Rules**: Pick **None**, **Daily**, **Weekly**, or **Monthly**.
- **Export / Import .ics**: Sync appointments with Microsoft Outlook, Google Calendar, or Apple Calendar.

---

## ⚙️ Settings Tab
- **Alarm Sound Pattern**:
  - *Gentle Chime*: Melodic C-Major ascending arpeggio.
  - *Digital Watch*: Crisp double chirp.
  - *Urgent Siren*: Fast two-tone alternating alert.
  - *Custom Audio*: Pick any `.mp3` or `.wav` file on your computer.
- **Master Alarm Volume Slider**: Adjust loudness from `0%` to `100%` with true hardware/MCI volume scaling.
- **🔊 Play Sound Preview**: Audition the alarm sound at the chosen volume level immediately.
- **Gradual Escalation**: Soft and gentle initially, then ramps up tempo and audio intensity if unaddressed.
- **Launch at Windows Startup (minimized)**: Runs silently in the background when your computer boots.
- **Default Snooze**: Default 5 minutes or 15 minutes.

---

## 🪟 Windows System Tray & Hotkeys
- **`Ctrl + F7`**: Global toggle hotkey. Brings the window to the front or hides it to the tray from anywhere in Windows.
- **Close Button `[X]`**: Hides to the tray; timers continue running uninterrupted.
- **Tray Quick Actions (Right-Click Context Menu)**:
  - `⏯️ Pause / Resume Active Timer`
  - `Show / Hide (Ctrl+F7)`
  - `Exit App`
- **Dynamic Tooltip**: Hovering your mouse over the clock icon shows:
  `Next: check laundry (42m 10s)`.
- **Missed Alarm & Sleep Wake Detection**:
  If your laptop or PC goes to sleep during an appointment, the app detects clock drift upon wake-up and shows an *"Overdue Reminders"* alert so you never miss what happened while away.
