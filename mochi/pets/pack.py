"""Sprite pet packs: a directory with a `pack.json` and some PNGs. Adding a character needs no code.

pack.json (all lengths in window pixels at scale 1, image coordinates in pixels of body.png):
  id, name         identifier (letters, digits, - _) and the menu label
  size, feet       window side and the y of the floor line; `height` is the drawn height of the body, so top = feet - height
  walk_speed       px/s
  body             RGBA image of the whole figure, standing, its bottom edge on the floor line and centred on the pet
  face             {"box": [x, y, w, h]} where faces are drawn on the body; the body's own face area should be blank
  faces            {"neutral": ["faces/a.png", ...], "talk": [...], "laugh": [...]}: transparent overlays that fill the box.
                   "neutral" is required; a missing kind falls back to "neutral". Ink-style faces: dark strokes on transparency
  fps              {"talk": 10, ...} frames per second of an animated kind (default 8)
  behaviors        {"idle": 4, "walk": 3, "sleep": 1, "chase": 1, "rant": 2, ...} weights; names as in state.BEHAVIOR_NAMES
                   ("sleep" is accepted but never picked at random: sleeping follows the schedule, see sleep.py)
  chatter, scream  what it says now and then / when the ground vanishes
  scold            lines it says while scolding you ("point", "wag", "lecture" in behaviors make it jab and wag a finger at you)
  drop, desktop_remark   what it says when a file is dropped on it / about an item on the desktop; "{name}" stands for the item
  sway, bob        walking waddle: degrees of tilt and pixels of bounce
  looks            "right" (default) or "left": the way the art in body.png faces. It is mirrored so it always looks where it walks
  turn             seconds to turn round when it changes direction (default 0.25; 0 = instantly)
  body_free        {"left": "a.png", "right": "b.png", "both": "c.png"}: the body image again (same size) with the arm(s) that the art tucks
                   behind the back cut away on that side ("left" and "right" as the picture shows them). Used while the character draws
                   its own arm (pointing, holding a sign), so it never has two arms on one side
  ride             {"image": "ride.png", "height": 170, "speed": 2.0, "wheels": [...], "lines": ["Ting ting!", ...]}: while walking it
                   rides this picture (looking the same way as body.png), `speed` times as fast, spinning the wheels (each wheel:
                   x, y, rx, ry of the tyre, rim_x, rim_y, rim_rx, rim_ry of the rim, hub [x, y], avoid [[x, y], ...] a shape over the
                   rim to leave alone), and now and then calling out one of `lines`
  head_bottom      y in body.png pixels where the head ends (chin): while an arm is drawn, the part of the body above it is drawn again
                   on top, so a sleeve passes behind the head instead of over the face. Default 0: no such layer
  shoulders        {"left": [x, y], "right": [x, y]}: where a drawn arm is rooted, in body.png pixels, a little inside the torso's edge so
                   sleeve and body overlap (no gap). Default: a guess on the chest
  work_prop        what it holds while working (Pomodoro): "laptop" (default) or "sign", a red no-entry "BẬN" (busy) sign
"""
import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtGui import QColor, QImage

from ..bubble import clean_text
from ..state import BEHAVIOR_NAMES
from . import PetDef

MAX_JSON = 64 * 1024
MAX_IMAGE = 4096                                # px per side
MAX_FRAMES = 64
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


@dataclass
class Ride:
    image: QImage
    height: float
    speed: float
    wheels: tuple                               # dicts, see the module docstring
    lines: tuple


@dataclass
class SpritePack:
    body: QImage
    height: float
    box: tuple                                  # face box in body pixels: x, y, w, h
    faces: dict = field(default_factory=dict)   # kind -> [QImage]
    fps: dict = field(default_factory=dict)
    sway: float = 4.0
    bob: float = 4.0
    head_bottom: float = 0.0                      # see the module docstring
    shoulders: dict = field(default_factory=dict)  # "left" / "right" -> (x, y) in body pixels; empty: guess
    free: dict = field(default_factory=dict)      # arm-free bodies: "left" / "right" / "both" -> QImage (empty: none)
    ride: "Ride | None" = None                   # the tricycle, if it has one
    masks: dict = field(default_factory=dict)     # cache: (scale, facing) -> exact outline region
    art: int = 1                                  # the way the body image faces: 1 = right, -1 = left
    work_prop: str = "laptop"                     # what it holds while working: "laptop" | "sign" (a red "busy" sign)
    coat: QColor = field(default_factory=lambda: QColor(70, 82, 104))     # its sleeve colour, sampled from the body

    def face(self, kind, t):
        """the overlay for face `kind` at time t: an animated kind steps through its frames, others show their first"""
        frames = self.faces.get(kind) or self.faces["neutral"]
        return frames[int(t * self.fps.get(kind, 8)) % len(frames)] if len(frames) > 1 else frames[0]


