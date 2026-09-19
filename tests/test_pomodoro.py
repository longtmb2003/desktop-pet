from mochi.pomodoro import Pomodoro


class Clock:
    def __init__(self): self.t = 1000.0
    def __call__(self): return self.t


def make():
    c = Clock()
    return c, Pomodoro(c)


def test_a_full_cycle_focus_then_break_then_off():
    c, p = make()
    assert not p.active and p.poll() is None and p.label() == "Pomodoro: tắt"
    p.start(25 * 60, 5 * 60)
    assert p.focusing and p.remaining() == 1500 and p.label() == "Tập trung 25:00"
    c.t += 1499; assert p.poll() is None
    c.t += 2; assert p.poll() == "focus_done" and p.phase == "break" and not p.focusing
    assert p.poll() is None                                              # the event fires once
    assert 298 <= p.remaining() <= 300                                   # the break counts from the end of the focus
    c.t += 400; assert p.poll() == "break_done" and not p.active


def test_a_late_poll_does_not_lengthen_the_break():
    c, p = make()
    p.start(60, 300)
    c.t += 200                                                           # the app was frozen / the machine slept for 2m20s past the end
    assert p.poll() == "focus_done"
    assert p.remaining() == 160


def test_pause_freezes_the_remaining_time_and_resume_continues_it():
    c, p = make()
    p.start(600, 60)
    c.t += 100; p.pause()
    assert p.paused and not p.focusing and p.remaining() == 500 and "tạm dừng" in p.label()
    c.t += 10_000; assert p.poll() is None and p.remaining() == 500      # paused time doesn't count, however long
    p.resume(); c.t += 200
    assert p.remaining() == 300 and p.poll() is None


def test_reset_stops_everything_and_pause_resume_are_harmless_when_off():
    c, p = make()
    p.pause(); p.resume(); assert not p.active
    p.start(60, 60); p.pause(); p.reset()
    assert not p.active and p.remaining() == 0 and p.poll() is None
    p.start(60, 60); p.pause(); p.pause()                               # double pause must not clobber the remaining time
    c.t += 30; p.resume(); assert p.remaining() == 60


def test_restart_replaces_a_running_session():
    c, p = make()
    p.start(600, 60); c.t += 300
    p.start(120, 30)
    assert p.remaining() == 120 and p.break_s == 30
