"""iCalendar (.ics) import and export generator complying with RFC 5545."""
import re
import datetime
import uuid
from typing import List, Dict, Any

class CalendarManager:
    @staticmethod
    def export_to_ics(rendez_vous_items: List[Dict[str, Any]], filepath: str) -> bool:
        """Export a list of rendez-vous items to an .ics file."""
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Timer and Rendez-vous App//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH"
        ]

        now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        for item in rendez_vous_items:
            dt = datetime.datetime.fromtimestamp(item["target_time"])
            dt_str = dt.strftime("%Y%m%dT%H%M%S")
            # Default 30 min duration for calendar representation
            dt_end = dt + datetime.timedelta(minutes=30)
            dt_end_str = dt_end.strftime("%Y%m%dT%H%M%S")

            uid = item.get("id") or str(uuid.uuid4())
            name = item.get("name", "Meeting").replace(",", "\\,").replace(";", "\\;")
            repeat = item.get("repeat_rule", "none").lower()

            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{uid}")
            lines.append(f"DTSTAMP:{now_utc}")
            lines.append(f"DTSTART:{dt_str}")
            lines.append(f"DTEND:{dt_end_str}")
            lines.append(f"SUMMARY:{name}")

            if repeat == "daily":
                lines.append("RRULE:FREQ=DAILY")
            elif repeat == "weekly":
                lines.append("RRULE:FREQ=WEEKLY")
            elif repeat == "monthly":
                lines.append("RRULE:FREQ=MONTHLY")

            lines.append("STATUS:CONFIRMED")
            lines.append("END:VEVENT")

        lines.append("END:VCALENDAR")
        lines.append("")

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\r\n".join(lines))
            return True
        except Exception as e:
            print(f"Error exporting ICS: {e}")
            return False

    @staticmethod
    def import_from_ics(filepath: str) -> List[Dict[str, Any]]:
        """Parse events from an .ics file into rendez-vous dictionary items."""
        events = []
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return []

        # Find all VEVENT blocks
        vevent_blocks = re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", content, re.DOTALL)
        for block in vevent_blocks:
            summary_match = re.search(r"SUMMARY:(.*)", block)
            dtstart_match = re.search(r"DTSTART(?:;[^:]+)?:(\d{8}T\d{6})", block)
            rrule_match = re.search(r"RRULE:.*FREQ=(DAILY|WEEKLY|MONTHLY)", block, re.IGNORECASE)

            if dtstart_match:
                dt_str = dtstart_match.group(1)
                try:
                    dt = datetime.datetime.strptime(dt_str, "%Y%m%dT%H%M%S")
                    summary = summary_match.group(1).strip() if summary_match else "Imported Event"
                    summary = summary.replace("\\,", ",").replace("\\;", ";")
                    repeat = rrule_match.group(1).lower() if rrule_match else "none"

                    events.append({
                        "id": str(uuid.uuid4()),
                        "kind": "rendez-vous",
                        "name": summary,
                        "target_time": dt.timestamp(),
                        "repeat_rule": repeat,
                        "repeat_sec": 0
                    })
                except Exception:
                    continue

        return events

