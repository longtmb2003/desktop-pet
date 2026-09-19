"""Where the other windows' rects come from."""
from collections.abc import Callable


class Platform:
    """The base knows no windows, so the pet just walks on the screen floor."""

    def __init__(self, on_windows: Callable[[dict], None]):
        self.on_windows = on_windows        # called with {id: (x, y, w, h)}, ordered bottom -> top

    def start(self) -> None:
        pass
