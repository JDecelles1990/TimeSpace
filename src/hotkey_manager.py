"""Native Win32 global hotkey monitor (RegisterHotKey / WM_HOTKEY) without admin privileges."""
import sys
import ctypes
from ctypes import wintypes
import threading
from typing import Callable, Optional


MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

VK_MAP = {
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
}


class GlobalHotkeyListener:
    """Registers an OS-wide global hotkey on Windows using user32.RegisterHotKey."""

    def __init__(self, hotkey_str: str, callback: Callable[[], None]):
        self.hotkey_str = hotkey_str.lower().strip()
        self.callback = callback
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._running = False

    def start(self) -> None:
        if sys.platform != "win32" or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._message_loop, daemon=True)
        self._thread.start()

    def _parse_hotkey(self):
        parts = [p.strip() for p in self.hotkey_str.split("+") if p.strip()]
        modifiers = MOD_NOREPEAT
        vk = 0
        for part in parts:
            if part in ("ctrl", "control"):
                modifiers |= MOD_CONTROL
            elif part == "alt":
                modifiers |= MOD_ALT
            elif part == "shift":
                modifiers |= MOD_SHIFT
            elif part in ("win", "windows", "super"):
                modifiers |= MOD_WIN
            elif part in VK_MAP:
                vk = VK_MAP[part]
            elif len(part) == 1:
                vk = ord(part.upper())
        return modifiers, vk

    def _message_loop(self) -> None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._thread_id = kernel32.GetCurrentThreadId()

        modifiers, vk = self._parse_hotkey()
        if not vk:
            return

        hotkey_id = 1
        registered = bool(user32.RegisterHotKey(None, hotkey_id, modifiers, vk))
        if not registered:
            # Fallback to `keyboard` library if RegisterHotKey is already claimed by another process
            try:
                import keyboard
                keyboard.add_hotkey(self.hotkey_str, self.callback)
            except Exception:
                pass
            return

        msg = wintypes.MSG()
        try:
            while self._running:
                ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret == 0 or ret == -1:
                    break
                if msg.message == WM_HOTKEY and msg.wParam == hotkey_id:
                    try:
                        self.callback()
                    except Exception:
                        pass
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            user32.UnregisterHotKey(None, hotkey_id)

    def stop(self) -> None:
        self._running = False
        if sys.platform == "win32" and self._thread_id:
            try:
                ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
            except Exception:
                pass

