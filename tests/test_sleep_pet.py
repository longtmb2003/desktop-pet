from datetime import time

import pytest

from mochi.power import PowerWatcher
from mochi.state import Action, Motion, State


@pytest.fixture
def floor(pet):
    pet.px, pet.py, pet.vx, pet.vy, pet.support = 300.0, pet.screen_geo().bottom + 1 - pet.feet, 0.0, 0.0, None
    pet.grounded = True; pet.enter(State()); pet.until = float("inf"); pet.t = 100.0; pet.last_touch = -1e9
    pet.now_time = lambda: time(15, 0)
    return pet


def clock(pet, h, m=0):
    pet.now_time = lambda: time(h, m)
    pet.check_sleep()


ASLEEP, AWAKE = State(Motion.SLEEP), None


def test_it_is_awake_in_the_afternoon_and_never_dozes_off_by_itself(floor):
    slept = 0
    for _ in range(600):                                                 # many behaviour changes, in the afternoon
        floor.enter(State()); floor.until = 0.0; floor.tick()
        slept += floor.state.motion is Motion.SLEEP
    assert slept == 0


def test_the_midday_nap_starts_at_twelve_and_ends_at_half_past_one(floor):
    clock(floor, 11, 59); assert floor.state != ASLEEP
    clock(floor, 12, 0); assert floor.state == ASLEEP and floor.sleeping_for == "nap"
    for _ in range(3):                                                   # each time the sleep runs out it goes on sleeping
        floor.until = 0.0; floor.tick(); assert floor.state == ASLEEP
    clock(floor, 13, 29); assert floor.state == ASLEEP
    floor.bubble.dismiss(); clock(floor, 13, 30)
    assert floor.state == State(action=Action.YAWN) and floor.sleeping_for == "" and floor.bubble.lines == "Ưm... dậy rồi!"
    floor.until = 0.0; floor.tick(); assert floor.state.motion is not Motion.SLEEP


def test_it_sleeps_in_the_evening_and_wakes_in_the_morning(floor):
    clock(floor, 21, 59); assert floor.state != ASLEEP
    clock(floor, 22, 0); assert floor.state == ASLEEP and floor.sleeping_for == "night"
    clock(floor, 3, 0); assert floor.state == ASLEEP
    clock(floor, 6, 0); assert floor.state == State(action=Action.YAWN)


def test_a_locked_screen_puts_it_to_sleep_and_unlocking_wakes_it_with_a_greeting(floor):
    floor.on_lock(True)
    assert floor.state == ASLEEP and floor.sleeping_for == "system"
    floor.until = 0.0; floor.tick(); assert floor.state == ASLEEP        # it stays asleep while locked
    floor.bubble.dismiss(); floor.on_lock(False)
    assert floor.state == State(action=Action.YAWN) and floor.bubble.lines == "Chào mừng bạn quay lại!"


def test_the_computer_going_to_sleep_does_the_same(floor):
    floor.on_suspend(True); assert floor.state == ASLEEP
    floor.bubble.dismiss(); floor.on_suspend(False)
    assert floor.state == State(action=Action.YAWN) and floor.bubble.isVisible()


def test_lock_and_suspend_are_independent_and_both_must_clear(floor):
    floor.on_lock(True); floor.on_suspend(True)
    floor.on_lock(False); assert floor.state == ASLEEP                   # still suspended
    floor.on_suspend(False); assert floor.state.action is Action.YAWN


def test_the_lock_rule_can_be_switched_off(floor):
    floor.cfg.sleep_system = False
    floor.on_lock(True); floor.on_suspend(True)
    assert floor.state != ASLEEP


def test_a_lock_that_ends_during_the_night_leaves_it_asleep_for_the_night(floor):
    floor.on_lock(True)
    floor.now_time = lambda: time(23, 0)
    floor.on_lock(False)
    assert floor.state == ASLEEP and floor.sleeping_for == "night"


def test_windows_and_lock_can_be_turned_off_in_settings(floor):
    floor.cfg.nap_on = False; clock(floor, 12, 30); assert floor.state != ASLEEP
    floor.cfg.night_on = False; clock(floor, 23, 0); assert floor.state != ASLEEP


def landed(p):
    p.vy, p.py, p.grounded = 0.0, p.screen_geo().bottom + 1 - p.feet, True


def test_being_petted_wakes_it_and_it_dozes_off_again_a_while_later(floor):
    clock(floor, 12, 30); assert floor.state == ASLEEP
    floor.t = 500.0; floor.last_touch = floor.t; floor.pet_it()
    assert floor.state.motion is not Motion.SLEEP                        # awake at once
    landed(floor); floor.enter(State()); floor.until = float("inf")
    floor.t += 5; floor.next_check = 0.0; floor.tick()                   # five seconds after the pat, on its feet
    assert floor.state.motion is not Motion.SLEEP                        # the once-a-second check leaves it alone
    floor.until = 0.0; floor.t += 1; floor.tick()
    assert floor.state.motion is not Motion.SLEEP                        # and so does the end of what it was doing
    floor.t += 30; floor.enter(State()); floor.next_check = 0.0; landed(floor)
    floor.tick()
    assert floor.state == ASLEEP                                         # half a minute later it goes back to sleep


