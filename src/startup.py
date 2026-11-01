"""Windows startup registry management using standard library winreg."""
import os
import sys
import winreg
from src.config import APP_REGISTRY_NAME


def get_executable_command() -> str:
    """Return the exact command to run this application at Windows startup."""
    python_exe = sys.executable
    main_script = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "run.py"))
    pythonw_exe = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
    exe = pythonw_exe if os.path.exists(pythonw_exe) else python_exe
    return f'"{exe}" "{main_script}" --minimized'


def is_startup_enabled() -> bool:
    """Check if app is registered under HKCU Run key."""
    if sys.platform != "win32":
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        )
        val, _ = winreg.QueryValueEx(key, APP_REGISTRY_NAME)
        winreg.CloseKey(key)
        return bool(val)
    except FileNotFoundError:
        return False
    except Exception:
        return False


def set_startup_enabled(enable: bool) -> bool:
    """Enable or disable auto-start on Windows boot."""
    if sys.platform != "win32":
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        if enable:
            cmd = get_executable_command()
            winreg.SetValueEx(key, APP_REGISTRY_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_REGISTRY_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Error setting startup registry: {e}")
        return False
