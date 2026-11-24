"""Windows startup registry and Startup folder management using standard library winreg."""
import os
import sys
import winreg
from src.config import APP_REGISTRY_NAME
from src.paths import get_app_dir, is_frozen

_RUN_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APPROVED_RUN_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"


def _get_project_dir() -> str:
    return str(get_app_dir())


def get_startup_vbs_path() -> str:
    """Return the path to the windowless VBScript launcher inside the Windows Startup folder."""
    appdata = os.environ.get("APPDATA") or os.path.expanduser(r"~\AppData\Roaming")
    return os.path.join(
        appdata,
        "Microsoft",
        "Windows",
        "Start Menu",
        "Programs",
        "Startup",
        f"{APP_REGISTRY_NAME}.vbs",
    )


def get_executable_command() -> str:
    """Return the exact command to run this application at Windows startup."""
    if is_frozen():
        return f'"{os.path.abspath(sys.executable)}" --minimized'

    project_dir = _get_project_dir()
    main_script = os.path.join(project_dir, "run.py")

    # Prefer virtual environment pythonw.exe if available so PySide6 is guaranteed
    venv_pythonw = os.path.join(project_dir, ".venv", "Scripts", "pythonw.exe")
    if os.path.exists(venv_pythonw):
        exe = venv_pythonw
    else:
        python_exe = sys.executable
        pythonw_exe = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
        exe = pythonw_exe if os.path.exists(pythonw_exe) else python_exe

    return f'"{exe}" "{main_script}" --minimized'


def is_startup_enabled() -> bool:
    """Check if app is registered with up-to-date HKCU Run and Startup folder entries."""
    if sys.platform != "win32":
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _RUN_REG_PATH,
            0,
            winreg.KEY_READ,
        )
        val, _ = winreg.QueryValueEx(key, APP_REGISTRY_NAME)
        winreg.CloseKey(key)
        expected_cmd = get_executable_command()
        return val == expected_cmd and os.path.exists(get_startup_vbs_path())
    except FileNotFoundError:
        return False
    except Exception:
        return False


def set_startup_enabled(enable: bool) -> bool:
    """Enable or disable auto-start on Windows boot (HKCU Run + StartupApproved + Startup folder)."""
    if sys.platform != "win32":
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _RUN_REG_PATH,
            0,
            winreg.KEY_SET_VALUE,
        )
        vbs_path = get_startup_vbs_path()
        if enable:
            cmd = get_executable_command()
            winreg.SetValueEx(key, APP_REGISTRY_NAME, 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)

            approved_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, _APPROVED_RUN_REG_PATH)
            winreg.SetValueEx(
                approved_key,
                APP_REGISTRY_NAME,
                0,
                winreg.REG_BINARY,
                bytes([2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
            )
            winreg.CloseKey(approved_key)

            os.makedirs(os.path.dirname(vbs_path), exist_ok=True)
            proj_vbs = _get_project_dir().replace('"', '""')
            cmd_vbs = cmd.replace('"', '""')
            vbs_content = (
                'Set WshShell = CreateObject("WScript.Shell")\n'
                f'WshShell.CurrentDirectory = "{proj_vbs}"\n'
                f'WshShell.Run "{cmd_vbs}", 0, False\n'
            )
            with open(vbs_path, "w", encoding="utf-8") as fh:
                fh.write(vbs_content)
        else:
            try:
                winreg.DeleteValue(key, APP_REGISTRY_NAME)
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
            if os.path.exists(vbs_path):
                os.remove(vbs_path)
        return True
    except Exception as e:
        print(f"Error setting startup registry: {e}")
        return False
