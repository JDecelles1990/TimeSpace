"""Natural language parser for smart quick timer and rendez-vous input with expanded vocabulary."""
import re
import datetime
import time
from typing import Optional, Dict, Any, Tuple

class NaturalParser:
    @staticmethod
    def parse(text: str) -> Optional[Dict[str, Any]]:
        """
        Parses rich freeform expressions including:
          - "Ring in 15 min"
          - "in 45m check laundry"
          - "Check oven in 25 mins"
          - "Timer for 30m meditation"
          - "Remind me in 10 minutes to call John"
          - "RDV at 4PM"
          - "RDV tomorrow at 10am dentist"
          - "Call Linda at 7:15 tomorrow morning"
          - "Meeting with Bob tomorrow at 3:30pm"
          - "at 18:30 dinner"
          - "at 8 tonight netflix"
          - "Dentist on 2026-11-05 at 14:00"

        Returns:
          {
            "kind": "timer" | "rendez-vous",
            "name": str,
            "seconds_from_now": float,
            "original_duration": float (if timer),
            "target_dt": datetime.datetime (if rendez-vous),
            "display_str": str
          }
          or None if unrecognized.
        """
        raw = text.strip()
        if not raw:
            return None

        # Clean common polite / command prefixes
        normalized = raw
        # Remove trailing punctuation like period or exclamation mark
        normalized = re.sub(r"[.!]+$", "", normalized).strip()

        # Check for "remind me to <task> in <duration>"
        match_remind_to_in = re.match(r"^remind\s+me\s+to\s+(.+?)\s+in\s+(\d+.+)$", normalized, re.IGNORECASE)
        if match_remind_to_in:
            task_name = match_remind_to_in.group(1).strip()
            duration_str = match_remind_to_in.group(2).strip()
            total_sec = NaturalParser._parse_duration(duration_str)
            if total_sec > 0:
                return NaturalParser._build_timer_result(task_name or "Reminder", total_sec)

        # Check for "remind me in <duration> [to/for] <task>"
        match_remind_in = re.match(r"^remind\s+me\s+in\s+(\d+\w*.*)$", normalized, re.IGNORECASE)
        if match_remind_in:
            return NaturalParser._parse_in_pattern(match_remind_in.group(1), default_name="Reminder")

        # Check for "ring in <duration> [name]" or "alarm in <duration> [name]"
        match_ring = re.match(r"^(?:ring|alarm|timer)\s+(?:in|for)\s+(\d+\w*.*)$", normalized, re.IGNORECASE)
        if match_ring:
            return NaturalParser._parse_in_pattern(match_ring.group(1), default_name="Alarm")

        # Check for standard "in <duration> <task>"
        match_in = re.match(r"^in\s+(\d+\w*.*)$", normalized, re.IGNORECASE)
        if match_in:
            return NaturalParser._parse_in_pattern(match_in.group(1), default_name="Quick Timer")

        # Check for "<task> in <duration>" (e.g. "Check laundry in 45 min", "Call mom in 2 hours")
        match_task_in = re.match(r"^(.+?)\s+in\s+(\d+\s*(?:h|hr|hours?|m|min|mins|minutes?|s|sec|seconds?)(?:\s+and\s+\d+\s*(?:h|hr|hours?|m|min|mins|minutes?|s|sec|seconds?))*)$", normalized, re.IGNORECASE)
        if match_task_in:
            task_name = match_task_in.group(1).strip()
            duration_str = match_task_in.group(2).strip()
            total_sec = NaturalParser._parse_duration(duration_str)
            if total_sec > 0:
                return NaturalParser._build_timer_result(task_name, total_sec)

        # -------------------------------------------------------------
        # Calendar / Rendez-vous expressions
        # -------------------------------------------------------------

        # Check for "RDV at <time>" or "RDV tomorrow <time>" or "RDV <time>"
        match_rdv = re.match(r"^(?:rdv|rendez-vous|appointment)\s+(.+)$", normalized, re.IGNORECASE)
        if match_rdv:
            rest = match_rdv.group(1).strip()
            # If rest starts with "at", "tomorrow", "today", or direct time
            parsed_rdv = NaturalParser._parse_appointment_phrase(rest, default_name="RDV")
            if parsed_rdv:
                return parsed_rdv

        # Check for phrases with "tomorrow" or "today" or "tonight"
        # e.g. "Call Linda at 7:15 tomorrow morning", "Tomorrow 3pm dentist", "at 8 tonight netflix"
        parsed_appt = NaturalParser._parse_appointment_phrase(normalized, default_name="Meeting")
        if parsed_appt:
            return parsed_appt

        return None

    @staticmethod
    def _parse_duration(dur_str: str) -> int:
        """Extracts total seconds from duration string like '15 min', '1h 30m', '45m and 20s'."""
        unit_pattern = re.compile(
            r"(\d+)\s*(h(?:ours?)?|m(?:in(?:ute)?s?)?|s(?:ec(?:ond)?s?)?)\b",
            re.IGNORECASE
        )
        total_seconds = 0
        matches = unit_pattern.findall(dur_str)
        for val_str, unit in matches:
            val = int(val_str)
            u = unit.lower()
            if u.startswith("h"):
                total_seconds += val * 3600
            elif u.startswith("m"):
                total_seconds += val * 60
            elif u.startswith("s"):
                total_seconds += val
        return total_seconds

    @staticmethod
    def _parse_in_pattern(rest: str, default_name: str) -> Optional[Dict[str, Any]]:
        """Parses duration from front of rest string, and remaining is task name."""
        unit_pattern = re.compile(
            r"^(\d+)\s*(h(?:ours?)?|m(?:in(?:ute)?s?)?|s(?:ec(?:ond)?s?)?)\b",
            re.IGNORECASE
        )
        total_seconds = 0
        consumed_chars = 0
        temp_rest = rest
        found_unit = False

        while True:
            temp_rest = temp_rest.lstrip()
            unit_match = unit_pattern.match(temp_rest)
            if not unit_match:
                # Check for "and" separator between duration units (e.g. "1h and 30m")
                match_and = re.match(r"^and\s+", temp_rest, re.IGNORECASE)
                if match_and:
                    matched_and_len = len(match_and.group(0))
                    consumed_chars += (len(rest[consumed_chars:]) - len(temp_rest)) + matched_and_len
                    temp_rest = temp_rest[matched_and_len:]
                    continue
                break

            found_unit = True
            val = int(unit_match.group(1))
            unit = unit_match.group(2).lower()

            if unit.startswith("h"):
                total_seconds += val * 3600
            elif unit.startswith("m"):
                total_seconds += val * 60
            elif unit.startswith("s"):
                total_seconds += val

            matched_len = len(unit_match.group(0))
            consumed_chars += (len(rest[consumed_chars:]) - len(temp_rest)) + matched_len
            temp_rest = temp_rest[matched_len:]

        if found_unit and total_seconds > 0:
            name = rest[consumed_chars:].strip()
            name = re.sub(r"^(?:to|for)\s+", "", name, flags=re.IGNORECASE).strip()
            return NaturalParser._build_timer_result(name or default_name, total_seconds)

        return None

    @staticmethod
    def _build_timer_result(name: str, total_seconds: int) -> Dict[str, Any]:
        return {
            "kind": "timer",
            "name": name,
            "seconds_from_now": float(total_seconds),
            "original_duration": float(total_seconds),
            "display_str": f"Timer: '{name}' in {datetime.timedelta(seconds=total_seconds)}"
        }

    @staticmethod
    def _parse_appointment_phrase(phrase: str, default_name: str = "Appointment") -> Optional[Dict[str, Any]]:
        """
        Parses complex appointment sentences:
          - "Call Linda at 7:15 tomorrow morning"
          - "RDV at 4PM"
          - "at 18:30 dinner"
          - "tomorrow 3pm dentist"
          - "at 8 tonight party"
          - "team sync tomorrow at 10:30am"
        """
        text = phrase.strip()

        # Detect relative day: "tomorrow", "tonight", "today"
        is_tomorrow = bool(re.search(r"\btomorrow\b", text, re.IGNORECASE))
        is_tonight = bool(re.search(r"\btonight\b", text, re.IGNORECASE))

        # Detect time-of-day modifier: "morning", "afternoon", "evening", "night"
        tod_match = re.search(r"\b(morning|afternoon|evening|night)\b", text, re.IGNORECASE)
        tod = tod_match.group(1).lower() if tod_match else None

        # Clean day / tod keywords out when extracting task name later
        clean_target = re.sub(r"\b(tomorrow|today|tonight)\b", " ", text, flags=re.IGNORECASE)
        if tod:
            clean_target = re.sub(rf"\b{tod}\b", " ", clean_target, flags=re.IGNORECASE)

        # Find time pattern: e.g. "at 7:15", "at 4PM", "4:30 pm", "18:30", "at 9"
        # Match time with optional 'at' prefix
        time_regex = re.compile(
            r"(?:\bat\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
            re.IGNORECASE
        )

        for match in time_regex.finditer(clean_target):
            h_str, m_str, ampm = match.group(1), match.group(2), match.group(3)
            h = int(h_str)
            m = int(m_str or 0)

            if not (0 <= h <= 24 and 0 <= m <= 59):
                continue

            # If no AM/PM and no minutes and h <= 12 and no 'at', skip stray numbers unless preceded by 'at' or accompanied by tod
            had_at = "at" in clean_target[max(0, match.start() - 4):match.start() + 3].lower()
            if not ampm and m_str is None and not had_at and not tod and not is_tonight:
                continue

            # Resolve AM/PM based on explicit meridiem or time-of-day modifier
            if ampm:
                meridiem = ampm.lower()
                if meridiem == "pm" and h < 12:
                    h += 12
                elif meridiem == "am" and h == 12:
                    h = 0
            elif tod:
                if tod == "morning":
                    if h == 12:
                        h = 0
                elif tod in ("afternoon", "evening", "night"):
                    if h < 12:
                        h += 12
            elif is_tonight:
                if h < 12:
                    h += 12

            if not (0 <= h <= 23):
                continue

            # Task name is the remaining text outside the matched time
            name_part = (clean_target[:match.start()] + " " + clean_target[match.end():]).strip()
            # Clean lingering prepositions
            name_part = re.sub(r"\b(?:at|on|for|with)\b", " ", name_part, flags=re.IGNORECASE)
            name_part = " ".join(name_part.split()).strip()

            final_name = name_part or default_name

            # Calculate target datetime
            now = datetime.datetime.now()
            target_date = now.date()

            if is_tomorrow:
                target_date += datetime.timedelta(days=1)
            else:
                # If scheduling for today and the time has already passed, bump to tomorrow
                cand_dt = datetime.datetime.combine(target_date, datetime.time(h, m))
                if cand_dt <= now and not is_tonight:
                    target_date += datetime.timedelta(days=1)

            target_dt = datetime.datetime.combine(target_date, datetime.time(h, m))
            delta = (target_dt - now).total_seconds()
            day_str = "Tomorrow" if target_dt.date() == (now.date() + datetime.timedelta(days=1)) else "Today"

            return {
                "kind": "rendez-vous",
                "name": final_name,
                "seconds_from_now": max(0.0, delta),
                "target_dt": target_dt,
                "display_str": f"Rendez-vous: '{final_name}' on {day_str} at {h:02d}:{m:02d}"
            }

        return None