def pack_dirs(extra=()):
    """directories that may hold a pack: bundled ones, the user's own, and any `extra`"""
    data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    roots = [Path(__file__).with_name("packs"), data / "mochi-pet" / "pets", *map(Path, extra)]
    return sorted(d for r in roots if r.is_dir() for d in r.iterdir() if (d / "pack.json").is_file())


def _num(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= hi:
        raise ValueError(f"{name} must be a number in [{lo}, {hi}], got {v!r}")
    return float(v)


def _path(root, rel):
    """a file inside the pack directory; anything that resolves outside it (.., absolute, symlink) is refused"""
    p = (root / str(rel)).resolve()
    if root.resolve() not in p.parents: raise ValueError(f"{rel!r} is outside the pack directory")
    return p


def _image(root, rel):
    p = _path(root, rel)
    im = QImage(str(p))
    if im.isNull(): raise ValueError(f"cannot read image {rel!r}")
    if im.width() > MAX_IMAGE or im.height() > MAX_IMAGE: raise ValueError(f"image {rel!r} is too large")
    return im.convertToFormat(QImage.Format_ARGB32_Premultiplied)


WHEEL_KEYS = ("x", "y", "rx", "ry", "rim_x", "rim_y", "rim_rx", "rim_ry")


def load_free(root, j, body):
    """the arm-free bodies ({} if the pack has none); all three must be there and the same size as the body"""
    fj = j.get("body_free")
    if fj is None: return {}
    if not isinstance(fj, dict) or set(fj) != {"left", "right", "both"}: raise ValueError('body_free needs "left", "right" and "both"')
    free = {k: _image(root, v) for k, v in fj.items()}
    if any(im.size() != body.size() for im in free.values()): raise ValueError("body_free images must be the size of body.png")
    return free


def load_ride(root, j):
    """the tricycle (None if the pack has none)"""
    rj = j.get("ride")
    if rj is None: return None
    if not isinstance(rj, dict): raise ValueError("ride must be an object")
    image = _image(root, rj.get("image"))
    wheels = []
    for w in (rj.get("wheels") or [])[:4]:
        if not isinstance(w, dict): raise ValueError("each wheel must be an object")
        wheel = {k: _num(w.get(k), f"wheel.{k}", -4096, 4096) for k in WHEEL_KEYS}
        hub = w.get("hub")
        if not (isinstance(hub, list) and len(hub) == 2): raise ValueError("wheel.hub must be [x, y]")
        wheel["hub"] = tuple(_num(v, "wheel.hub", -4096, 4096) for v in hub)
        avoid = w.get("avoid") or []
        if not (isinstance(avoid, list) and len(avoid) <= 32 and all(isinstance(a, list) and len(a) == 2 for a in avoid)):
            raise ValueError("wheel.avoid must be a list of [x, y] points")
        wheel["avoid"] = tuple((_num(a[0], "wheel.avoid", -4096, 4096), _num(a[1], "wheel.avoid", -4096, 4096)) for a in avoid)
        wheels.append(wheel)
    lines = tuple(c for c in (clean_text(x)[:60] for x in (rj.get("lines") or [])[:20] if isinstance(x, str)) if c)
    height, speed = _num(rj.get("height", 170), "ride.height", 16, 512), _num(rj.get("speed", 1.8), "ride.speed", 1, 6)
    return Ride(image, height, speed, tuple(wheels), lines)


def load_shoulders(j, body):
    sj = j.get("shoulders")
    if sj is None: return {}
    if not isinstance(sj, dict) or set(sj) != {"left", "right"}: raise ValueError('shoulders needs "left" and "right"')
    out = {}
    for k, pt in sj.items():
        if not (isinstance(pt, list) and len(pt) == 2): raise ValueError(f"shoulders.{k} must be [x, y]")
        x, y = _num(pt[0], f"shoulders.{k}", 0, body.width()), _num(pt[1], f"shoulders.{k}", 0, body.height())
        out[k] = (x, y)
    return out


def coat_color(body):
    """the colour of the clothing at the upper arm (an opaque pixel about a quarter of the way in, 60% of the way down), for sleeves"""
    w, h = body.width(), body.height()
    for dx in (0, -0.05, 0.05, -0.1, 0.1, 0.15):
        c = QColor(body.pixel(int((0.25 + dx) * w), int(0.6 * h)))
        if c.alpha() == 255 and 25 < c.lightness() < 225: return c
    return QColor(70, 82, 104)


def load_dir(root):
    """PetDef for the pack in directory `root`; raises ValueError (or OSError) if anything about it is wrong"""
    root = Path(root)
    f = root / "pack.json"
    if f.stat().st_size > MAX_JSON: raise ValueError("pack.json is too large")
    j = json.loads(f.read_text(encoding="utf-8"))
    if not isinstance(j, dict): raise ValueError("pack.json must be an object")
    pid = j.get("id")
    if not isinstance(pid, str) or not ID_RE.match(pid): raise ValueError(f"bad id {pid!r}")
    name = clean_text(j.get("name") or pid)[:40] or pid
    size, feet = int(_num(j.get("size"), "size", 64, 512)), int(_num(j.get("feet"), "feet", 16, 512))
    height = _num(j.get("height"), "height", 16, 512)
    if feet > size or height > feet: raise ValueError("feet must be inside the window and the body must fit above them")
    body = _image(root, j.get("body"))
    box = j.get("face", {}).get("box") if isinstance(j.get("face"), dict) else None
    if not (isinstance(box, list) and len(box) == 4): raise ValueError("face.box must be [x, y, w, h]")
    bx, by, bw, bh = (_num(v, "face.box", 0, MAX_IMAGE) for v in box)
    if bw < 1 or bh < 1 or bx + bw > body.width() or by + bh > body.height(): raise ValueError("face.box is outside the body image")
    faces = {}
    fj = j.get("faces")
    if not isinstance(fj, dict) or not fj.get("neutral"): raise ValueError('faces needs a non-empty "neutral" list')
    for kind, files in fj.items():
        if not isinstance(files, list) or not 0 < len(files) <= MAX_FRAMES:
            raise ValueError(f"faces.{kind} must list 1-{MAX_FRAMES} images")
        faces[str(kind)] = [_image(root, x) for x in files]
    fps = {str(k): _num(v, "fps", 1, 60) for k, v in (j.get("fps") or {}).items()}
    weights = {}
    for k, v in (j.get("behaviors") or {}).items():
        if k not in BEHAVIOR_NAMES: raise ValueError(f"unknown behaviour {k!r}")
        w = _num(v, f"behaviors.{k}", 0, 100)
        if w > 0: weights[BEHAVIOR_NAMES[k]] = w
    if len(weights) < 2 or BEHAVIOR_NAMES["idle"] not in weights: raise ValueError('behaviors needs "idle" and at least one more')
    chatter = tuple(c for c in (clean_text(x) for x in (j.get("chatter") or [])[:50] if isinstance(x, str)) if c)
    sway, bob = _num(j.get("sway", 4), "sway", 0, 20), _num(j.get("bob", 4), "bob", 0, 30)
    prop = j.get("work_prop", "laptop")
    if prop not in ("laptop", "sign"): raise ValueError(f"work_prop must be laptop or sign, got {prop!r}")
    looks = j.get("looks", "right")
    if looks not in ("left", "right"): raise ValueError(f"looks must be left or right, got {looks!r}")
    turn = _num(j.get("turn", 0.25), "turn", 0, 2)
    pack = SpritePack(body, height, (bx, by, bw, bh), faces, fps, sway, bob, art=-1 if looks == "left" else 1, work_prop=prop,
                      coat=coat_color(body), free=load_free(root, j, body), ride=load_ride(root, j),
                      shoulders=load_shoulders(j, body), head_bottom=_num(j.get("head_bottom", 0), "head_bottom", 0, body.height()))
    scold = tuple(c for c in (clean_text(x)[:80] for x in (j.get("scold") or [])[:30] if isinstance(x, str)) if c)
    text = {k: clean_text(j.get(k) or "")[:80] or dflt for k, dflt in (("drop", PetDef.drop), ("desktop_remark", PetDef.desktop_remark))}
    return PetDef(pid, name, "sprite", size, feet, feet - int(height), _num(j.get("walk_speed", 45), "walk_speed", 5, 400), weights,
                  chatter or ("...",), clean_text(j.get("scream") or "Á!")[:20] or "Á!", drop=text["drop"], scold=scold,
                  desktop_remark=text["desktop_remark"], pack=pack, turn_s=turn, ride_speed=pack.ride.speed if pack.ride else 1.0)
