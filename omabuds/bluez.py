"""Discover a connected Galaxy Buds device and open its SPP RFCOMM channel."""

from __future__ import annotations

import re
import socket
import subprocess
import time

from . import models, protocol

_DEVICE_RE = re.compile(r"Device\s+([0-9A-Fa-f:]{17})\s+(.+)$")
_BATTERY_RE = re.compile(r"Battery Percentage:\s*(?:0x[0-9A-Fa-f]+\s*)?\((\d+)\)")

# Samsung's vendor SPP is rarely RFCOMM 1. Buds FE on this machine answers on 20.
_NEW_CHANNELS = (20, 1, 2, 3, 26, 28, 29)
_LEGACY_CHANNELS = (1, 2, 3)
_SILENT_OK = {1, 2, 3, 20}


class RfcommChannel:
    """RFCOMM socket that can replay bytes consumed while probing for SOM."""

    def __init__(self, sock: socket.socket, pending: bytes = b"") -> None:
        self._sock = sock
        self._pending = pending

    def fileno(self) -> int:
        return self._sock.fileno()

    def recv(self, size: int) -> bytes:
        if self._pending:
            chunk = self._pending[:size]
            self._pending = self._pending[size:]
            return chunk
        return self._sock.recv(size)

    def sendall(self, data: bytes) -> None:
        self._sock.sendall(data)

    def settimeout(self, timeout: float | None) -> None:
        self._sock.settimeout(timeout)

    def close(self) -> None:
        self._sock.close()

    def __enter__(self) -> RfcommChannel:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _run(*args: str) -> str:
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=8,
    )
    return result.stdout or ""


def connected_devices() -> list[tuple[str, str]]:
    """Return (address, name) pairs for connected Bluetooth devices."""
    devices = []
    for line in _run("bluetoothctl", "devices", "Connected").splitlines():
        match = _DEVICE_RE.search(line.strip())
        if match:
            devices.append((match.group(1), match.group(2).strip()))
    return devices


def find_buds() -> tuple[str, str, models.ModelSpec] | None:
    """Return (address, name, spec) for the first connected Galaxy Buds."""
    for address, name in connected_devices():
        if not models.looks_like_buds(name):
            continue
        key = models.identify_from_name(name)
        spec = models.spec_for(key)
        return address, name, spec
    return None


def device_battery(address: str) -> int | None:
    """Headset battery percent from BlueZ, if the device exposes it."""
    text = _run("bluetoothctl", "info", address)
    match = _BATTERY_RE.search(text)
    if not match:
        return None
    percent = int(match.group(1))
    if percent > 100:
        return None
    return percent


def _sdp_channels(address: str) -> list[int]:
    """RFCOMM channels advertised for this device, if sdptool is present."""
    try:
        text = _run("sdptool", "browse", address)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    channels: list[int] = []
    for match in re.finditer(r"Channel:\s*(\d+)", text):
        channel = int(match.group(1))
        if channel not in channels:
            channels.append(channel)
    return channels


def _connect_channel(address: str, channel: int, timeout: float = 3.0) -> socket.socket:
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    sock.settimeout(timeout)
    sock.connect((address, channel))
    return sock


def _probe_spp(sock: socket.socket) -> bytes | None:
    """Return pending bytes if this looks like Samsung SPP.

    Empty bytes mean the socket is open but silent (handshake may still work).
    None means the channel spoke a different protocol and should be dropped.
    """
    sock.settimeout(1.2)
    try:
        data = sock.recv(64)
    except (TimeoutError, socket.timeout):
        return b""
    except OSError:
        return None
    if not data:
        return None
    if data[0] in (protocol.SOM_NEW, protocol.SOM_LEGACY):
        return data
    return None


def _channel_list(address: str, spec: models.ModelSpec) -> list[int]:
    channels = _sdp_channels(address)
    preferred = _LEGACY_CHANNELS if protocol.uses_legacy_header(spec) else _NEW_CHANNELS
    for channel in preferred:
        if channel not in channels:
            channels.append(channel)
    return channels