def test_a_lock_ignores_the_grace_after_a_pat(floor):
    floor.t = 500.0; floor.last_touch = floor.t                          # petted this very second
    floor.on_lock(True)
    assert floor.state == ASLEEP
    floor.enter(State(expression=__import__("mochi.state", fromlist=["Expression"]).Expression.HAPPY)); floor.until = 0.0; floor.tick()
    assert floor.state == ASLEEP                                         # a locked screen means asleep, whoever touched it last


def test_a_pomodoro_focus_keeps_it_working_at_midday_and_it_naps_afterwards(floor):
    floor.start_focus(25)
    clock(floor, 12, 30); assert floor.state == State(action=Action.WORK)
    floor.until = 0.0; floor.tick(); assert floor.state == State(action=Action.WORK)
    floor.pomo.reset(); floor.until = 0.0; floor.tick()
    assert floor.state == ASLEEP


def test_locking_beats_a_pomodoro(floor):
    floor.start_focus(25); floor.on_lock(True)
    assert floor.state == ASLEEP


def test_sleep_you_asked_for_is_not_undone_by_the_schedule(floor):
    floor.enter(State(Motion.SLEEP))                                     # chosen from the menu, at 15:00
    floor.check_sleep()
    assert floor.state == ASLEEP and floor.sleeping_for == ""            # nothing wakes it early
    floor.until = 0.0; floor.tick()
    assert floor.state.motion is not Motion.SLEEP                        # it wakes when the nap you asked for runs out


def test_it_only_falls_asleep_when_settled_on_the_ground(floor):
    floor.enter(State(Motion.AIRBORNE)); floor.grounded = False
    clock(floor, 12, 30); assert floor.state == State(Motion.AIRBORNE)
    floor.enter(State(Motion.DRAG)); clock(floor, 12, 31); assert floor.state == State(Motion.DRAG)
    floor.enter(State()); floor.grounded = True; clock(floor, 12, 32); assert floor.state == ASLEEP


def test_it_wakes_in_the_afternoon_after_starting_up_inside_the_nap_window(pet):
    pet.now_time = lambda: time(12, 30)
    pet.px, pet.py, pet.vy, pet.support = 300.0, pet.screen_geo().bottom + 1 - pet.feet, 0.0, None
    pet.grounded = True; pet.enter(State()); pet.next_check = 0.0; pet.tick()
    assert pet.state == ASLEEP
    pet.now_time = lambda: time(13, 31); pet.next_check = 0.0; pet.tick()
    assert pet.state.action is Action.YAWN


def test_the_check_runs_from_the_normal_tick_once_a_second(floor):
    floor.now_time = lambda: time(12, 30)
    floor.next_check = 0.0; floor.tick()
    assert floor.state == ASLEEP


# ---- the watcher ---------------------------------------------------------------------------------------------------
class NoBus:
    def isConnected(self): return False


def test_the_watcher_forwards_lock_and_suspend_signals_and_works_without_any_bus(qapp):
    got = []
    w = PowerWatcher(lambda on: got.append(("lock", on)), lambda on: got.append(("sleep", on)), NoBus(), NoBus())
    assert w.connected == [] and got == [("lock", False)]                # no bus: it starts as "not locked" and nothing is ever heard
    w.screenActive(True); w.prepareForSleep(True); w.screenActive(False); w.prepareForSleep(False)
    assert got[1:] == [("lock", True), ("sleep", True), ("lock", False), ("sleep", False)]


def test_the_pet_can_hold_a_watcher(pet, qapp):
    w = PowerWatcher(pet.on_lock, pet.on_suspend, NoBus(), NoBus())
    pet.attach_power(w)
    assert pet.power is w


@pytest.mark.skipif(not __import__("shutil").which("dbus-daemon"), reason="needs dbus-daemon")
def test_the_watcher_really_hears_the_lock_signal_on_a_dbus_session(qapp):
    """the slot signatures are checked by Qt at connect time only: this catches a wrong one, with a private bus of its own"""
    import os
    import signal
    import subprocess

    from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer
    from PySide6.QtDBus import QDBusConnection, QDBusMessage
    cmd = ["dbus-daemon", "--session", "--fork", "--print-address", "--print-pid"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    addr, pid = proc.stdout.split()[:2]
    try:
        listen, sender = (QDBusConnection.connectToBus(addr, name) for name in ("mochi-test-listen", "mochi-test-send"))
        got = []
        w = PowerWatcher(lambda on: got.append(on), lambda on: None, listen, NoBus())
        assert "session:/org/freedesktop/ScreenSaver" in w.connected and got == [False]
        for value in (True, False):
            msg = QDBusMessage.createSignal("/org/freedesktop/ScreenSaver", "org.freedesktop.ScreenSaver", "ActiveChanged")
            msg.setArguments([value]); sender.send(msg)
            loop = QEventLoop(); QTimer.singleShot(200, loop.quit); loop.exec()
        assert got == [False, True, False]
        QCoreApplication.processEvents()
    finally:
        os.kill(int(pid), signal.SIGTERM)
