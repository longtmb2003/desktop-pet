import pytest

from mochi.bubble import MAX_CHARS, MAX_QUEUE, BubbleQueue, place, show_ms
from mochi.physics import FEET, S, Bounds

G = Bounds(0, 0, 1919, 1079)


def test_the_bubble_sits_above_the_pet_on_the_right_when_it_fits():
    x, y, right = place(500, 600, 120, 40, G)
    assert right and x > 500 and y + 40 <= 600 + FEET - 100           # right of centre, above the ears


def test_it_flips_to_the_left_near_the_right_screen_edge():
    x, y, right = place(1919 - S, 600, 140, 40, G)
    assert not right and x + 140 <= G.right and x >= G.left


@pytest.mark.parametrize("px,py", [(-200, -200), (5000, 5000), (0, 0), (1919 - S, 0)])
def test_it_never_leaves_the_screen(px, py):
    x, y, _ = place(px, py, 200, 60, G)
    assert G.left <= x and x + 200 <= G.right and G.top <= y


def test_urgent_jumps_the_queue_and_duplicates_are_ignored():
    q = BubbleQueue()
    assert q.push("a") and q.push("b") and not q.push("a") and q.push("URGENT", urgent=True)
    assert [q.next(), q.next(), q.next(), q.next()] == ["URGENT", "a", "b", None]
    assert q.push("b")                                                  # allowed again once it is no longer waiting or showing


def test_the_showing_message_is_not_repeated_immediately():
    q = BubbleQueue(); q.push("x"); q.next()
    assert not q.push("x")


def test_the_backlog_is_capped_and_long_or_blank_text_is_sanitised():
    q = BubbleQueue()
    for i in range(50): q.push(f"m{i}")
    assert len(q.items) == MAX_QUEUE and q.items[-1] == "m49"           # newest kept, oldest dropped
    q.clear()
    assert not q.push("   \n\t ") and q.push("x" * 5000) and len(q.next()) == MAX_CHARS
    assert q.push("a\n\nb   c") and q.next() == "a b c"


def test_reading_time_is_between_two_and_a_half_and_five_seconds():
    assert show_ms("Á!") == 2500 and show_ms("x" * 10_000) == 5000
    assert 2500 < show_ms("Nghỉ mắt một chút nhé!") < 5000                  # ordinary chatter lands in between
    assert all(2500 <= show_ms("x" * n) <= 5000 for n in range(0, 300, 7))
    assert [show_ms("x" * n) for n in range(0, 100, 10)] == sorted(show_ms("x" * n) for n in range(0, 100, 10))     # longer never shorter


def test_bubbles_show_in_turn_and_then_go_away(qapp):
    from mochi.bubble import SpeechBubble
    b = SpeechBubble()
    b.say("một"); b.say("hai")
    assert b.isVisible() and b.lines == "một" and b.phase == "show"
    b.advance(); assert not b.isVisible() and b.phase == "gap"          # time's up: hidden between messages
    b.advance(); assert b.isVisible() and b.lines == "hai"
    b.advance(); b.advance()
    assert not b.isVisible() and b.phase == "idle" and not b.timer.isActive()      # nothing lingers once the queue is empty
    b.say("ba"); assert b.isVisible()                                   # and it starts again
    b.dismiss(); assert not b.isVisible() and b.phase == "idle" and not b.queue.items


def test_the_bubble_is_click_through_and_does_not_touch_the_pet_window(qapp):
    from mochi.bubble import SpeechBubble
    from PySide6.QtCore import Qt
    b = SpeechBubble(); b.say("xin chào")
    assert b.testAttribute(Qt.WA_TransparentForMouseEvents) and b.windowFlags() & Qt.WindowTransparentForInput
