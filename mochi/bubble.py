"""Speech bubble: a separate click-through window that follows the pet, so the pet's own 160x160 window and physics never change."""
from collections import deque

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from .physics import FEET, S

MAX_W, PAD, TAIL = 220, 10, 9       # widest text line, inner padding, height of the pointer towards the pet (px)
MAX_QUEUE = 5                       # waiting messages; more than this and the oldest is dropped
GAP_MS = 250                        # pause between two bubbles
MAX_CHARS = 200


def clean_text(text):
    """one line of printable text, at most MAX_CHARS long ("" if nothing usable): what any outside string becomes before display"""
    return " ".join("".join(c if c.isprintable() else " " for c in str(text)).split())[:MAX_CHARS]


MIN_MS, MAX_MS = 2500, 5000         # a message stays up between these (long enough to read, never long enough to bother)


def show_ms(text):
    """how long a message stays up: a base time plus a little per character, between MIN_MS and MAX_MS"""
    return int(min(MAX_MS, max(MIN_MS, 2000 + 60 * len(text))))


def place(px, py, w, h, g, size=S, top=FEET - 106):
    """Top-left of a bubble of size (w, h) for a pet window (side `size`, head top at window-y `top`) at (px, py) on screen
    bounds `g`: above its head, on the right if it fits, else on the left, then kept fully on screen. Returns (x, y, on_right)."""
    head = py + top - 4
    right = px + size / 2 + w <= g.right - 4
    x = px + size / 2 - 24 if right else px + size / 2 + 24 - w   # the tail sits ~24 px off the pet's centre line
    x = max(g.left + 4, min(g.right - w - 4, x))
    y = max(g.top + 4, head - h)
    return x, y, right


class BubbleQueue:
    """Pending messages. Urgent ones jump the line, duplicates of what's already showing or waiting are ignored, and the
    backlog is capped so a chatty sender can never make bubbles pile up."""
    def __init__(self, cap=MAX_QUEUE):
        self.cap, self.items, self.current = cap, deque(), None

    def push(self, text, urgent=False):
        text = clean_text(text)
        if not text or text == self.current or text in self.items: return False
        if urgent: self.items.appendleft(text)
        else: self.items.append(text)
        while len(self.items) > self.cap: self.items.pop() if urgent else self.items.popleft()
        return True

    def next(self):
        self.current = self.items.popleft() if self.items else None
        return self.current

    def clear(self):
        self.items.clear(); self.current = None


class SpeechBubble(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)        # never steals a click from what's underneath
        self.queue, self.on_right, self.lines, self.box = BubbleQueue(), True, "", QRect()
        self.phase = "idle"                                        # idle -> show -> gap -> show ... -> idle
        self.timer = QTimer(self, singleShot=True, timeout=self.advance)   # the only timer

    def say(self, text, urgent=False):
        if self.queue.push(text, urgent) and self.phase == "idle": self.advance()

    def advance(self):
        self.timer.stop()
        if self.phase == "show":                                   # time's up: hide, breathe, then the next one
            self.hide(); self.phase = "gap"; self.timer.start(GAP_MS); return
        text = self.queue.next()
        if text is None:
            self.phase = "idle"; return
        self.phase = "show"
        fm = QFontMetrics(self.font())
        r = fm.boundingRect(QRect(0, 0, MAX_W, 1000), Qt.TextWordWrap, text)
        self.lines, self.box = text, r
        self.resize(r.width() + 2 * PAD + 2, r.height() + 2 * PAD + TAIL + 2)
        self.show(); self.update()
        self.timer.start(show_ms(text))

    def dismiss(self):
        """drop everything (quiet mode, or the pet went to sleep)"""
        self.queue.clear(); self.timer.stop(); self.phase = "idle"; self.hide()

    def follow(self, px, py, g, size=S, top=FEET - 106):
        if not self.isVisible(): return
        x, y, self.on_right = place(px, py, self.width(), self.height(), g, size, top)
        if (int(x), int(y)) != (self.x(), self.y()): self.move(int(x), int(y))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width() - 2, self.height() - 2 - TAIL
        body = QPainterPath(); body.addRoundedRect(QRectF(1, 1, w, h), 10, 10)
        tx = 14 if self.on_right else w - 14 - 12                   # the pointer is on the side nearest the pet
        tail = QPainterPath(QPointF(tx, h)); tail.lineTo(tx + 12, h); tail.lineTo(tx + (3 if self.on_right else 9), h + TAIL)
        tail.closeSubpath()
        p.setPen(QPen(QColor(70, 60, 90), 1.6)); p.setBrush(QColor(255, 252, 248, 240))
        p.drawPath(body.united(tail))
        p.setPen(QColor(50, 42, 70))
        p.drawText(QRect(1 + PAD, 1 + PAD, self.box.width() + 2, self.box.height() + 2), Qt.TextWordWrap, self.lines)
