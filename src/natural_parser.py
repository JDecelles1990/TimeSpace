"""Natural language parser for smart quick timer and rendez-vous input with expanded vocabulary."""
import calendar
import datetime
import re
from typing import Any, Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# Helpers & Lookup Tables
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

_MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

_MONTH_PATTERN = "|".join(sorted(_MONTH_MAP.keys(), key=len, reverse=True))
_WEEKDAY_PATTERN = "|".join(sorted(_WEEKDAY_MAP.keys(), key=len, reverse=True))

# Matches "at HH:MM", "at2:15 PM", "@ 3pm", "14h30", "9h", "4:30pm", "18:30", etc.
_TIME_RE = re.compile(
    r"(?:(?:\bat(?:\s+|(?=\d))|@\s*))?"
    r"(\d{1,2})"
    r"(?:(?::(\d{2}))|(h(\d{2})?))?"
    r"\s*(am|pm)?\b",
    re.IGNORECASE,
)

_DURATION_UNIT_RE = re.compile(
    r"(\d+)\s*(days?|weeks?|h(?:ours?)?|m(?:in(?:ute)?s?)?|s(?:ec(?:ond)?s?)?)\b",
    re.IGNORECASE,
)

_COMPOUND_UNIT_RE = re.compile(
    r"^(\d+)\s*(weeks?|wks?|w|days?|d|hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s)\b",
    re.IGNORECASE,
)

_COMPOUND_CONNECTOR_RE = re.compile(
    r"^(?:\s*,\s*and\s+|\s+and\s+|\s*,\s*|\s*\+\s*|\s+)",
    re.IGNORECASE,
)

_CONVERSATIONAL_PREFIXES = (
    (re.compile(r"^(?:create|add|set)\s+(?:an?\s+|the\s+)?alarm(?:\s+(?:for|on|to))?\s+", re.IGNORECASE), "Alarm"),
    (re.compile(r"^(?:create|add|set)\s+(?:an?\s+|the\s+)?reminder(?:\s+(?:for|on|to))?\s+", re.IGNORECASE), "Reminder"),
    (re.compile(r"^(?:create|add|set)\s+(?:an?\s+|the\s+)?timer(?:\s+(?:for|on|to))?\s+", re.IGNORECASE), "Quick Timer"),
    (re.compile(r"^remind\s+me(?:\s+(?:on|for|to))?\s+", re.IGNORECASE), "Reminder"),
    (re.compile(r"^schedule\s+(?:an?\s+)?(?:(meeting|rdv|rendez-vous|appointment|call|alarm|reminder)\s+)?(?:(?:for|on|to)\s+)?", re.IGNORECASE), "Meeting"),
    (re.compile(r"^wake\s+me\s+up(?:\s+(?:on|for))?\s+", re.IGNORECASE), "Wake Up Alarm"),
)


