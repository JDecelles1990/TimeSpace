"""iCalendar (.ics) import and export generator complying with RFC 5545."""
import re
import datetime
import uuid
from typing import List, Dict, Any

class CalendarManager:
    @staticmethod
    def _escape_ics_text(text: str) -> str:
        return (
            text.replace("\\", "\\\\")
            .replace("\r\n", "\\n")
            .replace("\n", "\\n")
            .replace(",", "\\,")
            .replace(";", "\\;")
        )

    @staticmethod
    def _unescape_ics_text(text: str) -> str:
        return (
            text.replace("\\n", "\n")
            .replace("\\N", "\n")
            .replace("\\,", ",")
            .replace("\\;", ";")
            .replace("\\\\", "\\")
        )

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
            lead_sec = max(0, int(item.get("lead_time_min", 0) or 0)) * 60
            dt = datetime.datetime.fromtimestamp(float(item["target_time"]) + lead_sec)
            dt_str = dt.strftime("%Y%m%dT%H%M%S")
            # Default 30 min duration for calendar representation
            dt_end = dt + datetime.timedelta(minutes=30)
            dt_end_str = dt_end.strftime("%Y%m%dT%H%M%S")

            uid = item.get("id") or str(uuid.uuid4())
            name = CalendarManager._escape_ics_text(str(item.get("name", "Meeting")))
            note = str(item.get("note", "") or "").strip()
            url = str(item.get("url", "") or "").strip()
            repeat = str(item.get("repeat_rule", "none") or "none").lower()

            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{uid}")
            lines.append(f"DTSTAMP:{now_utc}")
            lines.append(f"DTSTART:{dt_str}")
            lines.append(f"DTEND:{dt_end_str}")
            lines.append(f"SUMMARY:{name}")
            if note:
                lines.append(f"DESCRIPTION:{CalendarManager._escape_ics_text(note)}")
            if url:
                lines.append(f"URL:{url}")

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
            with open(filepath, "w", encoding="utf-8", newline="") as f:
                f.write("\r\n".join(lines))
            return True
        except Exception as e:
            print(f"Error exporting ICS: {e}")
            return False

    @staticmethod
    def import_from_ics(filepath: str) -> List[Dict[str, Any]]:
        """Parse events from an .ics file into rendez-vous dictionary items."""
        events: List[Dict[str, Any]] = []
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                raw_content = f.read()
        except Exception:
            return []

        # RFC 5545 line unfolding: join continuation lines starting with space or tab
        content = re.sub(r"\r?\n[ \t]", "", raw_content)

        # Find all VEVENT blocks
        vevent_blocks = re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", content, re.DOTALL)
        for block in vevent_blocks:
            summary_match = re.search(r"^SUMMARY(?:;[^:]*)?:(.*)$", block, re.MULTILINE)
            dtstart_match = re.search(r"^DTSTART(?:;[^:]*)?:(\d{8}T\d{6})", block, re.MULTILINE)
            rrule_match = re.search(r"^RRULE:.*FREQ=(DAILY|WEEKLY|MONTHLY)", block, re.IGNORECASE | re.MULTILINE)
            url_match = re.search(r"^URL(?:;[^:]*)?:(.*)$", block, re.MULTILINE)
            desc_match = re.search(r"^DESCRIPTION(?:;[^:]*)?:(.*)$", block, re.MULTILINE)

            if dtstart_match:
                dt_str = dtstart_match.group(1)
                try:
                    dt = datetime.datetime.strptime(dt_str, "%Y%m%dT%H%M%S")
                    summary = (
                        CalendarManager._unescape_ics_text(summary_match.group(1).strip())
                        if summary_match
                        else "Imported Event"
                    )
                    repeat = rrule_match.group(1).lower() if rrule_match else "none"
                    url = url_match.group(1).strip() if url_match else ""
                    note = (
                        CalendarManager._unescape_ics_text(desc_match.group(1).strip())
                        if desc_match
                        else ""
                    )

                    # If no explicit URL property, extract embedded https:// meeting link from DESCRIPTION
                    if not url and note:
                        embedded_url = re.search(r"https?://[^\s<>\"']+", note)
                        if embedded_url:
                            url = embedded_url.group(0).rstrip(".,;)")

                    # Keep imported note single-line/compact for clean UI display
                    compact_note = " ".join(note.splitlines()).strip()
                    if len(compact_note) > 200:
                        compact_note = compact_note[:197] + "..."

                    events.append({
                        "id": str(uuid.uuid4()),
                        "kind": "rendez-vous",
                        "name": summary,
                        "target_time": dt.timestamp(),
                        "repeat_rule": repeat,
                        "repeat_sec": 0,
                        "url": url,
                        "note": compact_note,
                    })
                except Exception:
                    continue

        return events