def open_channel(address: str, spec: models.ModelSpec) -> RfcommChannel:
    """Open RFCOMM to the buds. Prefer SDP, then known Samsung channels."""
    last_error: OSError | None = None
    for channel in _channel_list(address, spec):
        sock: socket.socket | None = None
        try:
            sock = _connect_channel(address, channel)
            pending = _probe_spp(sock)
            if pending is None:
                sock.close()
                continue
            if pending == b"" and channel not in _SILENT_OK:
                sock.close()
                continue
            sock.settimeout(None)
            return RfcommChannel(sock, pending)
        except OSError as error:
            last_error = error
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
    gio = _connect_profile_gio(address, spec.spp_uuid)
    if gio is not None:
        return gio
    if spec.spp_uuid != models.SPP_STANDARD:
        gio = _connect_profile_gio(address, models.SPP_STANDARD)
        if gio is not None:
            return gio
    raise last_error or OSError("could not open Galaxy Buds SPP channel")


def _connect_profile_gio(address: str, uuid: str) -> RfcommChannel | None:
    """Register as a BlueZ profile client and take the NewConnection fd."""
    try:
        import gi

        gi.require_version("Gio", "2.0")
        gi.require_version("GLib", "2.0")
        from gi.repository import Gio, GLib
    except (ImportError, ValueError):
        return None

    loop = GLib.MainLoop()
    result: dict[str, RfcommChannel | None] = {"sock": None}

    xml = """
    <node>
      <interface name="org.bluez.Profile1">
        <method name="Release"></method>
        <method name="NewConnection">
          <arg name="device" type="o" direction="in"/>
          <arg name="fd" type="h" direction="in"/>
          <arg name="fd_properties" type="a{sv}" direction="in"/>
        </method>
        <method name="RequestDisconnection">
          <arg name="device" type="o" direction="in"/>
        </method>
      </interface>
    </node>
    """

    def on_method(_connection, _sender, _path, _interface, method, parameters, invocation):
        if method == "NewConnection":
            message = invocation.get_message()
            fd_list = message.get_unix_fd_list() if message is not None else None
            _device, fd_handle, _props = parameters.unpack()
            raw_fd = None
            if fd_list is not None:
                try:
                    index = int(fd_handle)
                    raw_fd = fd_list.get(index)
                except (TypeError, ValueError, OSError):
                    raw_fd = None
            if raw_fd is None:
                try:
                    raw_fd = fd_handle.take() if hasattr(fd_handle, "take") else int(fd_handle)
                except (OSError, TypeError, ValueError):
                    raw_fd = None
            if raw_fd is not None:
                try:
                    sock = socket.fromfd(
                        raw_fd, socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM
                    )
                    sock.settimeout(None)
                    result["sock"] = RfcommChannel(sock)
                except OSError:
                    result["sock"] = None
            invocation.return_value(None)
            loop.quit()
            return
        invocation.return_value(None)

    try:
        bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        node = Gio.DBusNodeInfo.new_for_xml(xml)
        iface = node.interfaces[0]
        registration = bus.register_object(
            "/omarchy/omabuds/profile",
            iface,
            on_method,
            None,
            None,
        )
        proxy = Gio.DBusProxy.new_sync(
            bus,
            Gio.DBusProxyFlags.NONE,
            None,
            "org.bluez",
            "/org/bluez",
            "org.bluez.ProfileManager1",
            None,
        )
        options = {
            "Role": GLib.Variant("s", "client"),
            "AutoConnect": GLib.Variant("b", True),
        }
        try:
            proxy.call_sync(
                "RegisterProfile",
                GLib.Variant("(osa{sv})", ("/omarchy/omabuds/profile", uuid, options)),
                Gio.DBusCallFlags.NONE,
                4000,
                None,
            )
        except GLib.Error:
            pass
        device_path = "/org/bluez/hci0/dev_" + address.replace(":", "_").upper()
        device = Gio.DBusProxy.new_sync(
            bus,
            Gio.DBusProxyFlags.NONE,
            None,
            "org.bluez",
            device_path,
            "org.bluez.Device1",
            None,
        )
        try:
            device.call_sync(
                "ConnectProfile",
                GLib.Variant("(s)", (uuid,)),
                Gio.DBusCallFlags.NONE,
                8000,
                None,
            )
        except GLib.Error:
            pass
        GLib.timeout_add(4000, loop.quit)
        loop.run()
        bus.unregister_object(registration)
        return result["sock"]
    except Exception:
        return None


def wait_for_buds(poll_seconds: float = 5.0) -> tuple[str, str, models.ModelSpec] | None:
    found = find_buds()
    if found:
        return found
    time.sleep(poll_seconds)
    return find_buds()
