"""Samsung Galaxy Buds RFCOMM frames: CRC, encode, decode, status parse."""

from __future__ import annotations

from dataclasses import dataclass, field

from . import models

SOM_LEGACY = 0xFE
EOM_LEGACY = 0xEE
SOM_NEW = 0xFD
EOM_NEW = 0xDD
# Aliases kept for tests and callers that still say SOM/EOM.
SOM = SOM_NEW
EOM = EOM_NEW
TYPE_REQUEST = 0
TYPE_RESPONSE = 1
HEADER_RESPONSE = 0x1000
HEADER_FRAGMENT = 0x2000
HEADER_SIZE_MASK = 0x3FF

EXTENDED_STATUS_UPDATED = 97
STATUS_UPDATED = 96
VERSION_INFO = 99
DEBUG_SKU = 34
MANAGER_INFO = 136
EQUALIZER = 134
LOCK_TOUCHPAD = 144
SET_AMBIENT_MODE = 128
AMBIENT_VOLUME = 132
AMBIENT_MODE_UPDATED = 129
ADJUST_SOUND_SYNC = 133
FIND_MY_EARBUDS_START = 160
FIND_MY_EARBUDS_STOP = 161
NOISE_CONTROLS = 120
NOISE_CONTROLS_UPDATE = 119
SET_NOISE_REDUCTION = 152
SET_DETECT_CONVERSATIONS = 122
SET_ONE_EARBUD_ANC = 158
MUTE_EARBUD_STATUS_UPDATED = 163

PLACEMENT = {
    0: "disconnected",
    1: "wearing",
    2: "idle",
    3: "in_case",
    4: "in_case",
    100: "in_case",
}

ACK_IDS = {EXTENDED_STATUS_UPDATED, STATUS_UPDATED, VERSION_INFO}


def crc16(data: bytes) -> int:
    """Samsung accessory CRC-16 (CCITT-style nibble algorithm)."""
    crc = 0
    for byte in data:
        crc = ((crc >> 8) | (crc << 8)) & 0xFFFF
        crc ^= byte
        crc ^= (crc & 0xFF) >> 4
        crc ^= (crc << 12) & 0xFFFF
        crc ^= ((crc & 0xFF) << 5) & 0xFFFF
    return crc & 0xFFFF


def uses_legacy_header(spec: models.ModelSpec | None) -> bool:
    return spec is not None and spec.generation == "buds"


def encode(
    msg_id: int,
    payload: bytes = b"",
    msg_type: int = TYPE_REQUEST,
    *,
    legacy: bool = False,
) -> bytes:
    body = bytes([msg_id]) + payload
    checksum = crc16(body)
    size = len(payload) + 3
    if legacy:
        return (
            bytes([SOM_LEGACY, msg_type, size, msg_id])
            + payload
            + checksum.to_bytes(2, "little")
            + bytes([EOM_LEGACY])
        )
    header = size & HEADER_SIZE_MASK
    if msg_type == TYPE_RESPONSE:
        header |= HEADER_RESPONSE
    return (
        bytes([SOM_NEW])
        + header.to_bytes(2, "little")
        + bytes([msg_id])
        + payload
        + checksum.to_bytes(2, "little")
        + bytes([EOM_NEW])
    )


def _frame_size(packet: bytes) -> int | None:
    if len(packet) < 4:
        return None
    if packet[0] == SOM_LEGACY:
        return packet[2]
    if packet[0] == SOM_NEW:
        return int.from_bytes(packet[1:3], "little") & HEADER_SIZE_MASK
    return None


def decode_frame(packet: bytes) -> tuple[int, int, bytes] | None:
    """Return (type, msg_id, payload) or None if the packet is not a complete frame."""
    if len(packet) < 7:
        return None
    size = _frame_size(packet)
    if size is None or len(packet) != size + 4:
        return None
    if packet[0] == SOM_LEGACY:
        if packet[-1] != EOM_LEGACY:
            return None
        msg_type = packet[1]
    elif packet[0] == SOM_NEW:
        if packet[-1] != EOM_NEW:
            return None
        header = int.from_bytes(packet[1:3], "little")
        msg_type = TYPE_RESPONSE if header & HEADER_RESPONSE else TYPE_REQUEST
    else:
        return None
    msg_id = packet[3]
    payload = packet[4 : 4 + size - 3]
    checksum = int.from_bytes(packet[4 + len(payload) : 6 + len(payload)], "little")
    if crc16(bytes([msg_id]) + payload) != checksum:
        return None
    return msg_type, msg_id, payload


def _next_som(buffer: bytes) -> int:
    start_new = buffer.find(bytes([SOM_NEW]))
    start_legacy = buffer.find(bytes([SOM_LEGACY]))
    if start_new < 0:
        return start_legacy
    if start_legacy < 0:
        return start_new
    return min(start_new, start_legacy)


