"""Galaxy Buds model table: SPP UUID, display name, and capability flags."""

from __future__ import annotations

from dataclasses import dataclass

SPP_STANDARD = "00001101-0000-1000-8000-00805f9b34fb"
SPP_NEW = "2e73a4ad-332d-41fc-90e2-16bef06523f2"

FEATURE_ANC = "anc"
FEATURE_AMBIENT = "ambient"
FEATURE_ADAPTIVE = "adaptive"
FEATURE_EQ = "eq"
FEATURE_FIND = "find"
FEATURE_TOUCH_LOCK = "touch_lock"
FEATURE_GAMING = "gaming"
FEATURE_ONEBUD = "onebud"
FEATURE_VOICE_DETECT = "voice_detect"
FEATURE_AMBIENT_VOLUME = "ambient_volume"
FEATURE_CASE = "case"

EQ_PRESETS = ("bass", "soft", "dynamic", "clear", "treble")
NOISE_MODES = ("off", "anc", "ambient", "adaptive")
MODE_TO_BYTE = {"off": 0, "anc": 1, "ambient": 2, "adaptive": 3}
BYTE_TO_MODE = {value: name for name, value in MODE_TO_BYTE.items()}
EQ_TO_BYTE = {name: index for index, name in enumerate(EQ_PRESETS)}
BYTE_TO_EQ = {index: name for index, name in enumerate(EQ_PRESETS)}

# Device color IDs from the extended-status payload (little-endian int16).
COLOR_TO_MODEL = {
    257: "Buds",
    258: "BudsPlus",
    259: "BudsPlus",
    260: "BudsPlus",
    261: "BudsPlus",
    262: "BudsPlus",
    263: "BudsPlus",
    264: "BudsPlus",
    265: "BudsPlus",
    266: "BudsPlus",
    278: "BudsLive",
    279: "BudsLive",
    280: "BudsLive",
    281: "BudsLive",
    282: "BudsLive",
    283: "BudsLive",
    284: "BudsLive",
    298: "BudsPro",
    299: "BudsPro",
    300: "BudsPro",
    301: "BudsPro",
    313: "Buds2",
    314: "Buds2",
    315: "Buds2",
    316: "Buds2",
    317: "Buds2",
    318: "Buds2",
    319: "Buds2",
    320: "Buds2",
    321: "Buds2",
    322: "BudsCore",
    323: "BudsCore",
    325: "Buds2Pro",
    326: "Buds2Pro",
    327: "Buds2Pro",
    328: "Buds2Pro",
    330: "BudsFe",
    331: "BudsFe",
    333: "Buds3",
    334: "Buds3",
    340: "Buds3Pro",
    341: "Buds3Pro",
    347: "Buds3Fe",
    348: "Buds3Fe",
    355: "Buds4",
    356: "Buds4",
    359: "Buds4Pro",
    360: "Buds4Pro",
    361: "Buds4Pro",
}

SKU_PREFIXES = (
    ("SM-R640", "Buds4Pro"),
    ("SM-R540", "Buds4"),
    ("SM-R630", "Buds3Pro"),
    ("SM-R530", "Buds3"),
    ("SM-R420", "Buds3Fe"),
    ("SM-R410", "BudsCore"),
    ("SM-R400", "BudsFe"),
    ("SM-R510", "Buds2Pro"),
    ("SM-R177", "Buds2"),
    ("SM-R190", "BudsPro"),
    ("SM-R180", "BudsLive"),
    ("SM-R175", "BudsPlus"),
    ("SM-R170", "Buds"),
    ("R400N", "BudsFe"),
    ("R400", "BudsFe"),
    ("R640", "Buds4Pro"),
    ("R540", "Buds4"),
    ("R630", "Buds3Pro"),
    ("R530", "Buds3"),
    ("R420", "Buds3Fe"),
    ("R410", "BudsCore"),
    ("R510", "Buds2Pro"),
    ("R177", "Buds2"),
    ("R190", "BudsPro"),
    ("R180", "BudsLive"),
    ("R175", "BudsPlus"),
    ("R170", "Buds"),
)

# Longer, more specific names first so "Buds2 Pro" does not become "Buds2".
NAME_HINTS = (
    ("buds4 pro", "Buds4Pro"),
    ("buds 4 pro", "Buds4Pro"),
    ("buds4", "Buds4"),
    ("buds 4", "Buds4"),
    ("buds3 pro", "Buds3Pro"),
    ("buds 3 pro", "Buds3Pro"),
    ("buds3 fe", "Buds3Fe"),
    ("buds 3 fe", "Buds3Fe"),
    ("buds3", "Buds3"),
    ("buds 3", "Buds3"),
    ("buds2 pro", "Buds2Pro"),
    ("buds 2 pro", "Buds2Pro"),
    ("buds2", "Buds2"),
    ("buds 2", "Buds2"),
    ("buds fe", "BudsFe"),
    ("buds core", "BudsCore"),
    ("buds live", "BudsLive"),
    ("buds pro", "BudsPro"),
    ("buds+", "BudsPlus"),
    ("buds plus", "BudsPlus"),
    ("galaxy buds", "Buds"),
)


@dataclass(frozen=True)
class ModelSpec:
    key: str
    name: str
    sku: str
    spp_uuid: str
    features: frozenset[str]
    max_ambient_volume: int = 2
    generation: str = "live"  # buds | plus | live | pro | buds2 | fe | buds3


