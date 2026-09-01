"""Parse-check fixtures with no Bluetooth."""

from __future__ import annotations

from . import models, protocol


def _fe_extended_payload() -> bytes:
    """Buds FE-shaped EXTENDED_STATUS_UPDATED payload (revision 2)."""
    payload = bytearray(44)
    payload[0] = 2
    payload[1] = 0
    payload[2] = 80
    payload[3] = 78
    payload[4] = 1
    payload[5] = 1
    payload[6] = (1 << 4) | 1  # both wearing
    payload[7] = 60
    payload[8] = 0  # gaming off
    payload[9] = 2  # dynamic
    payload[10] = 0
    payload[12] = models.MODE_TO_BYTE["anc"]
    payload[14] = 330 & 0xFF  # BudsFeGraphite
    payload[15] = 330 >> 8
    payload[16] = 330 & 0xFF
    payload[17] = 330 >> 8
    payload[23] = 1
    payload[26] = 1  # voice detect
    payload[28] = 1  # one-bud
    payload[43] = 0  # not charging
    return bytes(payload)


def run() -> None:
    encoded = protocol.encode(protocol.EQUALIZER, bytes([2]))
    decoded = protocol.decode_frame(encoded)
    assert decoded is not None, encoded.hex()
    msg_type, msg_id, payload = decoded
    assert msg_type == protocol.TYPE_REQUEST
    assert msg_id == protocol.EQUALIZER
    assert payload == bytes([2])

    reader = protocol.FrameReader()
    frames = reader.feed(encoded[:5] + encoded[5:])
    assert len(frames) == 1
    assert frames[0] == encoded

    spec = models.spec_for("BudsFe")
    session = protocol.Session(spec=spec)
    session.state["address"] = "AA:BB:CC:DD:EE:FF"
    replies = session.observe(protocol.EXTENDED_STATUS_UPDATED, _fe_extended_payload())
    assert replies, "extended status should be acknowledged"
    assert replies[0][3] == protocol.EXTENDED_STATUS_UPDATED
    assert replies[1][3] == protocol.MANAGER_INFO
    state = session.state
    assert state["battery"]["left"] == 80, state
    assert state["battery"]["right"] == 78, state
    assert state["battery"]["case"] == 60, state
    assert state["mode"] == "anc", state
    assert state["eq"] == "dynamic", state
    assert state["ear"] == ["wearing", "wearing"], state
    assert state["onebud"] is True, state
    assert state["model"] == "BudsFe", state
    assert "anc" in state["features"], state

    session.observe(
        protocol.STATUS_UPDATED,
        bytes([0, 40, 41, 1, 1, (2 << 4) | 1, 55]),
    )
    assert session.state["battery"]["left"] == 40, session.state
    assert session.state["ear"][0] == "idle", session.state

    frame = session.command("mode", "ambient")
    assert frame is not None
    decoded = protocol.decode_frame(frame)
    assert decoded is not None
    assert decoded[1] == protocol.NOISE_CONTROLS
    assert decoded[2] == bytes([models.MODE_TO_BYTE["ambient"]])
    assert session.state["mode"] == "ambient"

    frame = session.command("eq", "bass")
    assert frame is not None and protocol.decode_frame(frame)[2] == bytes([0])

    frame = session.command("find", "on")
    assert frame is not None and protocol.decode_frame(frame)[1] == protocol.FIND_MY_EARBUDS_START

    plus = protocol.Session(spec=models.spec_for("BudsPlus"))
    plus_payload = bytes(
        [
            11,
            0,
            70,
            71,
            1,
            0,
            (3 << 4) | 3,
            90,
            1,
            2,
            1,
            4,
            0,
            0,
        ]
    )
    plus.observe(protocol.EXTENDED_STATUS_UPDATED, plus_payload)
    assert plus.state["mode"] == "ambient", plus.state
    assert plus.state["gaming"] is True, plus.state
    assert plus.state["battery"]["case"] == 90, plus.state
    frame = plus.command("mode", "off")
    assert frame is not None
    assert protocol.decode_frame(frame)[1] == protocol.SET_AMBIENT_MODE

    live = protocol.Session(spec=models.spec_for("BudsLive"))
    live_payload = bytearray(20)
    live_payload[2] = 10
    live_payload[3] = 11
    live_payload[6] = (1 << 4) | 1
    live_payload[7] = 20
    live_payload[12] = 1
    live.observe(protocol.EXTENDED_STATUS_UPDATED, bytes(live_payload))
    assert live.state["mode"] == "anc", live.state
    frame = live.command("mode", "off")
    assert frame is not None
    assert protocol.decode_frame(frame)[1] == protocol.SET_NOISE_REDUCTION

    buds3 = models.spec_for("Buds3Pro")
    assert "adaptive" in buds3.features
    assert models.identify_from_sku("SM-R400NZKAEUD") == "BudsFe"
    assert models.identify_from_name("Galaxy Buds2 Pro") == "Buds2Pro"
    assert models.identify_from_color(330) == "BudsFe"
    assert protocol.snapshot(protocol.empty_state())["connected"] is False
    print("ok")
