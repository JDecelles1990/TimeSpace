"""Windows System Tray Icon integration with pystray, quick actions, and dynamic tooltips."""
import threading
from typing import Callable, Optional

class TrayManager:
    def __init__(
        self,
        on_toggle: Callable,
        on_exit: Callable,
        on_quick_pomodoro: Optional[Callable] = None,
        on_quick_break: Optional[Callable] = None,
        on_toggle_pause: Optional[Callable] = None
    ):
        self.on_toggle = on_toggle
        self.on_exit = on_exit
        self.on_quick_pomodoro = on_quick_pomodoro
        self.on_quick_break = on_quick_break
        self.on_toggle_pause = on_toggle_pause
        self.icon = None

    def start(self):
        thread = threading.Thread(target=self._create_tray, daemon=True)
        thread.start()

    def update_tooltip(self, text: str):
        """Update the hover tooltip in the Windows notification area."""
        if self.icon:
            try:
                self.icon.title = text[:128]
            except Exception:
                pass

    def _create_image(self):
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Clock circle
        draw.ellipse([4, 4, 60, 60], outline="#6366f1", width=5)
        # Clock hands
        draw.line([32, 32, 32, 14], fill="#f4f4f5", width=4)
        draw.line([32, 32, 46, 32], fill="#f59e0b", width=3)
        return img

    def _create_tray(self):
        try:
            import pystray
            from pystray import MenuItem as item, Menu

            image = self._create_image()
            menu_items = [
                item("Show / Hide (Ctrl+F7)", lambda: self.on_toggle(), default=True),
                Menu.SEPARATOR,
            ]

            if self.on_quick_pomodoro:
                menu_items.append(item("🍅 Start 25m Pomodoro", lambda: self.on_quick_pomodoro()))
            if self.on_quick_break:
                menu_items.append(item("☕ Start 5m Break", lambda: self.on_quick_break()))
            if self.on_toggle_pause:
                menu_items.append(item("⏯️ Pause / Resume Active Timer", lambda: self.on_toggle_pause()))

            menu_items.extend([
                Menu.SEPARATOR,
                item("Exit App", lambda: self.on_exit())
            ])

            self.icon = pystray.Icon("timer_rdv_app", image, "Timer & Rendez-vous", Menu(*menu_items))
            self.icon.run()
        except ImportError:
            pass

    def stop(self):
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