_CORE = frozenset(
    {
        FEATURE_EQ,
        FEATURE_FIND,
        FEATURE_TOUCH_LOCK,
        FEATURE_CASE,
    }
)
_NOISE = _CORE | frozenset({FEATURE_ANC, FEATURE_AMBIENT, FEATURE_AMBIENT_VOLUME, FEATURE_GAMING})
_ONEBUD = _NOISE | frozenset({FEATURE_ONEBUD})
_VOICE = _ONEBUD | frozenset({FEATURE_VOICE_DETECT})
_ADAPTIVE = _VOICE | frozenset({FEATURE_ADAPTIVE})

SPECS: dict[str, ModelSpec] = {
    "Buds": ModelSpec(
        "Buds",
        "Galaxy Buds",
        "SM-R170",
        SPP_STANDARD,
        frozenset({FEATURE_AMBIENT, FEATURE_EQ, FEATURE_FIND, FEATURE_TOUCH_LOCK, FEATURE_AMBIENT_VOLUME}),
        5,
        "buds",
    ),
    "BudsPlus": ModelSpec(
        "BudsPlus",
        "Galaxy Buds+",
        "SM-R175",
        SPP_STANDARD,
        _CORE | frozenset({FEATURE_AMBIENT, FEATURE_AMBIENT_VOLUME, FEATURE_GAMING}),
        2,
        "plus",
    ),
    "BudsLive": ModelSpec(
        "BudsLive",
        "Galaxy Buds Live",
        "SM-R180",
        SPP_STANDARD,
        _CORE | frozenset({FEATURE_ANC, FEATURE_GAMING}),
        0,
        "live",
    ),
    "BudsPro": ModelSpec(
        "BudsPro",
        "Galaxy Buds Pro",
        "SM-R190",
        SPP_STANDARD,
        _VOICE,
        2,
        "pro",
    ),
    "Buds2": ModelSpec("Buds2", "Galaxy Buds2", "SM-R177", SPP_NEW, _ONEBUD, 2, "buds2"),
    "Buds2Pro": ModelSpec(
        "Buds2Pro", "Galaxy Buds2 Pro", "SM-R510", SPP_NEW, _VOICE, 2, "buds2"
    ),
    "BudsFe": ModelSpec("BudsFe", "Galaxy Buds FE", "SM-R400N", SPP_NEW, _VOICE, 2, "fe"),
    "BudsCore": ModelSpec(
        "BudsCore", "Galaxy Buds Core", "SM-R410", SPP_NEW, _ONEBUD, 2, "fe"
    ),
    "Buds3": ModelSpec("Buds3", "Galaxy Buds3", "SM-R530", SPP_NEW, _ADAPTIVE, 2, "buds3"),
    "Buds3Fe": ModelSpec(
        "Buds3Fe", "Galaxy Buds3 FE", "SM-R420", SPP_NEW, _VOICE, 2, "fe"
    ),
    "Buds3Pro": ModelSpec(
        "Buds3Pro", "Galaxy Buds3 Pro", "SM-R630", SPP_NEW, _ADAPTIVE, 2, "buds3"
    ),
    "Buds4": ModelSpec("Buds4", "Galaxy Buds4", "SM-R540", SPP_NEW, _ADAPTIVE, 2, "buds3"),
    "Buds4Pro": ModelSpec(
        "Buds4Pro", "Galaxy Buds4 Pro", "SM-R640", SPP_NEW, _ADAPTIVE, 2, "buds3"
    ),
}

UNKNOWN = ModelSpec(
    "Unknown",
    "Galaxy Buds",
    "",
    SPP_NEW,
    _CORE | frozenset({FEATURE_ANC, FEATURE_AMBIENT, FEATURE_GAMING, FEATURE_AMBIENT_VOLUME}),
    2,
    "fe",
)


def spec_for(key: str | None) -> ModelSpec:
    if not key:
        return UNKNOWN
    return SPECS.get(key, UNKNOWN)


def identify_from_color(color: int) -> str | None:
    return COLOR_TO_MODEL.get(color)


def identify_from_sku(text: str) -> str | None:
    upper = text.upper()
    for prefix, key in SKU_PREFIXES:
        if prefix in upper:
            return key
    return None


def identify_from_name(name: str) -> str | None:
    lowered = name.lower()
    for hint, key in NAME_HINTS:
        if hint in lowered:
            return key
    if "buds" in lowered:
        return None
    return None


def looks_like_buds(name: str) -> bool:
    lowered = name.lower()
    return "buds" in lowered or "galaxy bud" in lowered


def noise_modes_for(spec: ModelSpec) -> tuple[str, ...]:
    modes: list[str] = ["off"]
    if FEATURE_ANC in spec.features:
        modes.append("anc")
    if FEATURE_AMBIENT in spec.features:
        modes.append("ambient")
    if FEATURE_ADAPTIVE in spec.features:
        modes.append("adaptive")
    return tuple(modes)


def eq_name(value: int | None) -> str | None:
    if value is None:
        return None
    index = value - 5 if value >= 5 else value
    return BYTE_TO_EQ.get(index)


def eq_byte(name: str) -> int | None:
    return EQ_TO_BYTE.get(name)
