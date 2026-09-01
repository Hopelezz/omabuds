"""Watch socket security tests."""

from __future__ import annotations

import struct
import unittest
from unittest.mock import patch

from omabuds import watch


class _FakeClient:
    def __init__(self, uid: int) -> None:
        self.uid = uid
        self.closed = False
        self.sent: list[bytes] = []

    def getsockopt(self, _level: int, _optname: int, _size: int) -> bytes:
        return struct.pack("3i", 123, self.uid, 456)

    def sendall(self, data: bytes) -> None:
        self.sent.append(data)

    def close(self) -> None:
        self.closed = True


class _FakeServer:
    def __init__(self, client: _FakeClient) -> None:
        self.client = client

    def accept(self) -> tuple[_FakeClient, None]:
        return self.client, None


class WatchSecurityTests(unittest.TestCase):
    def test_accept_rejects_other_uid(self) -> None:
        clients: list[_FakeClient] = []
        activity: dict[_FakeClient, float] = {}
        client = _FakeClient(uid=9999)
        with patch("omabuds.watch.os.getuid", return_value=1000):
            watch._accept_client(_FakeServer(client), clients, activity, [""])
        self.assertTrue(client.closed)
        self.assertEqual(clients, [])

    def test_accept_evicts_oldest_at_capacity(self) -> None:
        stale = _FakeClient(uid=1000)
        clients: list[_FakeClient] = [stale]
        activity: dict[_FakeClient, float] = {stale: 10.0}
        newcomer = _FakeClient(uid=1000)
        with (
            patch("omabuds.watch.os.getuid", return_value=1000),
            patch("omabuds.watch.MAX_CLIENTS", 1),
            patch("omabuds.watch.time.monotonic", side_effect=[20.0, 21.0]),
        ):
            watch._accept_client(_FakeServer(newcomer), clients, activity, [""])
        self.assertTrue(stale.closed)
        self.assertEqual(clients, [newcomer])

    def test_expire_clients_closes_stale(self) -> None:
        stale = _FakeClient(uid=1000)
        fresh = _FakeClient(uid=1000)
        clients: list[_FakeClient] = [stale, fresh]
        activity: dict[_FakeClient, float] = {stale: 1.0, fresh: 100.0}
        with patch("omabuds.watch.CLIENT_TTL_SECONDS", 50.0):
            watch._expire_clients(clients, activity, now=120.0)
        self.assertTrue(stale.closed)
        self.assertFalse(fresh.closed)
        self.assertEqual(clients, [fresh])


if __name__ == "__main__":
    unittest.main()
