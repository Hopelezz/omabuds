"""Hold one SPP channel and print a JSON line per change."""

from __future__ import annotations

import json
import os
import select
import socket
import sys
import time

from . import bluez, protocol

LOCK = "\0omarchy-omabuds"


def _emit_line(line: str, last: list[str], clients: list[socket.socket]) -> None:
    # Always write stdout so a bar Process that attached after the first
    # line still sees the current snapshot. Unix mirrors only need changes.
    print(line, flush=True)
    if line == last[0]:
        return
    last[0] = line
    for client in list(clients):
        try:
            client.sendall((line + "\n").encode())
        except OSError:
            clients.remove(client)
            client.close()


def _apply_commands(session: protocol.Session, sock: socket.socket, blob: bytes) -> None:
    if not blob:
        raise SystemExit(0)
    words = blob.decode(errors="ignore").split()
    for key, value in zip(words[::2], words[1::2]):
        frame = session.command(key, value)
        if frame:
            sock.sendall(frame)


def watch() -> None:
    while True:
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server.bind(LOCK)
            server.listen()
        except OSError:
            server.close()
            _mirror()
            continue
        with server:
            _own(server)


def _mirror() -> None:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(LOCK)
    except OSError:
        time.sleep(1)
        return
    with sock:
        while True:
            ready = select.select([sock, 0], [], [])[0]
            for source in ready:
                if source is sock:
                    lines = sock.recv(4096)
                    if not lines:
                        return
                    sys.stdout.write(lines.decode())
                    sys.stdout.flush()
                    continue
                command = os.read(0, 4096)
                if not command:
                    raise SystemExit(0)
                sock.sendall(command)


def _own(server: socket.socket) -> None:
    clients: list[socket.socket] = []
    last = [""]
    reader = protocol.FrameReader()

    def emit_state(state: dict) -> None:
        _emit_line(json.dumps(protocol.snapshot(state), separators=(",", ":")), last, clients)

    def _service_idle(timeout: float) -> None:
        ready = select.select([0, server] + clients, [], [], timeout)[0]
        for source in ready:
            if source is server:
                client, _ = server.accept()
                clients.append(client)
                if last[0]:
                    client.sendall((last[0] + "\n").encode())
            elif source == 0:
                command = os.read(0, 4096)
                if not command:
                    raise SystemExit(0)
            else:
                command = source.recv(4096)
                if not command:
                    clients.remove(source)
                    source.close()

    while True:
        found = bluez.find_buds()
        if not found:
            emit_state(protocol.empty_state())
            _service_idle(5)
            continue
        address, name, spec = found
        preview = protocol.connected_preview(
            address, name, spec, bluez.device_battery(address)
        )
        emit_state(preview)
        try:
            with bluez.open_channel(address, spec) as sock:
                reader.reset()
                session = protocol.Session(spec=spec)
                session.state["address"] = address
                session.state["name"] = name
                session.state["connected"] = True
                protocol.apply_spec(session.state, spec)
                for frame in protocol.handshake_requests(spec):
                    sock.sendall(frame)
                sock.settimeout(None)
                emit_state(session.state)
                while True:
                    ready = select.select([sock, 0, server] + clients, [], [], 3)[0]
                    if not ready and last[0]:
                        print(last[0], flush=True)
                        continue
                    for source in ready:
                        if source is sock:
                            chunk = sock.recv(1024)
                            if not chunk:
                                raise OSError("channel closed")
                            for packet in reader.feed(chunk):
                                decoded = protocol.decode_frame(packet)
                                if decoded is None:
                                    continue
                                _type, msg_id, payload = decoded
                                for reply in session.observe(msg_id, payload):
                                    sock.sendall(reply)
                            emit_state(session.state)
                        elif source is server:
                            client, _ = server.accept()
                            clients.append(client)
                            if last[0]:
                                client.sendall((last[0] + "\n").encode())
                        elif source == 0:
                            _apply_commands(session, sock, os.read(0, 4096))
                            emit_state(session.state)
                        else:
                            command = source.recv(4096)
                            if not command:
                                clients.remove(source)
                                source.close()
                                continue
                            _apply_commands(session, sock, command)
                            emit_state(session.state)
        except OSError:
            pass
        if bluez.find_buds():
            emit_state(preview)
            _service_idle(5)
            continue
        emit_state(protocol.empty_state())
        _service_idle(5)


def capture() -> None:
    found = bluez.find_buds()
    if not found:
        sys.exit("omabuds: no Galaxy Buds connected")
    address, _name, spec = found
    with bluez.open_channel(address, spec) as sock:
        for frame in protocol.handshake_requests(spec):
            sock.sendall(frame)
        sock.settimeout(None)
        while True:
            chunk = sock.recv(1024)
            if not chunk:
                return
            print(chunk.hex(), flush=True)


def selftest() -> None:
    from .selftest import run

    run()
