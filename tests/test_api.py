import pytest

import mochi.api as api
from mochi.api import Api
from mochi.state import Action, Expression, Motion, State


@pytest.fixture
def bus(pet):
    return Api(pet)


def test_show_message_shows_a_sanitised_bubble_even_in_quiet_mode(bus, pet):
    pet.cfg.quiet = True
    assert bus.showMessage("  build\x00 finished\n\n\x1b[31mred  ") is True
    assert pet.bubble.lines == "build finished [31mred"
    assert not any(c in pet.bubble.lines for c in "\x00\x1b\n")


def test_message_length_is_limited_and_blank_is_refused(bus, pet):
    assert bus.showMessage("x" * 100_000) is True and len(pet.bubble.lines) == 200
    assert bus.showMessage(" \n\t\x00 ") is False


@pytest.mark.parametrize("name,expected", [("happy", Expression.HAPPY), ("SCARED", Expression.SCARED), (" tired ", Expression.TIRED),
                                           ("dizzy", Expression.DIZZY)])
def test_set_expression(bus, pet, name, expected):
    pet.enter(State())
    assert bus.setExpression(name) is True and pet.state.expression is expected
    assert bus.setExpression("normal") is True and pet.state == State()


@pytest.mark.parametrize("bad", ["", "angry", "happy; rm -rf /", "x" * 10_000, "\x00"])
def test_unknown_expressions_are_refused_and_change_nothing(bus, pet, bad):
    pet.enter(State())
    assert bus.setExpression(bad) is False and pet.state == State()


def test_expressions_are_not_forced_on_a_pet_being_dragged_or_thrown(bus, pet):
    for motion in (Motion.DRAG, Motion.AIRBORNE):
        pet.enter(State(motion))
        assert bus.setExpression("happy") is False and pet.state == State(motion)


def test_task_finished_cheers_and_names_the_task(bus, pet, monkeypatch):
    import mochi.pet as mp
    chimes = []
    monkeypatch.setattr(mp, "chime", lambda: chimes.append(1))
    pet.grounded = True; pet.enter(State())
    assert bus.notifyTaskFinished("make -j8") is True
    assert pet.bubble.lines == "Xong rồi: make -j8" and pet.state.expression is Expression.HAPPY and chimes == [1]
    pet.bubble.dismiss(); pet.cfg.quiet = True; chimes.clear()
    assert bus.notifyTaskFinished("") is True and pet.bubble.lines == "Xong rồi!" and chimes == []       # quiet: no sound


def test_start_pomodoro_validates_the_length(bus, pet):
    assert bus.startPomodoro(0) is False and bus.startPomodoro(-5) is False and bus.startPomodoro(181) is False
    assert not pet.pomo.active
    pet.grounded = True; pet.enter(State())
    assert bus.startPomodoro(45) is True and pet.pomo.active and 44 * 60 < pet.pomo.remaining() <= 45 * 60
    assert pet.state == State(action=Action.WORK)


def test_calls_are_rate_limited_then_recover(bus, pet, monkeypatch, caplog):
    t = [1000.0]
    monkeypatch.setattr(api.time, "monotonic", lambda: t[0])
    results = [bus.showMessage(f"m{i}") for i in range(30)]
    assert results[:api.RATE_CALLS] == [True] * api.RATE_CALLS and results[api.RATE_CALLS:] == [False] * 10
    assert sum("refused" in r.message for r in caplog.records) == 1          # one warning, not ten
    t[0] += api.RATE_SECS + 1
    assert bus.showMessage("again") is True


def test_a_failing_pet_never_raises_out_of_a_slot(bus, pet, monkeypatch):
    monkeypatch.setattr(pet, "say", lambda *a, **k: 1 / 0)
    assert bus.showMessage("x") is False


def test_without_a_pet_everything_is_refused():
    b = Api(None)
    assert (b.showMessage("x"), b.setExpression("happy"), b.notifyTaskFinished("x"), b.startPomodoro(5)) == (False,) * 4
