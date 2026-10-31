"""Natural language parser for smart quick timer and rendez-vous input with expanded vocabulary."""
import re
import datetime
import time
from typing import Optional, Dict, Any, Tuple

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WEEKDAY_MAP = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

# Regex that matches "at HH:MM", "at 4pm", "at 9", "4:30pm", "18:30" etc.
_TIME_RE = re.compile(
    r"(?:\bat\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
    re.IGNORECASE,
)

_DURATION_UNIT_RE = re.compile(
    r"(\d+)\s*(days?|weeks?|h(?:ours?)?|m(?:in(?:ute)?s?)?|s(?:ec(?:ond)?s?)?)\b",
    re.IGNORECASE,
)


def _next_weekday(from_date: datetime.date, weekday: int) -> datetime.date:
    """Return the next occurrence of *weekday* (0=Monday … 6=Sunday) after *from_date*."""
    days_ahead = (weekday - from_date.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return from_date + datetime.timedelta(days=days_ahead)


def _parse_time_str(h: int, m: int, ampm: Optional[str], tod: Optional[str], is_tonight: bool) -> Optional[int]:
    """Resolve final 24-h hour from raw parsed components.  Returns None on invalid input."""
    if ampm:
        mer = ampm.lower()
        if mer == "pm" and h < 12:
            h += 12
        elif mer == "am" and h == 12:
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

    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None
    return h


# ---------------------------------------------------------------------------
# Main parser class
# ---------------------------------------------------------------------------

class NaturalParser:
    @staticmethod
    def parse(text: str) -> Optional[Dict[str, Any]]:
        """
        Parses rich freeform expressions including:
          Timer expressions
          - "Ring in 15 min"
          - "in 45m check laundry"
          - "Check oven in 25 mins"
          - "Timer for 30m meditation"
          - "Remind me in 10 minutes to call John"

          Relative-day rendez-vous (NEW / FIXED)
          - "Call Sam in 2 days"
          - "Call Sam in 2 days at 3pm"
          - "Doctor in 1 week"
          - "Doctor in 1 week at 10am"
          - "Dentist next Friday"
          - "Dentist next Friday at 14:00"
          - "Meeting on Wednesday at 3pm"

          Calendar / time rendez-vous
          - "RDV at 4PM"
          - "RDV tomorrow at 10am dentist"
          - "Call Linda at 7:15 tomorrow morning"
          - "at 18:30 dinner"
          - "at 8 tonight netflix"
          - "Dentist on 2026-11-05 at 14:00"

        Returns a dict or None if unrecognized.
        """
        raw = text.strip()
        if not raw:
            return None

        normalized = re.sub(r"[.!]+$", "", raw).strip()

        # ── 1. "remind me to <task> in <duration>" ──────────────────────────
        m = re.match(r"^remind\s+me\s+to\s+(.+?)\s+in\s+(\d+.+)$", normalized, re.IGNORECASE)
        if m:
            task = m.group(1).strip()
            secs = NaturalParser._parse_duration_seconds(m.group(2))
            if secs > 0:
                return NaturalParser._build_timer(task or "Reminder", secs)

        # ── 2. "remind me in <duration> [to/for] <task>" ───────────────────
        m = re.match(r"^remind\s+me\s+in\s+(\d+\w*.*)$", normalized, re.IGNORECASE)
        if m:
            result = NaturalParser._try_timer_from_in(m.group(1), "Reminder")
            if result:
                return result

        # ── 3. "ring/alarm/timer in/for <duration> [name]" ─────────────────
        m = re.match(r"^(?:ring|alarm|timer)\s+(?:in|for)\s+(\d+\w*.*)$", normalized, re.IGNORECASE)
        if m:
            result = NaturalParser._try_timer_from_in(m.group(1), "Alarm")
            if result:
                return result

        # ── 4. "in <duration> <task>" where duration is h/m/s only ─────────
        m = re.match(r"^in\s+(\d+\w*.*)$", normalized, re.IGNORECASE)
        if m:
            result = NaturalParser._try_timer_from_in(m.group(1), "Quick Timer")
            if result:
                return result

        # ── 5. "<task> in <N> days/weeks [at <time>]"  ─────────────────────
        #       Also handles "<task> in <N> h/m/s" (timer) as fallback
        rdv_days = NaturalParser._try_relative_days(normalized)
        if rdv_days:
            return rdv_days

        # ── 6. "<task> in <duration h/m/s>" ─────────────────────────────────
        m = re.match(
            r"^(.+?)\s+in\s+(\d+\s*(?:h|hr|hours?|m|min|mins|minutes?|s|sec|seconds?)(?:\s+and\s+\d+\s*(?:h|hr|hours?|m|min|mins|minutes?|s|sec|seconds?))*)$",
            normalized, re.IGNORECASE,
        )
        if m:
            secs = NaturalParser._parse_duration_seconds(m.group(2))
            if secs > 0:
                return NaturalParser._build_timer(m.group(1).strip(), secs)

        # ── 7. "next <weekday> [at <time>] <task>" ──────────────────────────
        next_wd = NaturalParser._try_next_weekday(normalized)
        if next_wd:
            return next_wd

        # ── 8. RDV / rendez-vous / appointment prefix ───────────────────────
        m = re.match(r"^(?:rdv|rendez-vous|appointment)\s+(.+)$", normalized, re.IGNORECASE)
        if m:
            result = NaturalParser._parse_appointment_phrase(m.group(1).strip(), "RDV")
            if result:
                return result

        # ── 9. General appointment phrase (today/tomorrow/at/tonight/weekday)─
        result = NaturalParser._parse_appointment_phrase(normalized, "Meeting")
        if result:
            return result

        return None

    # ── Duration helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _parse_duration_seconds(dur_str: str) -> int:
        """Extract total seconds from 'h/m/s' only duration string (days handled separately)."""
        total = 0
        for val_s, unit in _DURATION_UNIT_RE.findall(dur_str):
            u = unit.lower()
            if u.startswith("d") or u.startswith("w"):
                continue  # days/weeks not handled here
            val = int(val_s)
            if u.startswith("h"):
                total += val * 3600
            elif u.startswith("m"):
                total += val * 60
            elif u.startswith("s"):
                total += val
        return total

    @staticmethod
    def _try_timer_from_in(rest: str, default_name: str) -> Optional[Dict[str, Any]]:
        """Parse leading h/m/s duration from 'rest'; remainder is task name."""
        unit_re = re.compile(
            r"^(\d+)\s*(h(?:ours?)?|m(?:in(?:ute)?s?)?|s(?:ec(?:ond)?s?)?)\b",
            re.IGNORECASE,
        )
        total_sec = 0
        pos = 0
        temp = rest
        found = False

        while True:
            temp = temp.lstrip()
            um = unit_re.match(temp)
            if not um:
                am = re.match(r"^and\s+", temp, re.IGNORECASE)
                if am:
                    temp = temp[len(am.group(0)):]
                    continue
                break
            found = True
            val, unit = int(um.group(1)), um.group(2).lower()
            if unit.startswith("h"):
                total_sec += val * 3600
            elif unit.startswith("m"):
                total_sec += val * 60
            elif unit.startswith("s"):
                total_sec += val
            consumed = len(rest) - len(temp) + len(um.group(0))
            pos = consumed
            temp = temp[len(um.group(0)):]

        if found and total_sec > 0:
            name = rest[pos:].strip()
            name = re.sub(r"^(?:to|for)\s+", "", name, flags=re.IGNORECASE).strip()
            return NaturalParser._build_timer(name or default_name, total_sec)
        return None

    # ── Relative-day rendez-vous ─────────────────────────────────────────────

    @staticmethod
    def _try_relative_days(text: str) -> Optional[Dict[str, Any]]:
        """
        Handle patterns like:
          "<task> in <N> days [at <time>]"
          "<task> in <N> week[s] [at <time>]"
          "in <N> days [at <time>] [<task>]"
        """
        # Match: (optional leading task) "in N days/weeks" (optional "at time") (optional trailing task)
        pattern = re.compile(
            r"^(.*?)\bin\s+(\d+)\s+(days?|weeks?)\b(.*?)$",
            re.IGNORECASE,
        )
        m = pattern.match(text.strip())
        if not m:
            return None

        pre_task  = m.group(1).strip()   # text before "in N days"
        n         = int(m.group(2))
        unit      = m.group(3).lower()
        post_text = m.group(4).strip()   # text after "in N days"

        if unit.startswith("w"):
            n *= 7  # convert weeks to days

        # Calculate base target date
        now       = datetime.datetime.now()
        base_date = now.date() + datetime.timedelta(days=n)

        # Try to extract an explicit time from the post-text (e.g. "at 3pm", "at 10:30")
        h_out, min_out = None, None
        if post_text:
            tod_m = re.search(r"\b(morning|afternoon|evening|night)\b", post_text, re.IGNORECASE)
            tod   = tod_m.group(1).lower() if tod_m else None

            for tm in _TIME_RE.finditer(post_text):
                h_raw  = int(tm.group(1))
                mi_raw = int(tm.group(2) or 0)
                ampm   = tm.group(3)
                # Guard: require 'at' or ampm or tod or HH:MM for unambiguous times
                had_at = "at" in post_text[max(0, tm.start() - 4):tm.start() + 3].lower()
                if not ampm and tm.group(2) is None and not had_at and not tod:
                    continue
                resolved = _parse_time_str(h_raw, mi_raw, ampm, tod, False)
                if resolved is not None:
                    h_out, min_out = resolved, mi_raw
                    break

        # Default time: noon if no explicit time given
        if h_out is None:
            h_out, min_out = 12, 0

        # Build task name from pre + post (minus the time part)
        post_clean = post_text
        if h_out is not None:
            post_clean = _TIME_RE.sub("", post_clean)
            post_clean = re.sub(r"\bat\b", "", post_clean, flags=re.IGNORECASE)
            post_clean = re.sub(r"\b(morning|afternoon|evening|night)\b", "", post_clean, flags=re.IGNORECASE)
        name_parts = " ".join(filter(None, [pre_task, post_clean.strip()]))
        name_parts = re.sub(r"\b(rdv|appointment|rendez-vous)\b", "", name_parts, flags=re.IGNORECASE)
        name_parts = " ".join(name_parts.split()).strip()
        final_name = name_parts or f"In {n} day{'s' if n != 1 else ''}"

        target_dt = datetime.datetime.combine(base_date, datetime.time(h_out, min_out))
        delta     = (target_dt - now).total_seconds()

        day_label = target_dt.strftime("%b %d")
        return {
            "kind": "rendez-vous",
            "name": final_name,
            "seconds_from_now": max(0.0, delta),
            "target_dt": target_dt,
            "display_str": f"Rendez-vous: '{final_name}' on {day_label} at {h_out:02d}:{min_out:02d}",
        }

    # ── Next-weekday handler ─────────────────────────────────────────────────

    @staticmethod
    def _try_next_weekday(text: str) -> Optional[Dict[str, Any]]:
        """
        Handle: "next <weekday> [at <time>] [<task>]"
                "<task> next <weekday> [at <time>]"
                "<task> on <weekday> at <time>"
                "on <weekday> at <time> <task>"
        """
        wd_pattern = "|".join(_WEEKDAY_MAP.keys())
        # "next <weekday>" pattern
        m = re.search(
            rf"\b(?:next|on)\s+({wd_pattern})\b",
            text, re.IGNORECASE,
        )
        if not m:
            return None

        wd_str   = m.group(1).lower()
        weekday  = _WEEKDAY_MAP[wd_str]
        now      = datetime.datetime.now()
        base_date = _next_weekday(now.date(), weekday)

        # Strip the "next/on <weekday>" part and look for time + task in remaining
        remaining = (text[:m.start()] + " " + text[m.end():]).strip()

        # Detect time-of-day modifier
        tod_m = re.search(r"\b(morning|afternoon|evening|night)\b", remaining, re.IGNORECASE)
        tod   = tod_m.group(1).lower() if tod_m else None

        h_out, min_out = 12, 0  # default noon
        for tm in _TIME_RE.finditer(remaining):
            h_raw  = int(tm.group(1))
            mi_raw = int(tm.group(2) or 0)
            ampm   = tm.group(3)
            had_at = "at" in remaining[max(0, tm.start() - 4):tm.start() + 3].lower()
            if not ampm and tm.group(2) is None and not had_at and not tod:
                continue
            resolved = _parse_time_str(h_raw, mi_raw, ampm, tod, False)
            if resolved is not None:
                h_out, min_out = resolved, mi_raw
                # Remove matched time from remaining
                remaining = (remaining[:tm.start()] + " " + remaining[tm.end():]).strip()
                break

        # Clean remaining into task name
        if tod:
            remaining = re.sub(rf"\b{tod}\b", "", remaining, flags=re.IGNORECASE)
        remaining = re.sub(r"\bat\b", "", remaining, flags=re.IGNORECASE)
        remaining = re.sub(r"\b(rdv|appointment|rendez-vous)\b", "", remaining, flags=re.IGNORECASE)
        final_name = " ".join(remaining.split()).strip() or f"{wd_str.capitalize()} meeting"

        target_dt = datetime.datetime.combine(base_date, datetime.time(h_out, min_out))
        delta     = (target_dt - now).total_seconds()
        day_label = target_dt.strftime("%A %b %d")

        return {
            "kind": "rendez-vous",
            "name": final_name,
            "seconds_from_now": max(0.0, delta),
            "target_dt": target_dt,
            "display_str": f"Rendez-vous: '{final_name}' on {day_label} at {h_out:02d}:{min_out:02d}",
        }

    # ── Appointment phrase (today/tomorrow/tonight + explicit time) ──────────

    @staticmethod
    def _parse_appointment_phrase(phrase: str, default_name: str = "Appointment") -> Optional[Dict[str, Any]]:
        """
        Parses:
          - "Call Linda at 7:15 tomorrow morning"
          - "RDV at 4PM"
          - "at 18:30 dinner"
          - "tomorrow 3pm dentist"
          - "at 8 tonight party"
          - "team sync tomorrow at 10:30am"
        """
        text = phrase.strip()

        is_tomorrow = bool(re.search(r"\btomorrow\b", text, re.IGNORECASE))
        is_tonight  = bool(re.search(r"\btonight\b",  text, re.IGNORECASE))

        tod_m = re.search(r"\b(morning|afternoon|evening|night)\b", text, re.IGNORECASE)
        tod   = tod_m.group(1).lower() if tod_m else None

        clean = re.sub(r"\b(tomorrow|today|tonight)\b", " ", text, flags=re.IGNORECASE)
        if tod:
            clean = re.sub(rf"\b{tod}\b", " ", clean, flags=re.IGNORECASE)

        for match in _TIME_RE.finditer(clean):
            h_raw  = int(match.group(1))
            mi_raw = int(match.group(2) or 0)
            ampm   = match.group(3)

            had_at = "at" in clean[max(0, match.start() - 4):match.start() + 3].lower()
            # Strict guard: require 'at', ampm, tod, minutes, or tonight to accept time
            if not ampm and match.group(2) is None and not had_at and not tod and not is_tonight:
                continue
            # Extra guard: bare single digit with no context is likely not a time
            if not ampm and not had_at and not tod and not is_tonight and h_raw <= 6:
                continue

            resolved = _parse_time_str(h_raw, mi_raw, ampm, tod, is_tonight)
            if resolved is None:
                continue
            h_out = resolved

            name_part = (clean[:match.start()] + " " + clean[match.end():]).strip()
            name_part = re.sub(r"\b(?:at|on|for|with)\b", " ", name_part, flags=re.IGNORECASE)
            name_part = " ".join(name_part.split()).strip()
            final_name = name_part or default_name

            now         = datetime.datetime.now()
            target_date = now.date()

            if is_tomorrow:
                target_date += datetime.timedelta(days=1)
            else:
                cand_dt = datetime.datetime.combine(target_date, datetime.time(h_out, mi_raw))
                if cand_dt <= now and not is_tonight:
                    target_date += datetime.timedelta(days=1)

            target_dt = datetime.datetime.combine(target_date, datetime.time(h_out, mi_raw))
            delta     = (target_dt - now).total_seconds()
            day_str   = "Tomorrow" if target_dt.date() == (now.date() + datetime.timedelta(days=1)) else "Today"

            return {
                "kind": "rendez-vous",
                "name": final_name,
                "seconds_from_now": max(0.0, delta),
                "target_dt": target_dt,
                "display_str": f"Rendez-vous: '{final_name}' on {day_str} at {h_out:02d}:{mi_raw:02d}",
            }

        return None

    # ── Shared builder ───────────────────────────────────────────────────────

    @staticmethod
    def _build_timer(name: str, total_seconds: int) -> Dict[str, Any]:
        return {
            "kind": "timer",
            "name": name,
            "seconds_from_now": float(total_seconds),
            "original_duration": float(total_seconds),
            "display_str": f"Timer: '{name}' in {datetime.timedelta(seconds=total_seconds)}",
        }
