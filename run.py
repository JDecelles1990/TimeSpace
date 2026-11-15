"""Launch the TimeSpace application."""
import ctypes
import os
import subprocess
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

_INSTANCE_MUTEX = None


def _acquire_single_instance_mutex() -> bool:
    """Ensure only one standalone TimeSpace instance runs per Windows session."""
    global _INSTANCE_MUTEX
    if sys.platform != "win32":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, False, "Local\\TimeSpace_SingleInstance_Mutex")
        if not handle:
            return True
        _INSTANCE_MUTEX = handle
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            return False
    except Exception:
        pass
    return True


def _ensure_pyside6_interpreter() -> None:
    """If launched with a global Python missing PySide6, auto-relaunch via local .venv if available."""
    try:
        import PySide6  # noqa: F401
        return
    except ImportError:
        venv_python = os.path.join(PROJECT_DIR, ".venv", "Scripts", "python.exe")
        script_path = os.path.abspath(__file__)
        if os.path.exists(venv_python) and os.path.normcase(sys.executable) != os.path.normcase(venv_python):
            sys.exit(subprocess.call([venv_python, script_path, *sys.argv[1:]]))
        raise


if __name__ == "__main__":
    _ensure_pyside6_interpreter()
    if not _acquire_single_instance_mutex():
        sys.exit(0)
    from src.gui import MainApp

    start_min = "--minimized" in sys.argv
    app = MainApp(start_minimized=start_min)
    app.mainloop()
