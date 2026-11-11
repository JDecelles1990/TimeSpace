"""Zero-dependency Windows 10/11 microphone capture activity detector.

Monitors active microphone capture sessions across standard Win32 and packaged/UWP
applications (Microsoft Teams, Zoom, Webex, Google Meet, Slack, Discord, browsers)
via Windows CapabilityAccessManager ConsentStore registry keys.
"""
import sys
import os
from typing import List, Tuple

if sys.platform == "win32":
    import winreg
else:
    winreg = None


def _clean_app_name(sub_type: str, raw_key: str) -> str:
    """Extract a user-friendly application name from raw registry subkeys."""
    if sub_type == "NonPackaged":
        # Raw key is typically a path encoded with '#' separators:
        # e.g., 'C:#Program Files#Microsoft Teams#current#Teams.exe'
        path_str = raw_key.replace("#", "\\")
        base = os.path.basename(path_str)
        return base if base else raw_key
    elif sub_type == "Packaged":
        # Raw key is package family name: e.g. 'MicrosoftTeams_8wekyb3d8bbwe'
        parts = raw_key.split("_")
        return parts[0] if parts else raw_key
    return raw_key


def get_active_microphone_apps() -> List[str]:
    """Return a list of friendly application names currently capturing microphone audio."""
    if sys.platform != "win32" or winreg is None:
        return []

    base_path = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"
    active_apps: List[str] = []

    for sub_type in ("NonPackaged", "Packaged"):
        full_path = f"{base_path}\\{sub_type}"
        try:
            parent_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, full_path, 0, winreg.KEY_READ)
        except Exception:
            continue

        try:
            idx = 0
            while True:
                try:
                    app_key_name = winreg.EnumKey(parent_key, idx)
                    idx += 1
                except OSError:
                    break

                try:
                    app_key = winreg.OpenKey(parent_key, app_key_name, 0, winreg.KEY_READ)
                    try:
                        stop_val, _ = winreg.QueryValueEx(app_key, "LastUsedTimeStop")
                        start_val, _ = winreg.QueryValueEx(app_key, "LastUsedTimeStart")
                        # When microphone is actively open/capturing, Windows sets LastUsedTimeStop to 0
                        # and LastUsedTimeStart to the FILETIME timestamp of session start.
                        if stop_val == 0 and start_val > 0:
                            friendly_name = _clean_app_name(sub_type, app_key_name)
                            if friendly_name and friendly_name not in active_apps:
                                active_apps.append(friendly_name)
                    except FileNotFoundError:
                        pass
                    finally:
                        winreg.CloseKey(app_key)
                except Exception:
                    pass
        finally:
            try:
                winreg.CloseKey(parent_key)
            except Exception:
                pass

    return active_apps


def is_microphone_in_use() -> bool:
    """Return True if any application is currently capturing audio from the microphone."""
    return bool(get_active_microphone_apps())

