"""CPU load, for a pet that feels hot when the machine is busy. psutil is optional: without it the monitor is simply unavailable."""
try:
    import psutil
except ImportError:                                 # optional dependency (pip install "mochi-pet[monitor]")
    psutil = None

AVAILABLE = psutil is not None
POLL_MS = 8000                                      # never per frame: one cheap syscall every few seconds
HOT_ABOVE, COOL_BELOW = 80.0, 65.0                  # the gap between them stops the expression flickering around one threshold


class Hysteresis:
    """on above `hi`, off below `lo`, and unchanged in between"""
    def __init__(self, hi=HOT_ABOVE, lo=COOL_BELOW):
        self.hi, self.lo, self.on = hi, lo, False

    def update(self, v):
        if v > self.hi: self.on = True
        elif v < self.lo: self.on = False
        return self.on


def cpu_percent():
    """CPU use (%) since the previous call, or None without psutil. The first call only primes the counter and reads 0."""
    return psutil.cpu_percent(interval=None) if psutil else None
