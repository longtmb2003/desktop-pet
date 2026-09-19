from datetime import datetime, timedelta

import pytest

from mochi.reminders import GRACE, MAX_REMINDERS, MAX_TEXT, Reminder, Scheduler, dump, from_dict, parse, valid_time


class Clocks:
    def __init__(self):
        self.m, self.dt = 1000.0, datetime(2026, 9, 21, 8, 0, 0)          # a Monday

    def mono(self): return self.m
    def now(self): return self.dt

    def advance(self, secs):
        self.m += secs; self.dt += timedelta(seconds=secs)


def sched(*rs):
    c = Clocks()
    return c, Scheduler(rs, c.mono, c.now)


def test_an_interval_reminder_fires_each_period_and_never_in_a_burst():
    c, s = sched(Reminder("Uống nước", "every", 45))
    assert s.due() == []
    c.advance(45 * 60 - 1); assert s.due() == []
    c.advance(2); assert [r.text for r in s.due()] == ["Uống nước"]
    assert s.due() == []                                                   # once per period
    c.advance(45 * 60 * 5)                                                 # stalled for five periods
    assert len(s.due()) == 1 and s.due() == []                             # one reminder, not five
    c.advance(45 * 60); assert len(s.due()) == 1


def test_a_daily_reminder_fires_once_at_its_time_on_its_days():
    c, s = sched(Reminder("Họp nhóm", "daily", at="09:30", days=(0, 2)))     # Monday and Wednesday
    c.advance(89 * 60 + 59); assert s.due() == []                          # 09:29:59
    c.advance(1); assert [r.text for r in s.due()] == ["Họp nhóm"]         # 09:30:00
    c.advance(30); assert s.due() == []                                    # not twice the same day
    c.advance(24 * 3600); assert s.due() == []                             # Tuesday: not a listed day
    c.advance(24 * 3600); assert [r.text for r in s.due()] == ["Họp nhóm"]                                 # Wednesday


def test_a_daily_reminder_is_not_fired_retroactively_after_a_late_start():
    c, s = sched(Reminder("Họp", "daily", at="08:00"))
    c.dt = c.dt.replace(hour=8, minute=0, second=0); c.advance(GRACE - 1); assert len(s.due()) == 1       # just missed: still worth saying
    c2, s2 = sched(Reminder("Họp", "daily", at="07:00"))
    assert s2.due() == []                                                  # an hour ago: too late, stay quiet
    c3, s3 = sched(Reminder("Họp", "daily", at="08:00"))
    c3.advance(GRACE + 1); assert s3.due() == []


def test_disabled_reminders_never_fire_and_several_can_be_due_together():
    c, s = sched(Reminder("a", "every", 1, enabled=False), Reminder("b", "every", 1), Reminder("c", "every", 1))
    c.advance(61)
    assert [r.text for r in s.due()] == ["b", "c"]


def test_replacing_the_list_keeps_the_schedule_of_untouched_reminders():
    keep = Reminder("giữ", "every", 10)
    c, s = sched(keep)
    c.advance(9 * 60)
    s.replace([keep, Reminder("mới", "every", 10)])
    c.advance(61)
    assert [r.text for r in s.due()] == ["giữ"]                            # the old one carries on; the new one is 10 minutes away
    s.replace([Reminder("giữ", "every", 20)])                              # an edited one starts afresh
    c.advance(15 * 60); assert s.due() == []


@pytest.mark.parametrize("t,ok", [("09:00", True), ("0:05", True), ("23:59", True), ("24:00", False), ("12:60", False), ("abc", False),
                                  ("9", False), ("", False)])
def test_time_validation(t, ok):
    assert valid_time(t) is ok


def test_json_round_trip_and_defaults():
    rs = [Reminder("Uống nước", "every", 30), Reminder("Họp", "daily", at="09:05", days=(0, 4), enabled=False)]
    assert parse(dump(rs)) == rs
    assert parse("") == [] and parse("null") == [] and parse("{}") == []


def test_untrusted_json_is_cleaned_or_skipped_and_never_raises():
    raw = ('[{"text": "ok"}, {"text": ""}, {"text": "x", "kind": "hourly"}, {"text": "x", "minutes": 0}, {"text": "x", "minutes": true},'
           ' {"text": "x", "kind": "daily", "at": "25:00"}, {"text": "x", "days": []}, {"text": "x", "days": [7]}, 5, null, "s",'
           ' {"text": "a\\u0000b\\n\\u001b[0mc", "minutes": 10}, {"text": "big", "minutes": 99999999999999999999}]')
    got = parse(raw)
    assert [r.text for r in got] == ["ok", "a b [0mc"]
    assert parse("not json") == []
    assert len(parse(dump([Reminder(f"r{i}") for i in range(200)]) )) == MAX_REMINDERS
    assert len(from_dict({"text": "x" * 5000}).text) == MAX_TEXT
    assert from_dict({"text": "x", "kind": "daily", "at": "9:05"}).at == "09:05"


def test_describe_reads_naturally():
    assert Reminder("Uống nước", "every", 45).describe() == "Uống nước  —  mỗi 45 phút"
    assert "09:30" in Reminder("Họp", "daily", at="09:30").describe() and "[tắt]" in Reminder("x", enabled=False).describe()