class FrameReader:
    """Accumulate a byte stream into complete SPP frames (legacy FE/EE or FE-family FD/DD)."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    def reset(self) -> None:
        self._buffer.clear()

    def feed(self, chunk: bytes) -> list[bytes]:
        self._buffer.extend(chunk)
        frames: list[bytes] = []
        while True:
            start = _next_som(self._buffer)
            if start < 0:
                self._buffer.clear()
                return frames
            if start:
                del self._buffer[:start]
            if len(self._buffer) < 4:
                return frames
            size = _frame_size(self._buffer)
            if size is None:
                del self._buffer[0]
                continue
            total = size + 4
            if len(self._buffer) < total:
                return frames
            candidate = bytes(self._buffer[:total])
            decoded = decode_frame(candidate)
            if decoded is None:
                del self._buffer[0]
                continue
            del self._buffer[:total]
            frames.append(candidate)
        return frames


def _u8(payload: bytes, index: int, default: int | None = None) -> int | None:
    if index < 0 or index >= len(payload):
        return default
    return payload[index]


def _bool(payload: bytes, index: int) -> bool | None:
    value = _u8(payload, index)
    if value is None:
        return None
    return value == 1


def _placement(nibble: int) -> str:
    return PLACEMENT.get(nibble, "idle")


def _battery(value: int | None) -> int | None:
    if value is None or value > 100:
        return None
    return value


def _eq(value: int | None) -> str | None:
    return models.eq_name(value)


def _color(payload: bytes, index: int) -> int | None:
    if index + 1 >= len(payload):
        return None
    return int.from_bytes(payload[index : index + 2], "little")


def empty_state() -> dict:
    return {
        "connected": False,
        "address": "",
        "name": None,
        "model": None,
        "sku": None,
        "mode": None,
        "battery": {"left": None, "right": None, "case": None},
        "charging": {"left": False, "right": False, "case": False},
        "ear": None,
        "eq": None,
        "touch_lock": None,
        "voice_detect": None,
        "onebud": None,
        "gaming": None,
        "ambient_volume": None,
        "finding": False,
        "features": [],
    }


def apply_spec(state: dict, spec: models.ModelSpec) -> None:
    state["model"] = spec.key
    if not state.get("name"):
        state["name"] = spec.name
    if spec.sku and not state.get("sku"):
        state["sku"] = spec.sku
    state["features"] = sorted(spec.features)


def connected_preview(
    address: str, name: str, spec: models.ModelSpec, battery_percent: int | None = None
) -> dict:
    """Bar-visible state from BlueZ before the SPP session is up."""
    state = empty_state()
    state["connected"] = True
    state["address"] = address
    state["name"] = name
    apply_spec(state, spec)
    if battery_percent is not None and battery_percent <= 100:
        state["battery"]["left"] = battery_percent
        state["battery"]["right"] = battery_percent
    return state


def _set_ear(state: dict, left: str, right: str) -> None:
    state["ear"] = [left, right]


def parse_extended_status(payload: bytes, spec: models.ModelSpec, state: dict) -> None:
    """Fold an EXTENDED_STATUS_UPDATED payload into state."""
    if len(payload) < 8:
        return
    generation = spec.generation
    state["battery"]["left"] = _battery(_u8(payload, 2))
    state["battery"]["right"] = _battery(_u8(payload, 3))

    if generation == "buds":
        wear = _u8(payload, 6) or 0
        left = "wearing" if wear in (1, 17) else "idle"
        right = "wearing" if wear in (16, 17) else "idle"
        _set_ear(state, left, right)
        if models.FEATURE_AMBIENT in spec.features:
            enabled = _u8(payload, 7) == 1
            state["mode"] = "ambient" if enabled else "off"
            state["ambient_volume"] = _u8(payload, 9)
        state["eq"] = _eq(_u8(payload, 11))
        if len(payload) > 13:
            state["touch_lock"] = bool(payload[12])
        elif len(payload) > 12:
            state["touch_lock"] = bool((payload[12] & 0xF0) >> 4)
        return

    left = _placement((payload[6] & 0xF0) >> 4)
    right = _placement(payload[6] & 0x0F)
    _set_ear(state, left, right)
    state["battery"]["case"] = _battery(_u8(payload, 7))

    if generation == "plus":
        enabled = _u8(payload, 8) == 1
        state["mode"] = "ambient" if enabled else "off"
        state["ambient_volume"] = _u8(payload, 9)
        state["gaming"] = _u8(payload, 10) == 1
        state["eq"] = _eq(_u8(payload, 11))
        state["touch_lock"] = bool(_u8(payload, 12))
        return

    # Buds Live and later share the first 21 bytes.
    state["gaming"] = _u8(payload, 8) == 1
    state["eq"] = _eq(_u8(payload, 9))
    touch = _u8(payload, 10) or 0
    if generation in {"buds2", "fe", "buds3"}:
        state["touch_lock"] = (touch & (1 << 7)) != 128
    else:
        state["touch_lock"] = touch == 1

    if generation == "live":
        state["mode"] = "anc" if _u8(payload, 12) == 1 else "off"
        return

    mode = models.BYTE_TO_MODE.get(_u8(payload, 12) or 0)
    if mode:
        state["mode"] = mode
    state["ambient_volume"] = _u8(payload, 23)

    color = _color(payload, 14) or _color(payload, 16)
    if color:
        key = models.identify_from_color(color)
        if key:
            apply_spec(state, models.spec_for(key))
            spec = models.spec_for(key)

    if generation == "pro":
        state["voice_detect"] = _bool(payload, 26)
        if len(payload) > 32:
            state["onebud"] = _u8(payload, 32) == 1
        return

    # Buds2, FE, 2 Pro, 3, 4: DetectConversations at 26, one-bud at 28.
    if len(payload) > 26:
        state["voice_detect"] = _u8(payload, 26) == 1
    if len(payload) > 28:
        state["onebud"] = _u8(payload, 28) == 1

    if generation == "buds2" and len(payload) > 36:
        _apply_charging(state, payload[36])
        return

    # FE and later: charging is the last byte of a 10-byte tail from offset 34.
    if len(payload) > 43:
        _apply_charging(state, payload[43])
    elif len(payload) >= 36:
        _apply_charging(state, payload[-1])


def _apply_charging(state: dict, status: int) -> None:
    state["charging"]["left"] = (status & 16) == 16
    state["charging"]["right"] = (status & 4) == 4
    state["charging"]["case"] = (status & 1) == 1


def parse_status_update(payload: bytes, spec: models.ModelSpec, state: dict) -> None:
    if len(payload) < 6:
        return
    if spec.generation == "buds":
        state["battery"]["left"] = _battery(_u8(payload, 1))
        state["battery"]["right"] = _battery(_u8(payload, 2))
        wear = _u8(payload, 5) or 0
        left = "wearing" if wear in (1, 17) else "idle"
        right = "wearing" if wear in (16, 17) else "idle"
        _set_ear(state, left, right)
        return
    state["battery"]["left"] = _battery(_u8(payload, 1))
    state["battery"]["right"] = _battery(_u8(payload, 2))
    if len(payload) > 5:
        left = _placement((payload[5] & 0xF0) >> 4)
        right = _placement(payload[5] & 0x0F)
        _set_ear(state, left, right)
    if len(payload) > 6:
        state["battery"]["case"] = _battery(payload[6])
    if spec.generation not in {"plus", "live"} and len(payload) > 7:
        mode = models.BYTE_TO_MODE.get(payload[7])
        if mode:
            state["mode"] = mode


def parse_sku(payload: bytes, state: dict) -> None:
    text = payload.split(b"\x00")[0].decode("ascii", errors="ignore")
    if not text:
        return
    key = models.identify_from_sku(text)
    if key:
        apply_spec(state, models.spec_for(key))
        return
    state["sku"] = text


def parse_version(payload: bytes, state: dict) -> None:
    text = payload.decode("ascii", errors="ignore")
    key = models.identify_from_sku(text)
    if key:
        apply_spec(state, models.spec_for(key))


@dataclass
class Session:
    spec: models.ModelSpec = field(default_factory=lambda: models.UNKNOWN)
    state: dict = field(default_factory=empty_state)

    def __post_init__(self) -> None:
        apply_spec(self.state, self.spec)
        self.state["connected"] = True

    def _encode(
        self, msg_id: int, payload: bytes = b"", msg_type: int = TYPE_REQUEST
    ) -> bytes:
        return encode(
            msg_id, payload, msg_type, legacy=uses_legacy_header(self.spec)
        )

    def observe(self, msg_id: int, payload: bytes) -> list[bytes]:
        """Update state from a device message. Return reply frames to send."""
        replies: list[bytes] = []
        if msg_id == EXTENDED_STATUS_UPDATED:
            parse_extended_status(payload, self.spec, self.state)
            self.spec = models.spec_for(self.state.get("model"))
            replies.append(self._encode(EXTENDED_STATUS_UPDATED, b"\x00", TYPE_RESPONSE))
            replies.append(self._encode(MANAGER_INFO, bytes([1, 2, 31]), TYPE_REQUEST))
        elif msg_id == STATUS_UPDATED:
            parse_status_update(payload, self.spec, self.state)
            replies.append(self._encode(STATUS_UPDATED, b"\x00", TYPE_RESPONSE))
        elif msg_id == DEBUG_SKU:
            parse_sku(payload, self.state)
            self.spec = models.spec_for(self.state.get("model"))
        elif msg_id == VERSION_INFO:
            parse_version(payload, self.state)
            self.spec = models.spec_for(self.state.get("model"))
            replies.append(self._encode(VERSION_INFO, b"\x00", TYPE_RESPONSE))
        elif msg_id == NOISE_CONTROLS_UPDATE and payload:
            mode = models.BYTE_TO_MODE.get(payload[0])
            if mode:
                self.state["mode"] = mode
        elif msg_id == AMBIENT_MODE_UPDATED and payload:
            self.state["mode"] = "ambient" if payload[0] == 1 else "off"
        elif msg_id == MUTE_EARBUD_STATUS_UPDATED:
            self.state["finding"] = True
        return replies

    def command(self, key: str, value: str) -> bytes | None:
        spec = self.spec
        if key == "mode":
            if value not in models.noise_modes_for(spec):
                return None
            if spec.generation == "buds" or (
                spec.generation == "plus" and value in {"off", "ambient"}
            ):
                frame = self._encode(
                    SET_AMBIENT_MODE, bytes([1 if value == "ambient" else 0])
                )
            elif spec.generation == "live":
                frame = self._encode(
                    SET_NOISE_REDUCTION, bytes([1 if value == "anc" else 0])
                )
            else:
                frame = self._encode(NOISE_CONTROLS, bytes([models.MODE_TO_BYTE[value]]))
            self.state["mode"] = value
            return frame
        if key == "eq":
            preset = models.eq_byte(value)
            if preset is None or models.FEATURE_EQ not in spec.features:
                return None
            if spec.generation == "buds":
                frame = self._encode(EQUALIZER, bytes([1, preset]))
            else:
                frame = self._encode(EQUALIZER, bytes([preset]))
            self.state["eq"] = value
            return frame
        if key == "touch_lock" and value in ("on", "off"):
            enabled = value == "on"
            self.state["touch_lock"] = enabled
            return self._encode(LOCK_TOUCHPAD, bytes([1 if enabled else 0]))
        if key == "find" and value in ("on", "off"):
            self.state["finding"] = value == "on"
            msg_id = FIND_MY_EARBUDS_START if value == "on" else FIND_MY_EARBUDS_STOP
            return self._encode(msg_id)
        if key == "gaming" and value in ("on", "off"):
            enabled = value == "on"
            self.state["gaming"] = enabled
            return self._encode(ADJUST_SOUND_SYNC, bytes([1 if enabled else 0]))
        if key == "ambient" and value.isdigit():
            volume = int(value)
            if volume < 0 or volume > spec.max_ambient_volume:
                return None
            self.state["ambient_volume"] = volume
            return self._encode(AMBIENT_VOLUME, bytes([volume]))
        if key == "voice_detect" and value in ("on", "off"):
            enabled = value == "on"
            self.state["voice_detect"] = enabled
            return self._encode(SET_DETECT_CONVERSATIONS, bytes([1 if enabled else 0]))
        if key == "onebud" and value in ("on", "off"):
            enabled = value == "on"
            self.state["onebud"] = enabled
            return self._encode(SET_ONE_EARBUD_ANC, bytes([1 if enabled else 0]))
        return None


def handshake_requests(spec: models.ModelSpec | None = None) -> list[bytes]:
    legacy = uses_legacy_header(spec)
    return [encode(DEBUG_SKU, legacy=legacy), encode(VERSION_INFO, legacy=legacy)]


def snapshot(state: dict) -> dict:
    """JSON-safe copy of the public watch line."""
    battery = state.get("battery") or {}
    charging = state.get("charging") or {}
    return {
        "connected": state.get("connected") is True,
        "address": state.get("address") or "",
        "name": state.get("name"),
        "model": state.get("model"),
        "sku": state.get("sku"),
        "mode": state.get("mode"),
        "battery": {
            "left": battery.get("left"),
            "right": battery.get("right"),
            "case": battery.get("case"),
        },
        "charging": {
            "left": bool(charging.get("left")),
            "right": bool(charging.get("right")),
            "case": bool(charging.get("case")),
        },
        "ear": list(state["ear"]) if state.get("ear") else None,
        "eq": state.get("eq"),
        "touch_lock": state.get("touch_lock"),
        "voice_detect": state.get("voice_detect"),
        "onebud": state.get("onebud"),
        "gaming": state.get("gaming"),
        "ambient_volume": state.get("ambient_volume"),
        "finding": bool(state.get("finding")),
        "features": list(state.get("features") or []),
    }
