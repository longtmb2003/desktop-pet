"""Reminders the user sets up: pure scheduling with injectable clocks, no Qt. Stored as JSON text in Settings."""
import json
import time
from dataclasses import dataclass
from datetime import datetime

from .bubble import clean_text

MAX_REMINDERS, MAX_TEXT = 30, 120
GRACE = 300                                    # a daily reminder still fires up to this many seconds late (say, right after login)
ALL_DAYS = (0, 1, 2, 3, 4, 5, 6)               # Monday = 0


@dataclass(frozen=True)
class Reminder:
    text: str
    kind: str = "every"                        # "every": each `minutes` minutes; "daily": at `at` (local time) on `days`
    minutes: int = 45
    at: str = "09:00"
    days: tuple = ALL_DAYS
    enabled: bool = True

    def clock(self):
        """the daily time as (hour, minute)"""
        h, m = self.at.split(":")
        return int(h), int(m)

    def describe(self):
        when = f"mỗi {self.minutes} phút" if self.kind == "every" else f"{self.at}" + ("" if self.days == ALL_DAYS else " (một số ngày)")
        return f"{self.text}  —  {when}" + ("" if self.enabled else "  [tắt]")


def valid_time(s):
    try:
        h, m = str(s).split(":")
        return len(m) == 2 and 0 <= int(h) <= 23 and 0 <= int(m) <= 59
    except ValueError:
        return False


def from_dict(d):
    """a validated Reminder from an untrusted dict; raises ValueError/TypeError if it is not usable"""
    text = clean_text(d.get("text", ""))[:MAX_TEXT]
    if not text: raise ValueError("empty text")
    kind = d.get("kind", "every")
    if kind not in ("every", "daily"): raise ValueError(f"unknown kind {kind!r}")
    minutes = d.get("minutes", 45)
    if isinstance(minutes, bool) or not isinstance(minutes, int) or not 1 <= minutes <= 1440: raise ValueError("minutes must be 1-1440")
    at = str(d.get("at", "09:00"))
    if not valid_time(at): raise ValueError(f"bad time {at!r}")
    days = d.get("days", ALL_DAYS)
    ok = isinstance(days, (list, tuple)) and days and all(isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= 6 for x in days)
    if not ok: raise ValueError("days must be a list of 0-6")
    h, m = at.split(":")
    return Reminder(text, kind, minutes, f"{int(h):02d}:{m}", tuple(sorted(set(days))), bool(d.get("enabled", True)))


def parse(raw):
    """[Reminder] from the JSON text in Settings: anything unusable is skipped, nothing raises"""
    try:
        data = json.loads(raw) if raw else []
    except ValueError:
        return []
    out = []
    for d in (data if isinstance(data, list) else [])[:MAX_REMINDERS]:
        try:
            out.append(from_dict(d))
        except (ValueError, TypeError, AttributeError, OverflowError):
            pass
    return out


def dump(reminders):
    return json.dumps([{"text": r.text, "kind": r.kind, "minutes": r.minutes, "at": r.at, "days": list(r.days), "enabled": r.enabled}
                       for r in reminders[:MAX_REMINDERS]], ensure_ascii=False)


class Scheduler:
    def __init__(self, reminders=(), mono=time.monotonic, now=datetime.now):
        self.mono, self.now, self.items, self.state = mono, now, [], {}
        self.replace(reminders)

    def replace(self, reminders):
        """switch to a new list; a reminder that is unchanged keeps its place in the schedule (editing one doesn't restart the rest)"""
        old, self.state, self.items = self.state, {}, list(reminders)
        for r in self.items:
            self.state[r] = old.get(r) or ({"next": self.mono() + r.minutes * 60} if r.kind == "every" else {"fired": None})

    def due(self):
        """the reminders that fire right now (each once); call as often as you like"""
        out, mono, now = [], self.mono(), self.now()
        for r in self.items:
            if not r.enabled: continue
            st = self.state[r]
            if r.kind == "every":
                if mono >= st["next"]:
                    out.append(r); st["next"] = mono + r.minutes * 60             # no catching up on the ones missed while stalled
            elif now.weekday() in r.days and st["fired"] != now.date():
                h, m = r.clock()
                late = (now - now.replace(hour=h, minute=m, second=0, microsecond=0)).total_seconds()
                if 0 <= late <= GRACE:
                    out.append(r); st["fired"] = now.date()
        return out
