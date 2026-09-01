"""Protocol and model tests that do not need Bluetooth."""

from __future__ import annotations

import unittest

from omabuds import models, protocol
from omabuds.selftest import run


class SelftestTests(unittest.TestCase):
    def test_selftest(self) -> None:
        run()


class FrameTests(unittest.TestCase):
    def test_crc_roundtrip(self) -> None:
        frame = protocol.encode(protocol.LOCK_TOUCHPAD, bytes([1]))
        decoded = protocol.decode_frame(frame)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded[1], protocol.LOCK_TOUCHPAD)
        self.assertEqual(decoded[2], bytes([1]))

    def test_bad_crc_rejected(self) -> None:
        frame = bytearray(protocol.encode(protocol.EQUALIZER, bytes([3])))
        frame[5] ^= 0xFF
        self.assertIsNone(protocol.decode_frame(bytes(frame)))

    def test_partial_then_complete(self) -> None:
        frame = protocol.encode(protocol.FIND_MY_EARBUDS_STOP)
        reader = protocol.FrameReader()
        self.assertEqual(reader.feed(frame[:3]), [])
        self.assertEqual(len(reader.feed(frame[3:])), 1)

    def test_legacy_roundtrip(self) -> None:
        frame = protocol.encode(protocol.LOCK_TOUCHPAD, bytes([1]), legacy=True)
        self.assertEqual(frame[0], protocol.SOM_LEGACY)
        decoded = protocol.decode_frame(frame)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded[1], protocol.LOCK_TOUCHPAD)

    def test_buds_fe_capture(self) -> None:
        raw = bytes.fromhex(
            "fd33086103066363010111000003b92202004b014b010300046600010010"
            "00000000110200000000d0a30f00a0030f00e80000001f4add"
        )
        decoded = protocol.decode_frame(raw)
        self.assertIsNotNone(decoded)
        _type, msg_id, payload = decoded
        self.assertEqual(msg_id, protocol.EXTENDED_STATUS_UPDATED)
        spec = models.spec_for("BudsFe")
        session = protocol.Session(spec=spec)
        session.observe(msg_id, payload)
        self.assertEqual(session.state["battery"]["left"], 99)
        self.assertEqual(session.state["battery"]["right"], 99)
        self.assertEqual(session.state["model"], "BudsFe")
        self.assertEqual(session.state["ear"], ["wearing", "wearing"])


class ModelTests(unittest.TestCase):
    def test_name_order(self) -> None:
        self.assertEqual(models.identify_from_name("Galaxy Buds FE"), "BudsFe")
        self.assertEqual(models.identify_from_name("Galaxy Buds2 Pro"), "Buds2Pro")
        self.assertEqual(models.identify_from_name("Buds3 Pro"), "Buds3Pro")

    def test_noise_modes(self) -> None:
        fe = models.noise_modes_for(models.spec_for("BudsFe"))
        self.assertIn("anc", fe)
        self.assertNotIn("adaptive", fe)
        pro3 = models.noise_modes_for(models.spec_for("Buds3Pro"))
        self.assertIn("adaptive", pro3)


if __name__ == "__main__":
    unittest.main()
