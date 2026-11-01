"""Audio alarm player with Winsound presets, gradual escalation, volume slider, and native MCI (MP3/WAV)."""
import os
import sys
import time
import ctypes
import threading
from typing import Callable, Optional
from src.config import AppConfig, SOUND_PRESETS
from src.storage import Storage


class SoundPlayer:
    def __init__(self, config: Optional[AppConfig] = None):
        self.config: AppConfig = config or Storage.load_config()
        self._playing: bool = False
        self._thread: Optional[threading.Thread] = None
        self._preview_thread: Optional[threading.Thread] = None
        self._previewing: bool = False

    def update_config(self, config: AppConfig) -> None:
        """Synchronize runtime audio settings with the active AppConfig."""
        self.config = config

    def start_alarm(self, config: Optional[AppConfig] = None) -> None:
        if config is not None:
            self.config = config
        if self._playing:
            return
        self.stop_preview()
        self._playing = True
        self._thread = threading.Thread(target=self._play_alarm_loop, daemon=True)
        self._thread.start()

    def stop_alarm(self) -> None:
        self._playing = False
        self._stop_mci()

    def start_preview(self, sound_type: str, custom_path: str = "", volume: int = 85) -> None:
        self.stop_alarm()
        self.stop_preview()
        self._previewing = True
        self._preview_thread = threading.Thread(
            target=self._play_preview_loop,
            args=(sound_type, custom_path, volume),
            daemon=True,
        )
        self._preview_thread.start()

    def stop_preview(self) -> None:
        self._previewing = False
        self._stop_mci()

    def _play_preview_loop(self, sound_type: str, custom_path: str, volume: int) -> None:
        cycles = 2
        for _ in range(cycles):
            if not self._previewing:
                break
            if sound_type == "custom" and custom_path and os.path.exists(custom_path):
                self._play_mci_file(
                    custom_path,
                    max_cycles=1,
                    check_flag=lambda: self._previewing,
                    target_volume=volume,
                )
            else:
                self._play_preset_pattern(
                    sound_type,
                    check_flag=lambda: self._previewing,
                    speed_multiplier=1.0,
                )
            time.sleep(0.3)
        self._previewing = False

    def _play_alarm_loop(self) -> None:
        cfg = self.config or Storage.load_config()
        sound_type = cfg.sound_type
        custom_path = cfg.custom_sound_path
        escalate = cfg.gradual_escalation
        volume = cfg.volume

        start_time = time.time()

        if sound_type == "custom" and custom_path and os.path.exists(custom_path):
            self._play_mci_file(
                custom_path,
                max_cycles=999,
                check_flag=lambda: self._playing,
                target_volume=volume,
                escalate=escalate,
            )
        else:
            while self._playing:
                elapsed = time.time() - start_time
                multiplier = 1.0
                if escalate:
                    if elapsed < 8:
                        multiplier = 0.7  # slower, gentler
                    elif elapsed < 16:
                        multiplier = 1.0
                    else:
                        multiplier = 1.4  # faster, urgent

                self._play_preset_pattern(
                    sound_type,
                    check_flag=lambda: self._playing,
                    speed_multiplier=multiplier,
                )
                pause = max(0.2, 0.8 / multiplier)
                time.sleep(pause)

    def _play_preset_pattern(
        self,
        sound_type: str,
        check_flag: Callable[[], bool],
        speed_multiplier: float = 1.0,
    ) -> None:
        if sys.platform != "win32":
            sys.stdout.write("\a")
            sys.stdout.flush()
            time.sleep(0.5)
            return

        import winsound

        def dur(base_ms: int) -> int:
            return max(50, int(base_ms / speed_multiplier))

        if sound_type == "digital":
            if check_flag():
                winsound.Beep(2048, dur(100))
            time.sleep(0.08)
            if check_flag():
                winsound.Beep(2048, dur(100))
        elif sound_type == "urgent":
            if check_flag():
                winsound.Beep(880, dur(180))
            if check_flag():
                winsound.Beep(1320, dur(260))
        else:
            notes = [523, 659, 784, 1046]
            for note in notes:
                if not check_flag():
                    break
                winsound.Beep(note, dur(140))
                time.sleep(0.02)

    def _play_mci_file(
        self,
        file_path: str,
        max_cycles: int = 999,
        check_flag: Optional[Callable[[], bool]] = None,
        target_volume: int = 85,
        escalate: bool = False,
    ) -> None:
        if sys.platform != "win32":
            return

        if check_flag is None:
            check_flag = lambda: self._playing

        winmm = ctypes.windll.winmm
        alias = "AlarmMedia"
        count = 0
        start_time = time.time()

        while check_flag() and count < max_cycles:
            winmm.mciSendStringW(f"close {alias}", None, 0, None)
            cmd = f'open "{file_path}" type mpegvideo alias {alias}'
            err = winmm.mciSendStringW(cmd, None, 0, None)
            if err != 0:
                self._play_preset_pattern("gentle", check_flag)
                return

            cur_vol = target_volume
            if escalate:
                elapsed = time.time() - start_time
                ramp = min(1.0, max(0.25, elapsed / 15.0))
                cur_vol = int(target_volume * ramp)

            mci_vol = int((cur_vol / 100.0) * 1000)
            winmm.mciSendStringW(f"setaudio {alias} volume to {mci_vol}", None, 0, None)
            winmm.mciSendStringW(f"play {alias}", None, 0, None)

            status_buf = ctypes.create_unicode_buffer(128)
            while check_flag():
                if escalate:
                    elapsed = time.time() - start_time
                    ramp = min(1.0, max(0.25, elapsed / 15.0))
                    cur_vol = int(target_volume * ramp)
                    mci_vol = int((cur_vol / 100.0) * 1000)
                    winmm.mciSendStringW(f"setaudio {alias} volume to {mci_vol}", None, 0, None)

                winmm.mciSendStringW(f"status {alias} mode", status_buf, 128, None)
                if status_buf.value != "playing":
                    break
                time.sleep(0.25)
            count += 1
            time.sleep(0.3)

        winmm.mciSendStringW(f"close {alias}", None, 0, None)

    def _stop_mci(self) -> None:
        if sys.platform == "win32":
            ctypes.windll.winmm.mciSendStringW("close AlarmMedia", None, 0, None)
