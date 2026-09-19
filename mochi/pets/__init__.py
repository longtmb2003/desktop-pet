"""Pet definitions: everything that makes one character different from another, as data.

A definition says how big the pet is, how it moves, what it tends to do, what it says and how it is drawn ("vector": painted in
code, like Mochi; "sprite": images from a pack directory, see pack.py). Behaviour code never checks *which* pet it is."""
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ..state import BEHAVIORS

log = logging.getLogger("mochi")


@dataclass(frozen=True)
class PetDef:
    id: str
    name: str                                   # as shown in the menu
    kind: str = "vector"                        # "vector" | "sprite"
    size: int = 160                             # window side (px) at scale 1.0
    feet: int = 146                             # window-y of the floor line
    top: int = 40                               # window-y of the top of the head (the ceiling stops it there)
    walk_speed: float = 55.0                    # px/s at scale 1.0
    behaviors: Mapping = field(default_factory=lambda: dict(BEHAVIORS))     # (motion, action) -> weight: what it does next
    chatter: tuple = ("Meo~",)                  # things it says now and then
    scream: str = "Á!"                          # what it yells when the ground vanishes
    turn_s: float = 0.0                         # seconds it takes to turn round when it changes direction (0: at once)
    drop: str = "Nom nom! {name} ngon quá!"     # what it says when something is dropped on it ({name}: what)
    desktop_remark: str = "{name} nằm đó lâu rồi nhỉ?"     # an idle remark about something on the desktop
    pack: Any = None                            # the SpritePack of a sprite pet

    @property
    def height(self):
        return self.feet - self.top


MOCHI = PetDef(
    "mochi", "Mochi",
    chatter=("Meo~", "Bạn uống nước chưa?", "Nghỉ mắt một chút nhé!", "Mochi ở đây nè", "Nhớ lưu file nha", "Vươn vai một cái đi!"))


def available(extra_dirs=()):
    """{id: PetDef}: Mochi, plus every valid pack found in the built-in packs directory and `extra_dirs`.
    A broken pack is skipped with a warning, never fatal."""
    from .pack import load_dir, pack_dirs
    pets = {MOCHI.id: MOCHI}
    for d in pack_dirs(extra_dirs):
        try:
            p = load_dir(d)
        except Exception as e:                   # a bad pack (missing image, bad JSON, wrong types) must not stop Mochi starting
            log.warning("skipping pet pack %s: %s", d, e)
            continue
        if p.id in pets: log.warning("skipping pet pack %s: id %r is already taken", d, p.id)
        else: pets[p.id] = p
    return pets
