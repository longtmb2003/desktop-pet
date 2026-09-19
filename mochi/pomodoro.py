"""Pomodoro timer: pure logic with an injectable clock, no Qt. focus -> break -> off; the pet polls it once per frame."""
import time


class Pomodoro:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.phase, self.paused = "off", False          # phase: "off" | "focus" | "break"
        self.ends = self.left = 0.0                     # `ends`: clock time the phase ends; `left`: seconds remaining while paused
        self.break_s = 300.0

    @property
    def active(self): return self.phase != "off"

    @property
    def focusing(self): return self.phase == "focus" and not self.paused

    def start(self, focus_s, break_s):
        self.phase, self.paused, self.break_s = "focus", False, float(break_s)
        self.ends = self.clock() + focus_s

    def pause(self):
        if self.active and not self.paused: self.left, self.paused = max(0.0, self.ends - self.clock()), True

    def resume(self):
        if self.active and self.paused: self.ends, self.paused = self.clock() + self.left, False

    def reset(self):
        self.phase, self.paused = "off", False

    def remaining(self):
        if not self.active: return 0.0
        return self.left if self.paused else max(0.0, self.ends - self.clock())

    def poll(self):
        """advance the phase if its time is up; returns "focus_done" / "break_done" once, else None"""
        if not self.active or self.paused or self.clock() < self.ends: return None
        if self.phase == "focus":
            self.phase, self.ends = "break", self.ends + self.break_s     # the break starts where the focus ended, not when we noticed
            return "focus_done"
        self.phase = "off"
        return "break_done"

    def label(self):
        m, s = divmod(int(self.remaining() + 0.999), 60)
        name = {"focus": "Tập trung", "break": "Nghỉ"}.get(self.phase, "")
        return f"{name} {m:02d}:{s:02d}" + (" (tạm dừng)" if self.paused else "") if self.active else "Pomodoro: tắt"
