import math

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QImage, QPainter

from mochi import limbs
from mochi.limbs import DIGITS, draw_arm, draw_hand, two_link


def length(a, b):
    return math.hypot(a.x() - b.x(), a.y() - b.y())


@pytest.mark.parametrize("target", [(30, 40), (-30, 40), (20, -10), (0, 60), (50, 0), (1, 1), (0, 0)])
def test_the_segments_keep_their_lengths_and_the_hand_reaches_the_target_when_it_can(target):
    s, t = QPointF(0, 0), QPointF(*target)
    elbow, wrist = two_link(s, t, 36, 34)
    assert length(s, elbow) == pytest.approx(36, abs=1e-6) and length(elbow, wrist) == pytest.approx(34, abs=1e-6)
    if 2.5 < length(s, t) < 69.5: assert length(wrist, t) < 1e-6                     # within reach: it gets there


def test_an_arm_stretches_straight_at_a_target_out_of_reach():
    elbow, wrist = two_link(QPointF(0, 0), QPointF(300, 0), 36, 34)
    assert wrist.x() == pytest.approx(69.5) and abs(wrist.y()) < 1e-9 and abs(elbow.y()) < 6         # (all but) straight along the line
    assert length(QPointF(0, 0), wrist) <= 70


def test_the_elbow_sticks_out_for_a_raised_hand_and_a_folded_hanging_arm():
    elbow, _ = two_link(QPointF(28, -100), QPointF(30, -160), 36, 34)                # hand above the shoulder: elbow out to the side
    assert elbow.x() > 28 + 10 and -140 < elbow.y() < -120
    for side in (1, -1):                                                              # hand just below the shoulder, arm folded
        elbow, _ = two_link(QPointF(side * 28, -106), QPointF(side * 24, -82), 36, 34)
        assert abs(elbow.x()) > 28 + 15                                               # the elbow sticks out, away from the body


def test_no_two_attempts_disagree_and_nothing_is_nan_at_the_edges():
    for t in ((0, 0), (0.0001, 0), (0, 69.4), (0, 2.5), (1e9, 1e9), (-1e9, 3)):
        e, w = two_link(QPointF(0, 0), QPointF(*t), 36, 34)
        assert all(math.isfinite(v) for v in (e.x(), e.y(), w.x(), w.y()))


@pytest.mark.parametrize("kind", ["point", "open", "grip"])
def test_every_hand_has_a_thumb_and_four_fingers(kind):
    assert [d[0] for d in DIGITS[kind]] == ["thumb", "index", "middle", "ring", "pinky"]
    assert all(d[4] > 0 and d[5] > 0 for d in DIGITS[kind])


def test_pointing_puts_the_index_out_and_curls_the_rest_while_an_open_hand_spreads_all_five():
    point = {d[0]: d for d in DIGITS["point"]}
    curled = max(point[k][4] for k in ("middle", "ring", "pinky"))
    assert point["index"][4] > 3 * curled                                                            # the index far outreaches the curled
    spread = [d[3] for d in DIGITS["open"][1:]]
    assert spread == sorted(spread) and spread[-1] - spread[0] > 30                                # the four fingers fan out
    lengths = [d[4] for d in DIGITS["open"][1:]]
    assert min(lengths) > 8                                                                          # all of them are long


def paint(fn, size=90):
    img = QImage(size, size, QImage.Format_ARGB32); img.fill(0)
    p = QPainter(img); p.setRenderHint(QPainter.Antialiasing); fn(p); p.end()
    return img


def skin_pixels(img):
    return sum(1 for y in range(img.height()) for x in range(img.width()) if img.pixelColor(x, y).rgb() == limbs.SKIN.rgb())


@pytest.mark.parametrize("kind", ["point", "open", "grip"])
def test_a_hand_draws_in_skin_with_an_outline_and_they_look_different(kind):
    img = paint(lambda p: draw_hand(p, QPointF(20, 45), 0.0, kind))
    assert skin_pixels(img) > 100
    outline = sum(1 for y in range(90) for x in range(90) if img.pixelColor(x, y).alpha() > 200 and img.pixelColor(x, y).lightness() < 80)
    assert outline > 40                                                                              # a dark outline round the shapes


def test_the_three_hands_are_three_different_pictures():
    imgs = {k: bytes(paint(lambda p, k=k: draw_hand(p, QPointF(20, 45), 0.0, k)).constBits()) for k in ("point", "open", "grip")}
    assert len(set(imgs.values())) == 3


def test_a_hand_turns_with_the_forearm():
    def tip(angle):
        img = paint(lambda p: draw_hand(p, QPointF(45, 45), angle, "point"))
        pts = [(x, y) for y in range(90) for x in range(90) if img.pixelColor(x, y).alpha() > 100]
        return max(pts, key=lambda q: math.hypot(q[0] - 45, q[1] - 45))                              # the farthest pixel: the fingertip
    right, down, up = tip(0), tip(math.pi / 2), tip(-math.pi / 2)
    assert right[0] > 60 and abs(right[1] - 45) < 12 and down[1] > 60 and up[1] < 30


def test_an_arm_is_sleeve_elbow_cuff_and_hand_and_it_reports_where_they_are():
    coat = QColor(70, 82, 104)
    holder = {}

    def go(p):
        holder["w"], holder["e"] = draw_arm(p, coat, QPointF(15, 20), QPointF(60, 60), 14, "open", 36, 34)
    img = paint(go, 100)
    wrist, elbow = holder["w"], holder["e"]
    assert length(wrist, QPointF(60, 60)) < 1e-6 and length(QPointF(15, 20), elbow) == pytest.approx(36, abs=1e-6)
    assert any(img.pixelColor(x, y).rgb() == coat.rgb() for y in range(100) for x in range(100))       # sleeve colour
    assert any(img.pixelColor(x, y).rgb() == limbs.CUFF.rgb() for y in range(100) for x in range(100))  # the cuff at the wrist
    assert skin_pixels(img) > 100                                                                        # and a hand
