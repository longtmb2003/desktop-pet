"""When the pet sleeps. It never dozes off at random: only while the screen is locked or the computer sleeps, in a nap window at
midday, and at night (all local time, all editable in Settings). Pure functions; the pet does the rest."""
from datetime import time

NAP = ("12:00", "13:30")
NIGHT = ("22:00", "06:00")
DEFAULTS = {"nap_from": NAP[0], "nap_to": NAP[1], "night_from": NIGHT[0], "night_to": NIGHT[1]}


def parse_time(s, default):
    """a datetime.time from "H:MM"/"HH:MM"; the default (also a string) if it isn't one"""
    for v in (s, default):
        try:
            h, m = str(v).strip().split(":")
            if len(m) == 2 and 0 <= int(h) <= 23 and 0 <= int(m) <= 59: return time(int(h), int(m))
        except ValueError:
            pass
    return time(0, 0)


def in_window(now, start, end):
    """is `now` (a datetime.time) from `start` up to, not including, `end`? A window may run past midnight (22:00-06:00);
    start == end is an empty window, not the whole day"""
    if start == end: return False
    return start <= now < end if start < end else now >= start or now < end


def scheduled(now, cfg):
    """"nap", "night" or "" : which sleep window (if any) `now` falls in, given the Settings `cfg`"""
    if cfg.nap_on and in_window(now, parse_time(cfg.nap_from, NAP[0]), parse_time(cfg.nap_to, NAP[1])): return "nap"
    if cfg.night_on and in_window(now, parse_time(cfg.night_from, NIGHT[0]), parse_time(cfg.night_to, NIGHT[1])): return "night"
    return ""
