"""Modes: named bundles of settings (plus a leaning towards some behaviours), switched in one click. Built-in ones, and the user's
own, saved from the current settings. Pure data and validation: the pet applies them."""
import json
from dataclasses import dataclass, field

from .bubble import clean_text
from .state import BEHAVIOR_NAMES

KEYS = ("activity", "speed", "chase", "chatter", "time_of_day", "sound", "quiet", "mischief")   # what a mode sets: always all of them
DEFAULTS = {"activity": 1.0, "speed": 1.0, "chase": True, "chatter": True, "time_of_day": True, "sound": True, "quiet": False,
            "mischief": True}
RANGES = {"activity": (0.3, 3.0), "speed": (0.3, 3.0)}
STAYS = ("sleep", "work")                       # what a mode may keep the pet doing all the time
MAX_CUSTOM, MAX_NAME = 12, 30


@dataclass(frozen=True)
class Mode:
    id: str
    name: str
    values: dict = field(default_factory=lambda: dict(DEFAULTS), compare=False, hash=False)
    boost: dict = field(default_factory=dict, compare=False, hash=False)       # behaviour name -> factor on its weight
    stay: str = ""                               # "" | "sleep" | "work"
    builtin: bool = True


def make(id, name, stay="", boost=None, builtin=True, **over):
    return Mode(id, name, {**DEFAULTS, **over}, boost or {}, stay, builtin)


BUILTIN = {m.id: m for m in (
    make("normal", "Bình thường"),
    make("work", "Làm việc", stay="work", activity=0.5, speed=0.8, chase=False, chatter=False, mischief=False),
    make("play", "Chơi đùa", boost={"chase": 4, "walk": 2}, activity=2.0, speed=1.5, chatter=True),
    make("sleep", "Ngủ", stay="sleep", activity=0.5, chatter=False, sound=False, mischief=False),
    make("quiet", "Yên lặng", boost={"idle": 2}, activity=0.6, chatter=False, sound=False, quiet=True, mischief=False),
)}


def clean_values(d):
    """a full, in-range set of mode values from an untrusted dict: missing or wrong-typed entries take the default"""
    out = dict(DEFAULTS)
    for k in KEYS:
        v = d.get(k, DEFAULTS[k]) if isinstance(d, dict) else DEFAULTS[k]
        if isinstance(DEFAULTS[k], bool):
            out[k] = v if isinstance(v, bool) else DEFAULTS[k]
        elif isinstance(v, (int, float)) and not isinstance(v, bool) and v == v:
            lo, hi = RANGES[k]; out[k] = max(lo, min(hi, float(v)))
    return out


def clean_boost(d):
    if not isinstance(d, dict): return {}
    return {k: float(v) for k, v in d.items()
            if k in BEHAVIOR_NAMES and isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 20}


def parse_custom(raw):
    """{id: Mode} of the user's own modes from the JSON in Settings; junk is skipped, nothing raises. Ids look like "custom:<name>"."""
    try:
        data = json.loads(raw) if raw else {}
    except ValueError:
        return {}
    out = {}
    for name, d in list((data if isinstance(data, dict) else {}).items())[:MAX_CUSTOM]:
        name = clean_text(name)[:MAX_NAME]
        if not name or not isinstance(d, dict): continue
        stay = d.get("stay", "")
        out[f"custom:{name}"] = Mode(f"custom:{name}", name, clean_values(d.get("values")), clean_boost(d.get("boost")),
                                     stay if stay in STAYS else "", False)
    return out


def dump_custom(modes):
    return json.dumps({m.name: {"values": m.values, "boost": m.boost, "stay": m.stay} for m in modes.values() if not m.builtin},
                      ensure_ascii=False)


def available(raw):
    """every mode by id: the built-in ones, then the user's own"""
    return {**BUILTIN, **parse_custom(raw)}


def snapshot(name, current_values, base=None):
    """a new custom Mode holding `current_values`; it inherits the boosts and 'stay' of `base`, the mode being used, if any"""
    name = clean_text(name)[:MAX_NAME]
    if not name: raise ValueError("empty name")
    return Mode(f"custom:{name}", name, clean_values(current_values), dict(base.boost) if base else {}, base.stay if base else "", False)


def weights(behaviors, boost):
    """`behaviors` ({(motion, action): weight}) with the mode's factors applied"""
    if not boost: return behaviors
    return {k: w * next((boost[n] for n, key in BEHAVIOR_NAMES.items() if key == k and n in boost), 1.0) for k, w in behaviors.items()}
