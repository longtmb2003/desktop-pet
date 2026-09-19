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
  chatter, scream  what it says now and then / when the ground vanishes
  drop, desktop_remark   what it says when a file is dropped on it / about an item on the desktop; "{name}" stands for the item
  sway, bob        walking waddle: degrees of tilt and pixels of bounce
"""
import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtGui import QImage

from ..bubble import clean_text
from ..state import BEHAVIOR_NAMES
from . import PetDef

MAX_JSON = 64 * 1024
MAX_IMAGE = 4096                                # px per side
MAX_FRAMES = 64
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


@dataclass
class SpritePack:
    body: QImage
    height: float
    box: tuple                                  # face box in body pixels: x, y, w, h
    faces: dict = field(default_factory=dict)   # kind -> [QImage]
    fps: dict = field(default_factory=dict)
    sway: float = 4.0
    bob: float = 4.0
    masks: dict = field(default_factory=dict)     # cache: (scale, facing) -> exact outline region

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
    pack = SpritePack(body, height, (bx, by, bw, bh), faces, fps, sway, bob)
    text = {k: clean_text(j.get(k) or "")[:80] or dflt for k, dflt in (("drop", PetDef.drop), ("desktop_remark", PetDef.desktop_remark))}
    return PetDef(pid, name, "sprite", size, feet, feet - int(height), _num(j.get("walk_speed", 45), "walk_speed", 5, 400), weights,
                  chatter or ("...",), clean_text(j.get("scream") or "Á!")[:20] or "Á!", text["drop"], text["desktop_remark"], pack)
