"""Centralized frozen-safe path resolution for bundled read-only assets and writable user data."""
from __future__ import annotations

import os
from pathlib import Path
import sys


def is_frozen() -> bool:
    """Return True when running inside a PyInstaller frozen bundle."""
    return bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))


def get_bundle_root() -> Path:
    """Return the root directory containing read-only bundled assets (`sys._MEIPASS` when frozen)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return Path(__file__).resolve().parent.parent


def get_app_dir() -> Path:
    """Return the executable directory when frozen, or the repository root in dev mode."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def get_resource_path(*parts: str) -> Path:
    """Resolve a read-only asset or companion binary relative to the bundle/repo root."""
    return get_bundle_root().joinpath(*parts)


def get_go_binary_name() -> str:
    """Return the platform-specific compiled Go diagnostic CLI filename."""
    if sys.platform == "win32":
        return "diag_windows.exe"
    if sys.platform == "darwin":
        return "diag_mac_arm64"
    return "diag_linux"


def get_go_binary_path() -> Path:
    """Resolve the compiled Go diagnostic binary path in both dev and frozen modes."""
    name = get_go_binary_name()
    bundled = get_resource_path("bin", name)
    if bundled.exists():
        return bundled
    sibling = get_app_dir() / "bin" / name
    if sibling.exists():
        return sibling
    return bundled


def _is_dir_writable(path: Path) -> bool:
    """Check whether *path* can be created and written to safely."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def get_data_dir() -> Path:
    """
    Resolve the writable directory for user state (`settings.json`, `reminders.json`, etc.).
    Priority:
      1. Explicit `TIMESPACE_DATA_DIR` environment override.
      2. Dev mode (`not is_frozen()`): `<repo>/data` (preserves existing dev data).
      3. Frozen portable override: sibling `<exe_dir>/data` if `portable.flag` or `<exe_dir>/data` exists and is writable.
      4. Frozen default: `%APPDATA%\\TimeSpace\\data` on Windows (`~/.local/share/TimeSpace/data` elsewhere).
    """
    env_override = os.environ.get("TIMESPACE_DATA_DIR", "").strip()
    if env_override:
        return Path(env_override).expanduser().resolve()

    if not is_frozen():
        return get_app_dir() / "data"

    app_dir = get_app_dir()
    portable_dir = app_dir / "data"
    if ((app_dir / "portable.flag").exists() or portable_dir.is_dir()) and _is_dir_writable(portable_dir):
        return portable_dir

    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "").strip()
        base = Path(appdata) if appdata else (Path.home() / "AppData" / "Roaming")
        return base / "TimeSpace" / "data"

    xdg_data = os.environ.get("XDG_DATA_HOME", "").strip()
    base = Path(xdg_data) if xdg_data else (Path.home() / ".local" / "share")
    return base / "TimeSpace" / "data"


def get_reports_dir() -> Path:
    """Return the writable export directory for diagnostic reports and scratchpad notes."""
    preferred = Path(r"C:\Temp") if sys.platform == "win32" else Path("/tmp")
    if _is_dir_writable(preferred):
        return preferred
    return get_data_dir() / "reports"
