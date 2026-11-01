"""Windows 10/11 Action Center native toast notifications and OS link/path launcher."""
import os
import re
import sys
import subprocess
import threading
import webbrowser
from src.config import APP_TITLE


def normalize_link_target(raw_link: str) -> str:
    """Normalize a web URL, bare domain, custom URI scheme, or local Windows file/folder path."""
    if not raw_link:
        return ""
    cleaned = raw_link.strip().strip('"').strip("'")
    if not cleaned:
        return ""

    expanded = os.path.expandvars(os.path.expanduser(cleaned))
    if (
        re.match(r"^[a-zA-Z]:[\\/]", expanded)
        or expanded.startswith("\\\\")
        or os.path.exists(expanded)
    ):
        return expanded

    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", cleaned):
        return cleaned

    return f"https://{cleaned}"


def open_attachment_link(raw_link: str) -> bool:
    """Safely launch an attached URL, custom protocol URI, or local Windows file/folder."""
    target = normalize_link_target(raw_link)
    if not target:
        return False

    is_win_path = bool(re.match(r"^[a-zA-Z]:[\\/]", target) or target.startswith("\\\\"))
    if is_win_path and not os.path.exists(target):
        return False

    if sys.platform == "win32" and hasattr(os, "startfile"):
        try:
            os.startfile(target)  # type: ignore[attr-defined]
            return True
        except OSError:
            if is_win_path:
                return False

    try:
        return bool(webbrowser.open(target))
    except Exception:
        return False


def show_toast(title: str, message: str) -> None:
    """Deliver a native Windows Action Center toast notification in a background thread."""
    if sys.platform != "win32":
        return
    threading.Thread(target=_send_toast_worker, args=(title, message), daemon=True).start()


def _send_toast_worker(title: str, message: str) -> None:
    try:
        import win11toast
        win11toast.toast(title, message, app_id=APP_TITLE)
        return
    except Exception:
        pass

    clean_title = title.replace('"', '`"').replace("'", "''")
    clean_msg = message.replace('"', '`"').replace("'", "''")

    ps_script = f"""
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
    $template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
    $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
    $text = $xml.GetElementsByTagName('text')
    $text[0].AppendChild($xml.CreateTextNode('{clean_title}')) > $null
    $text[1].AppendChild($xml.CreateTextNode('{clean_msg}')) > $null
    $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{APP_TITLE}').Show($toast)
    """

    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
            timeout=5,
        )
    except Exception:
        pass
