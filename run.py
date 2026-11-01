"""Launch the Timer & Rendez-vous application."""
import os
import sys
import subprocess


def _ensure_pyside6_interpreter() -> None:
    """If launched with a global Python missing PySide6, auto-relaunch via local .venv if available."""
    try:
        import PySide6  # noqa: F401
        return
    except ImportError:
        project_dir = os.path.dirname(os.path.abspath(__file__))
        venv_python = os.path.join(project_dir, ".venv", "Scripts", "python.exe")
        script_path = os.path.abspath(__file__)
        if os.path.exists(venv_python) and os.path.normcase(sys.executable) != os.path.normcase(venv_python):
            sys.exit(subprocess.call([venv_python, script_path, *sys.argv[1:]]))
        raise


if __name__ == "__main__":
    _ensure_pyside6_interpreter()
    from src.gui import MainApp

    start_min = "--minimized" in sys.argv
    app = MainApp(start_minimized=start_min)
    app.mainloop()
