"""Launch the Timer & Rendez-vous application."""
import sys
from src.gui import MainApp

if __name__ == "__main__":
    start_min = "--minimized" in sys.argv
    app = MainApp(start_minimized=start_min)
    app.mainloop()
