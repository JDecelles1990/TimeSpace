"""Windows 10/11 Action Center native toast notifications."""
import sys
import subprocess
import threading

def show_toast(title: str, message: str):
    """Deliver a native Windows Action Center toast notification in a background thread."""
    if sys.platform != "win32":
        return
    threading.Thread(target=_send_toast_worker, args=(title, message), daemon=True).start()

def _send_toast_worker(title: str, message: str):
    try:
        # Try win11toast if installed
        import win11toast
        win11toast.toast(title, message, app_id="Timer & Rendez-vous")
        return
    except Exception:
        pass

    # Standard Windows PowerShell toast fallback (0 external libraries required)
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
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Timer & Rendez-vous').Show($toast)
    """

    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
            timeout=5
        )
    except Exception:
        pass

