# Architecture Specification - Timer & Rendez-vous

## Concurrency & Threading Model
The application maintains responsiveness, smooth canvas rendering, and non-blocking audio/scheduling using a multi-threaded architecture:

```
+-----------------------------------------------------------------------------------+
|                              Main GUI Thread (gui.py)                             |
|  - Tkinter event loop & canvas rendering                                          |
|  - Radial Circular Progress Ring with Pause/Resume (circular_ring.py)             |
|  - Pomodoro technique workflow & streak tracking                                  |
|  - Smart Natural Language Input Parser (natural_parser.py)                        |
|  - Settings & Preferences management (storage.py)                                 |
+-----------------------------------------------------------------------------------+
         ^                                           |                             ^
         | root.after() callbacks                    | triggers                    |
         v                                           v                             |
+------------------------------+     +-------------------------------+             |
|   Scheduler Thread           |     |    Alarm Window & Toasts      |             |
|   (src/scheduler.py)         |     |    (alarm_dialog.py,          |             |
|   - 500ms daemon loop        |     |     notifications.py)         |             |
|   - Sleep drift detector     |     +-------------------------------+             |
|   - Pause/Resume state       |                     |                             |
|   - Auto-persistence         |                     v                             |
+------------------------------+     +-------------------------------+             |
         |                           |    Sound Player Thread        |             |
         v                           |    (src/sound.py)             |             |
+------------------------------+     |    - winsound synthesizer     |             |
|   System Tray Daemon         |     |    - winmm.dll MCI player     |             |
|   (src/tray.py)              |     |    - setaudio volume 0-1000   |             |
|   - Live hover tooltip update|     |    - gradual volume fade-in   |             |
|   - Quick Pomodoro triggers  |     +-------------------------------+             |
+------------------------------+                                                   |
         |                                                                         |
         v                                                                         |
+----------------------------------------------------------------------------------+
|                     OS Hotkey Monitor (keyboard / Ctrl+F7)                       |
+----------------------------------------------------------------------------------+
```

## Sleep & Clock Drift Detection Algorithm
In `src/scheduler.py`, the worker thread records `last_tick = time.time()` on every 500ms iteration.
- If `now - last_tick > 6.0`, it concludes the system suspended, hibernated, or entered low-power modern standby.
- The scheduler queries all active, non-paused items whose `target_time` elapsed during that window.
- It immediately invokes `on_wake_missed_callback`, delivering an Action Center toast notification and visual warning dialog with missed items.

## Hardware Volume & Audio Fade-in (`src/sound.py`)
- Custom audio utilizes the Windows Multimedia MCI API:
  `mciSendStringW("setaudio AlarmMedia volume to <0-1000>")`.
- Converts the 0-100% volume slider value into the 0-1000 MCI hardware scale.
- When **Gradual Escalation** is active:
  - MCI playback begins at 25% volume and smoothly interpolates to 100% of the target volume over 15 seconds.
  - Synthesizer beeps accelerate tempo and extend pulse lengths dynamically.

## Pause & Resume Architecture
- `ScheduledItem` tracks:
  - `is_paused: bool`
  - `remaining_paused: float`
- When paused, `remaining_paused = target_time - now` is frozen and saved to disk.
- When resumed, a new `target_time = now + remaining_paused` is assigned, preventing elapsed time lost while paused.
- The Canvas ring displays `⏸️ PAUSED` and colors the arc `#3f3f46`.
