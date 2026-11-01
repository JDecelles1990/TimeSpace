"""Windows System Tray Icon integration with pystray, quick actions, and dynamic tooltips."""
import threading
from typing import Callable, Optional
from src.config import APP_TITLE, COLORS, HOTKEY


class TrayManager:
    def __init__(
        self,
        on_toggle: Callable[[], None],
        on_exit: Callable[[], None],
        on_toggle_pause: Optional[Callable[[], None]] = None,
        on_toggle_hud: Optional[Callable[[], None]] = None,
    ):
        self.on_toggle = on_toggle
        self.on_exit = on_exit
        self.on_toggle_pause = on_toggle_pause
        self.on_toggle_hud = on_toggle_hud
        self.icon = None

    def start(self) -> None:
        thread = threading.Thread(target=self._create_tray, daemon=True)
        thread.start()

    def update_tooltip(self, text: str) -> None:
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
        draw.ellipse([4, 4, 60, 60], outline=COLORS["accent"], width=5)
        draw.line([32, 32, 32, 14], fill=COLORS["text"], width=4)
        draw.line([32, 32, 46, 32], fill=COLORS["accent_warning"], width=3)
        return img

    def _create_tray(self) -> None:
        try:
            import pystray
            from pystray import MenuItem as item, Menu

            image = self._create_image()
            menu_items = [
                item(f"Show / Hide ({HOTKEY.upper()})", lambda: self.on_toggle(), default=True),
                Menu.SEPARATOR,
            ]

            if self.on_toggle_pause:
                menu_items.append(item("⏯️ Pause / Resume Active Timer", lambda: self.on_toggle_pause()))
            if self.on_toggle_hud:
                menu_items.append(item("📌 Toggle Mini HUD", lambda: self.on_toggle_hud()))

            menu_items.extend([
                Menu.SEPARATOR,
                item("Exit App", lambda: self.on_exit()),
            ])

            self.icon = pystray.Icon("timer_rdv_app", image, APP_TITLE, Menu(*menu_items))
            self.icon.run()
        except ImportError:
            pass

    def stop(self) -> None:
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