def _next_weekday(from_date: datetime.date, weekday: int) -> datetime.date:
    """Return the next occurrence of *weekday* (0=Monday … 6=Sunday) strictly after *from_date*."""
    days_ahead = (weekday - from_date.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return from_date + datetime.timedelta(days=days_ahead)


def _next_weekday_and_day(
    now: datetime.datetime,
    weekday: int,
    day_num: int,
    hour: int,
    minute: int,
) -> Optional[datetime.date]:
    """Return the next date matching both *weekday* and calendar *day_num* strictly in the future."""
    if not (1 <= day_num <= 31):
        return None
    start = now.date()
    days_to_wd = (weekday - start.weekday()) % 7
    cand = start + datetime.timedelta(days=days_to_wd)
    for _ in range(520):  # ~10 years of weekly steps
        if cand.day == day_num:
            cand_dt = datetime.datetime.combine(cand, datetime.time(hour, minute))
            if cand_dt > now:
                return cand
        cand += datetime.timedelta(days=7)
    return None


def _next_day_of_month(
    now: datetime.datetime,
    day_num: int,
    hour: int,
    minute: int,
) -> Optional[datetime.date]:
    """Return the next upcoming date whose calendar day is *day_num* strictly in the future."""
    if not (1 <= day_num <= 31):
        return None
    year, month = now.year, now.month
    for _ in range(48):  # up to 4 years (handles the 29th of Feb, 31st, etc.)
        max_day = calendar.monthrange(year, month)[1]
        if day_num <= max_day:
            cand = datetime.date(year, month, day_num)
            cand_dt = datetime.datetime.combine(cand, datetime.time(hour, minute))
            if cand_dt > now:
                return cand
        month += 1
        if month > 12:
            month = 1
            year += 1
    return None


def _parse_time_str(h: int, m: int, ampm: Optional[str], tod: Optional[str], is_tonight: bool) -> Optional[int]:
    """Resolve final 24-h hour from raw parsed components.  Returns None on invalid input."""
    if ampm:
        if h == 0 or h > 12:
            return None
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


def _normalize_natural_idioms(text: str) -> str:
    """Normalize friendly idioms like 'half an hour', 'an hour', 'a day', and 'day after tomorrow'."""
    out = re.sub(r"\b(?:the\s+)?day\s+after\s+tomorrow\b", "in 2 days", text, flags=re.IGNORECASE)
    out = re.sub(r"\b(in|for|and)\s+(?:half\s+an\s+hour|a\s+half\s+hour)\b", r"\1 30 minutes", out, flags=re.IGNORECASE)
    out = re.sub(r"([,+])\s*(?:half\s+an\s+hour|a\s+half\s+hour)\b", r"\1 30 minutes", out, flags=re.IGNORECASE)
    out = re.sub(r"\b(in|for|and)\s+an?\s+hour\b", r"\1 1 hour", out, flags=re.IGNORECASE)
    out = re.sub(r"([,+])\s*an?\s+hour\b", r"\1 1 hour", out, flags=re.IGNORECASE)
    out = re.sub(r"\b(in|for|and)\s+a\s+minute\b", r"\1 1 minute", out, flags=re.IGNORECASE)
    out = re.sub(r"([,+])\s*a\s+minute\b", r"\1 1 minute", out, flags=re.IGNORECASE)
    out = re.sub(r"\b(in|for|and)\s+a\s+second\b", r"\1 1 second", out, flags=re.IGNORECASE)
    out = re.sub(r"([,+])\s*a\s+second\b", r"\1 1 second", out, flags=re.IGNORECASE)
    out = re.sub(r"\b(in|for|and)\s+a\s+day\b", r"\1 1 day", out, flags=re.IGNORECASE)
    out = re.sub(r"([,+])\s*a\s+day\b", r"\1 1 day", out, flags=re.IGNORECASE)
    out = re.sub(r"\b(in|for|and)\s+a\s+week\b", r"\1 1 week", out, flags=re.IGNORECASE)
    out = re.sub(r"([,+])\s*a\s+week\b", r"\1 1 week", out, flags=re.IGNORECASE)
    return " ".join(out.split())


def _strip_conversational_prefix(text: str) -> Tuple[str, Optional[str]]:
    """Strip leading scheduling verbs ('Set an alarm for...', 'Remind me on...') and infer a default label."""
    for regex, default_label in _CONVERSATIONAL_PREFIXES:
        m = regex.match(text)
        if m:
            label = default_label
            if m.lastindex and m.group(1):
                matched_noun = m.group(1).lower()
                label = "RDV" if matched_noun == "rdv" else matched_noun.capitalize()
            return text[m.end():].strip(), label
    return text, None


def _clean_task_name(raw_name: str, fallback: str) -> str:
    """Tidy leftover leading/trailing connector prepositions around removed date/time spans."""
    cleaned = " ".join(raw_name.split()).strip(" ,.-:")
    for _ in range(2):
        cleaned = re.sub(r"^(?:at|on|for|to|about)\s+", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"\s+(?:at|on|for|to)$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\b(?:rdv|appointment|rendez-vous)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = " ".join(cleaned.split()).strip(" ,.-:")
    return cleaned or fallback


def _infer_rdv_fallback(raw_text: str, default_name: Optional[str]) -> Optional[str]:
    """Preserve explicit RDV / Rendez-vous / Appointment keyword as fallback label when no task remains."""
    if default_name:
        return default_name
    m = re.search(r"\b(rdv|rendez-vous|appointment)\b", raw_text, re.IGNORECASE)
    if m:
        kw = m.group(1).lower()
        if kw == "rdv":
            return "RDV"
        if kw == "rendez-vous":
            return "Rendez-vous"
        return "Appointment"
    return None


# ---------------------------------------------------------------------------
# Main parser class
# ---------------------------------------------------------------------------

class NaturalParser:
    @staticmethod
    def parse(text: str) -> Optional[Dict[str, Any]]:
        """
        Parses rich freeform expressions including:
          Timer expressions
          - "Ring in 15 min", "in 45m check laundry", "Check oven in 25 mins"
          - "Timer for 30m meditation", "Remind me in half an hour to check backup"

          Relative-day rendez-vous
          - "Call Sam in 2 days", "Call Sam in 2 days at 3pm"
          - "Doctor in 1 week at 10am", "Call client day after tomorrow at 14h30"

          Calendar, ordinal & weekday rendez-vous
          - "Set an alarm for Friday the 13th at 2:15 PM" (and "at2:15 PM")
          - "Meeting on Monday the 16th at 10am", "Pay rent on the 1st at 9am"
          - "Dentist on Nov 20th at 2:15 PM", "13th of December at 10am"
          - "Dentist on 2026-12-05 at 14:00", "Call client on 11/20 at 3pm"
          - "Dentist next Friday at 14:00", "Set an alarm for Friday at 2:15 PM"

          Same-day / tomorrow rendez-vous
          - "RDV at 4PM", "RDV tomorrow at 10am dentist", "at noon lunch"
          - "Call Linda at 7:15 tomorrow morning", "at 8 tonight netflix"

        Returns a dict or None if unrecognized.
        """
        raw = text.strip()
        if not raw:
            return None

        normalized = re.sub(r"[.!]+$", "", raw).strip()
        normalized = _normalize_natural_idioms(normalized)

        # ── 1. "remind me to <task> in <duration>" ──────────────────────────
        m = re.match(r"^remind\s+me\s+to\s+(.+?)\s+in\s+(\d+.+)$", normalized, re.IGNORECASE)
        if m:
            task = m.group(1).strip()
            total_days, sub_sec, rem = NaturalParser._consume_compound_duration(m.group(2))
            if total_days == 0 and sub_sec > 0 and not rem:
                return NaturalParser._build_timer(task or "Reminder", sub_sec)

        # ── 2. "remind me in <duration> [to/for] <task>" ───────────────────
        m = re.match(r"^remind\s+me\s+in\s+(\d+\w*.*)$", normalized, re.IGNORECASE)
        if m:
            result = NaturalParser._try_timer_from_in(m.group(1), "Reminder")
            if result:
                return result

        # ── 3. "[set an] ring/alarm/timer in/for <duration> [name]" ────────
        m = re.match(
            r"^(?:set\s+(?:an?\s+|the\s+)?)?(?:ring|alarm|timer)\s+(?:in|for)\s+(\d+\w*.*)$",
            normalized,
            re.IGNORECASE,
        )
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

        # ── Strip conversational prefixes for remaining RDV / timer rules ────
        body, conv_default = _strip_conversational_prefix(normalized)

        # ── 5. "<task> in <N> days/weeks [at <time>]"  ─────────────────────
        rdv_days = NaturalParser._try_relative_days(body, default_name=conv_default)
        if rdv_days:
            return rdv_days

        # ── 6. "<task> in <duration h/m/s>" ─────────────────────────────────
        m = re.match(r"^(.+?)\s+in\s+(\d+.+)$", body, re.IGNORECASE)
        if m:
            total_days, sub_sec, rem = NaturalParser._consume_compound_duration(m.group(2))
            if total_days == 0 and sub_sec > 0 and not rem:
                fallback = _infer_rdv_fallback(m.group(1), conv_default) or "Quick Timer"
                return NaturalParser._build_timer(_clean_task_name(m.group(1), fallback), sub_sec)

        # ── 7. Explicit / ordinal calendar dates ("Friday the 13th", "Nov 20th", "the 13th", "2026-12-05") ─
        cal_date = NaturalParser._try_calendar_date(body, default_name=conv_default or "Appointment")
        if cal_date:
            return cal_date

        # ── 8. "[next|this|on|for] <weekday> [at <time>] <task>" ───────────
        next_wd = NaturalParser._try_next_weekday(body, default_name=conv_default)
        if next_wd:
            return next_wd

        # ── 9. RDV / rendez-vous / appointment prefix ───────────────────────
        m = re.match(r"^(?:rdv|rendez-vous|appointment)\s+(.+)$", body, re.IGNORECASE)
        if m:
            result = NaturalParser._parse_appointment_phrase(m.group(1).strip(), conv_default or "RDV")
            if result:
                return result

        # ── 10. General appointment phrase (today/tomorrow/at/noon/time) ────
        result = NaturalParser._parse_appointment_phrase(body, conv_default or "Meeting")
        if result:
            return result

        return None

    # ── Shared time extraction helper ────────────────────────────────────────

    @staticmethod
    def _extract_time_from_text(
        text: str, is_tonight: bool = False
    ) -> Tuple[Optional[int], Optional[int], str]:
        """
        Extract an explicit time expression from *text*.
        Supports 'at 2:15 PM', 'at2:15 PM', '@3pm', '14:30', '14h30', '9h', 'at noon', 'at midnight'.
        Returns (hour_24, minute, remaining_text_without_time).
        """
        tod_m = re.search(r"\b(morning|afternoon|evening|night)\b", text, re.IGNORECASE)
        tod = tod_m.group(1).lower() if tod_m else None

        for match in _TIME_RE.finditer(text):
            h_raw = int(match.group(1))
            colon_min = match.group(2)
            h_marker = match.group(3)
            h_min = match.group(4)
            ampm = match.group(5)

            matched_slice = match.group(0).lower()
            had_at = matched_slice.startswith("at") or matched_slice.startswith("@")
            if not had_at:
                prefix_ctx = text[max(0, match.start() - 5):match.start()].lower()
                had_at = bool(re.search(r"(?:\bat\s*|@\s*)$", prefix_ctx))

            has_sep = colon_min is not None or h_marker is not None
            if colon_min is not None:
                mi_raw = int(colon_min)
            elif h_min is not None:
                mi_raw = int(h_min)
            else:
                mi_raw = 0

            # Guard: require 'at'/'@', am/pm, explicit ':'/'h' separator, tod, or tonight
            if not ampm and not has_sep and not had_at and not tod and not is_tonight:
                continue
            if not ampm and not has_sep and not had_at and not tod and not is_tonight and h_raw <= 6:
                continue

            resolved = _parse_time_str(h_raw, mi_raw, ampm, tod, is_tonight)
            if resolved is None:
                continue

            remaining = (text[:match.start()] + " " + text[match.end():]).strip()
            if tod:
                remaining = re.sub(rf"\b{tod}\b", " ", remaining, flags=re.IGNORECASE).strip()
            return resolved, mi_raw, " ".join(remaining.split())

        nm = re.search(r"\b(?:(?:at\s+|@\s*))?(noon|midnight)\b", text, re.IGNORECASE)
        if nm:
            h_out = 12 if nm.group(1).lower() == "noon" else 0
            remaining = (text[:nm.start()] + " " + text[nm.end():]).strip()
            if tod:
                remaining = re.sub(rf"\b{tod}\b", " ", remaining, flags=re.IGNORECASE).strip()
            return h_out, 0, " ".join(remaining.split())

        return None, None, text

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
    def _consume_compound_duration(text: str) -> Tuple[int, int, str]:
        """
        Consume one or more leading duration tokens connected by spaces, ',', 'and', or '+'.
        Returns (total_days, sub_day_seconds, unconsumed_trailing_text).
        """
        src = text.lstrip()
        first = _COMPOUND_UNIT_RE.match(src)
        if not first:
            return 0, 0, text

        total_days = 0
        sub_sec = 0

        def _add_token(val_s: str, unit_s: str) -> None:
            nonlocal total_days, sub_sec
            val = int(val_s)
            u = unit_s.lower()
            if u.startswith("w"):
                total_days += val * 7
            elif u.startswith("d"):
                total_days += val
            elif u.startswith("h"):
                sub_sec += val * 3600
            elif u.startswith("m"):
                sub_sec += val * 60
            elif u.startswith("s"):
                sub_sec += val

        _add_token(first.group(1), first.group(2))
        pos = first.end()

        while pos < len(src):
            cm = _COMPOUND_CONNECTOR_RE.match(src[pos:])
            if not cm:
                break
            next_start = pos + cm.end()
            um = _COMPOUND_UNIT_RE.match(src[next_start:])
            if not um:
                break
            _add_token(um.group(1), um.group(2))
            pos = next_start + um.end()

        return total_days, sub_sec, src[pos:].strip()

    @staticmethod
    def _try_timer_from_in(rest: str, default_name: str) -> Optional[Dict[str, Any]]:
        """Parse leading h/m/s duration from 'rest'; remainder is task name."""
        total_days, sub_sec, rem = NaturalParser._consume_compound_duration(rest)
        if total_days > 0:
            return None
        if sub_sec > 0:
            name = re.sub(r"^(?:to|for)\s+", "", rem, flags=re.IGNORECASE).strip()
            return NaturalParser._build_timer(name or default_name, sub_sec)
        return None

    # ── Relative-day rendez-vous ─────────────────────────────────────────────

    @staticmethod
    def _try_relative_days(text: str, default_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Handle patterns including compound relative offsets:
          "RDV in 5 days and 3 hours"
          "<task> in <N> days/weeks [and <H> hours ...] [at <time>]"
          "in <N> days [at <time>] [<task>]"
        """
        stripped = text.strip()
        for m in re.finditer(r"\bin\s+(?=\d)", stripped, re.IGNORECASE):
            pre_task = stripped[: m.start()].strip()
            after_in = stripped[m.end() :]
            total_days, sub_sec, post_text = NaturalParser._consume_compound_duration(after_in)
            if total_days <= 0:
                continue

            now = datetime.datetime.now()
            if sub_sec > 0:
                target_dt = now + datetime.timedelta(days=total_days, seconds=sub_sec)
                delta = float(total_days * 86400 + sub_sec)
                post_clean = post_text
                day_label = target_dt.strftime("%a, %b %d")
                time_label = target_dt.strftime("%H:%M:%S") if (sub_sec % 60) != 0 else target_dt.strftime("%H:%M")
            else:
                base_date = now.date() + datetime.timedelta(days=total_days)
                h_out, min_out, post_clean = NaturalParser._extract_time_from_text(post_text)
                if h_out is None or min_out is None:
                    h_out, min_out = 12, 0
                    post_clean = post_text
                target_dt = datetime.datetime.combine(base_date, datetime.time(h_out, min_out))
                delta = max(0.0, (target_dt - now).total_seconds())
                day_label = target_dt.strftime("%b %d")
                time_label = f"{h_out:02d}:{min_out:02d}"

            fallback = _infer_rdv_fallback(f"{pre_task} {post_clean}", default_name)
            name_parts = " ".join(
                filter(None, [_clean_task_name(pre_task, ""), _clean_task_name(post_clean, "")])
            ).strip()

            if name_parts:
                final_name = name_parts
            elif fallback:
                final_name = fallback
            elif sub_sec > 0:
                hrs = sub_sec // 3600
                mins = (sub_sec % 3600) // 60
                extra = f" {hrs}h" if hrs else ""
                if mins:
                    extra += f" {mins}m"
                final_name = f"In {total_days}d{extra}"
            else:
                final_name = f"In {total_days} day{'s' if total_days != 1 else ''}"

            return {
                "kind": "rendez-vous",
                "name": final_name,
                "seconds_from_now": max(0.0, delta),
                "target_dt": target_dt,
                "display_str": f"Rendez-vous: '{final_name}' on {day_label} at {time_label}",
            }

        return None

    # ── Explicit & ordinal calendar dates ────────────────────────────────────

    @staticmethod
    def _try_calendar_date(text: str, default_name: str = "Appointment") -> Optional[Dict[str, Any]]:
        """
        Handle calendar date expressions:
          - Weekday + ordinal day: "Friday the 13th at 2:15 PM", "Monday the 16th at 10am"
          - ISO date: "2026-12-05 at 14:00", "2026/12/05"
          - Month + day: "Nov 20th at 2:15 PM", "13th of December at 10am", "December 25 at 9am"
          - Numeric slash date: "11/20 at 3pm", "12/05/2026"
          - Ordinal day alone: "on the 13th at 2:15 PM", "on the 1st at 9am"
        """
        now = datetime.datetime.now()
        is_tonight = bool(re.search(r"\btonight\b", text, re.IGNORECASE))

        def _finish(target_date: datetime.date, h_val: int, mi_val: int, rem_text: str) -> Dict[str, Any]:
            cleaned_rem = re.sub(r"\b(?:today|tonight)\b", " ", rem_text, flags=re.IGNORECASE)
            final_name = _clean_task_name(cleaned_rem, default_name)
            target_dt = datetime.datetime.combine(target_date, datetime.time(h_val, mi_val))
            delta = (target_dt - now).total_seconds()
            date_fmt = "%a, %b %d, %Y" if target_dt.year != now.year else "%a, %b %d"
            day_label = target_dt.strftime(date_fmt)
            return {
                "kind": "rendez-vous",
                "name": final_name,
                "seconds_from_now": max(0.0, delta),
                "target_dt": target_dt,
                "display_str": f"Rendez-vous: '{final_name}' on {day_label} at {h_val:02d}:{mi_val:02d}",
            }

        # Case A: "<weekday> [the] <N>th" (e.g., "Friday the 13th", "Friday 13th")
        wd_ord_re = re.compile(
            rf"\b(?:(?:on|for)\s+)?({_WEEKDAY_PATTERN})\s+"
            rf"(?:the\s+(\d{{1,2}})(?:st|nd|rd|th)?|(\d{{1,2}})(?:st|nd|rd|th))"
            rf"\b(?!\s*(?::|am\b|pm\b))",
            re.IGNORECASE,
        )
        m = wd_ord_re.search(text)
        if m:
            weekday = _WEEKDAY_MAP[m.group(1).lower()]
            day_num = int(m.group(2) or m.group(3))
            rem = (text[:m.start()] + " " + text[m.end():]).strip()
            h_out, min_out, rem = NaturalParser._extract_time_from_text(rem, is_tonight)
            if h_out is None or min_out is None:
                h_out, min_out = 12, 0
            target_date = _next_weekday_and_day(now, weekday, day_num, h_out, min_out)
            if target_date is not None:
                return _finish(target_date, h_out, min_out, rem)
            return None

        # Case B: ISO date YYYY-MM-DD or YYYY/MM/DD
        iso_re = re.compile(r"\b(?:(?:on|for)\s+)?(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b", re.IGNORECASE)
        m = iso_re.search(text)
        if m:
            year, month, day_num = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                target_date = datetime.date(year, month, day_num)
            except ValueError:
                return None
            rem = (text[:m.start()] + " " + text[m.end():]).strip()
            h_out, min_out, rem = NaturalParser._extract_time_from_text(rem, is_tonight)
            if h_out is None or min_out is None:
                h_out, min_out = 12, 0
            return _finish(target_date, h_out, min_out, rem)

        # Case C1: "<Month> [the] <N>[th][, YYYY]"
        mon_day_re = re.compile(
            rf"\b(?:(?:on|for)\s+)?({_MONTH_PATTERN})\.?\s+(?:the\s+)?(\d{{1,2}})(?:st|nd|rd|th)?(?:\s*,?\s*(20\d{{2}}))?\b",
            re.IGNORECASE,
        )
        m = mon_day_re.search(text)
        if m:
            month = _MONTH_MAP[m.group(1).lower()]
            day_num = int(m.group(2))
            explicit_year = int(m.group(3)) if m.group(3) else None
            rem = (text[:m.start()] + " " + text[m.end():]).strip()
            h_out, min_out, rem = NaturalParser._extract_time_from_text(rem, is_tonight)
            if h_out is None or min_out is None:
                h_out, min_out = 12, 0
            target_date = NaturalParser._resolve_month_day(now, month, day_num, h_out, min_out, explicit_year)
            if target_date is not None:
                return _finish(target_date, h_out, min_out, rem)
            return None

        # Case C2: "[the] <N>[th] [of] <Month>[, YYYY]"
        day_mon_re = re.compile(
            rf"\b(?:(?:on|for)\s+)?(?:the\s+)?(\d{{1,2}})(?:st|nd|rd|th)?(?:\s+of)?\s+({_MONTH_PATTERN})\b(?:\s*,?\s*(20\d{{2}}))?",
            re.IGNORECASE,
        )
        m = day_mon_re.search(text)
        if m:
            day_num = int(m.group(1))
            month = _MONTH_MAP[m.group(2).lower()]
            explicit_year = int(m.group(3)) if m.group(3) else None
            rem = (text[:m.start()] + " " + text[m.end():]).strip()
            h_out, min_out, rem = NaturalParser._extract_time_from_text(rem, is_tonight)
            if h_out is None or min_out is None:
                h_out, min_out = 12, 0
            target_date = NaturalParser._resolve_month_day(now, month, day_num, h_out, min_out, explicit_year)
            if target_date is not None:
                return _finish(target_date, h_out, min_out, rem)
            return None

        # Case D: Numeric slash date "MM/DD" or "MM/DD/YYYY"
        slash_re = re.compile(r"\b(?:(?:on|for)\s+)?(\d{1,2})/(\d{1,2})(?:/(20\d{2}))?\b", re.IGNORECASE)
        m = slash_re.search(text)
        if m:
            month, day_num = int(m.group(1)), int(m.group(2))
            explicit_year = int(m.group(3)) if m.group(3) else None
            rem = (text[:m.start()] + " " + text[m.end():]).strip()
            h_out, min_out, rem = NaturalParser._extract_time_from_text(rem, is_tonight)
            if h_out is None or min_out is None:
                h_out, min_out = 12, 0
            target_date = NaturalParser._resolve_month_day(now, month, day_num, h_out, min_out, explicit_year)
            if target_date is not None:
                return _finish(target_date, h_out, min_out, rem)
            return None

        # Case E: Ordinal day of month alone ("on the 13th", "for the 1st", "the 13th")
        ord_re = re.compile(
            r"\b(?:(?:on|for)\s+(?:the\s+)?|the\s+)(\d{1,2})(?:st|nd|rd|th)\b",
            re.IGNORECASE,
        )
        m = ord_re.search(text)
        if m:
            day_num = int(m.group(1))
            rem = (text[:m.start()] + " " + text[m.end():]).strip()
            h_out, min_out, rem = NaturalParser._extract_time_from_text(rem, is_tonight)
            if h_out is None or min_out is None:
                h_out, min_out = 12, 0
            target_date = _next_day_of_month(now, day_num, h_out, min_out)
            if target_date is not None:
                return _finish(target_date, h_out, min_out, rem)
            return None

        return None

    @staticmethod
    def _resolve_month_day(
        now: datetime.datetime,
        month: int,
        day_num: int,
        hour: int,
        minute: int,
        explicit_year: Optional[int],
    ) -> Optional[datetime.date]:
        if explicit_year is not None:
            try:
                return datetime.date(explicit_year, month, day_num)
            except ValueError:
                return None

        for offset in range(5):
            year = now.year + offset
            try:
                cand = datetime.date(year, month, day_num)
            except ValueError:
                continue  # handles Feb 29 waiting for next leap year
            cand_dt = datetime.datetime.combine(cand, datetime.time(hour, minute))
            if cand_dt > now:
                return cand
        return None

    # ── Next/this/bare weekday handler ───────────────────────────────────────

    @staticmethod
    def _try_next_weekday(text: str, default_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Handle: "next <weekday> [at <time>] [<task>]"
                "this <weekday> at <time> [<task>]"
                "<task> on <weekday> at <time>"
                "Set an alarm for Friday at 2:15 PM"
        """
        m = re.search(rf"\b(?:(next|this|on|for)\s+)?({_WEEKDAY_PATTERN})\b", text, re.IGNORECASE)
        if not m:
            return None

        modifier = m.group(1).lower() if m.group(1) else None
        wd_str = m.group(2).lower()
        weekday = _WEEKDAY_MAP[wd_str]
        now = datetime.datetime.now()

        remaining = (text[:m.start()] + " " + text[m.end():]).strip()
        h_out, min_out, remaining = NaturalParser._extract_time_from_text(remaining)

        # Guard: a bare weekday (without next/this/on/for) requires an explicit time
        if modifier is None and h_out is None:
            return None

        if h_out is None or min_out is None:
            h_out, min_out = 12, 0

        if modifier != "next" and weekday == now.date().weekday():
            today_dt = datetime.datetime.combine(now.date(), datetime.time(h_out, min_out))
            base_date = now.date() if today_dt > now else _next_weekday(now.date(), weekday)
        else:
            base_date = _next_weekday(now.date(), weekday)

        fallback_label = default_name or f"{wd_str.capitalize()} meeting"
        final_name = _clean_task_name(remaining, fallback_label)

        target_dt = datetime.datetime.combine(base_date, datetime.time(h_out, min_out))
        delta = (target_dt - now).total_seconds()
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
          - "at 8 tonight netflix"
          - "Dinner at 19h30", "at noon lunch"
        """
        text = phrase.strip()

        is_tomorrow = bool(re.search(r"\btomorrow\b", text, re.IGNORECASE))
        is_tonight = bool(re.search(r"\btonight\b", text, re.IGNORECASE))

        clean = re.sub(r"\b(tomorrow|today|tonight)\b", " ", text, flags=re.IGNORECASE)
        h_out, mi_raw, name_part = NaturalParser._extract_time_from_text(clean, is_tonight=is_tonight)
        if h_out is None or mi_raw is None:
            return None

        final_name = _clean_task_name(name_part, default_name)

        now = datetime.datetime.now()
        target_date = now.date()

        if is_tomorrow:
            target_date += datetime.timedelta(days=1)
        else:
            cand_dt = datetime.datetime.combine(target_date, datetime.time(h_out, mi_raw))
            if cand_dt <= now and (not is_tonight or h_out == 0):
                target_date += datetime.timedelta(days=1)

        target_dt = datetime.datetime.combine(target_date, datetime.time(h_out, mi_raw))
        delta = (target_dt - now).total_seconds()
        day_str = "Tomorrow" if target_dt.date() == (now.date() + datetime.timedelta(days=1)) else "Today"

        return {
            "kind": "rendez-vous",
            "name": final_name,
            "seconds_from_now": max(0.0, delta),
            "target_dt": target_dt,
            "display_str": f"Rendez-vous: '{final_name}' on {day_str} at {h_out:02d}:{mi_raw:02d}",
        }

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
