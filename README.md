# Omabuds

Galaxy Buds noise control and battery in the [Omarchy](https://omarchy.org/) bar.

Standard Bluetooth profiles carry audio and the media keys, but they do not
carry noise control mode, per-bud battery, or in-ear status. Samsung sends
those over a vendor protocol on an RFCOMM serial channel. This plugin speaks
that protocol directly: the backend is Python on the standard library.
Nothing to compile, no systemd unit of its own, no companion app.

The plugin pauses the music when a bud comes out of your ear, and continues
it when the bud goes back in. The `earBehavior` setting picks the rule. The
plugin acts only on a player that it paused itself, and only while the buds
are the current audio output.

The panel shows, for the connected model:

- The device name and the model
- The battery level of each bud, and of the case when it reports one. A bolt
  marks a component that charges.
- Buttons for Off, Ambient, ANC, and Adaptive, with the current mode selected.
  Adaptive is absent on models that do not have it.
- Ambient volume while Ambient is the mode
- Equalizer presets
- Switches for Voice Detect, One-Bud ANC, touch lock, Find My Earbuds, and
  gaming / low-latency. A switch is omitted until the model reports the
  control.

The bar shows a buds icon with the battery level of the lowest bud. The
widget leaves the bar while no Galaxy Buds are connected. Volume, output
selection, and pairing stay in the stock Audio and Bluetooth panels.

## Requirements

- Omarchy Quattro with the schema version 1 plugin API
- Python 3.11 or newer (standard library only)
- BlueZ, including `bluetoothctl`

## Install

```bash
omarchy plugin add https://github.com/Hopelezz/omabuds.git --enable
```

To move the widget:

```bash
omarchy bar move io.github.hopelezz.omabuds --section right
```

## Do not run GalaxyBudsClient at the same time

The buds accept one SPP client. If
[GalaxyBudsClient](https://github.com/timschneeb/GalaxyBudsClient) holds the
channel, this plugin reads stale data and its commands are ignored. Use one
or the other.

## Command line

The backend works on its own:

```bash
~/.config/omarchy/plugins/io.github.hopelezz.omabuds/bin/omabuds watch
~/.config/omarchy/plugins/io.github.hopelezz.omabuds/bin/omabuds capture
~/.config/omarchy/plugins/io.github.hopelezz.omabuds/bin/omabuds selftest
```

`capture` prints every raw packet as hex, for building `selftest` fixtures.

`watch` holds the channel open and prints a line for each change, which is
what the panel runs:

```json
{"connected": true, "address": "…", "name": "Galaxy Buds FE", "model": "BudsFe",
 "sku": "SM-R400N", "mode": "anc", "battery": {"left": 80, "right": 78, "case": 60},
 "charging": {"left": false, "right": false, "case": true},
 "ear": ["wearing", "wearing"], "eq": "dynamic", "touch_lock": false,
 "voice_detect": null, "onebud": true, "gaming": false, "ambient_volume": 1,
 "features": ["anc", "ambient", "eq", "find", "touch_lock", "gaming", "onebud"]}
```

`watch` also takes `key value` commands on stdin: `mode anc`, `eq dynamic`,
`touch_lock on`, `find on`, `gaming off`, `ambient 2`, `voice_detect on`,
`onebud off`.

The bar starts one `watch` for each monitor, and the buds answer only the
first client. The copy that binds the abstract socket `omarchy-omabuds` opens
the channel; the others connect to it, print the lines it sends, and forward
their commands to it. That keeps the widget alive on every monitor.

A `null` value means the device has not reported it; the panel shows `—` or
omits the control. Putting one bud in the case disconnects the other bud on
some models, so the panel can go quiet mid-use.

## Interactions

- Bar icon: a click of any button toggles the panel.
- Low battery: a toast fires once when a bud in use drops to 20%, and again
  as critical at 10%. Charging or in-case buds are ignored. The next toast
  waits until the lowest bud is back above 30%.
- Panel: Tab and Shift+Tab move to the neighboring bar panel, Esc closes.
- IPC: `omarchy-shell shell summon io.github.hopelezz.omabuds '{}'` and
  `omarchy-shell shell hide io.github.hopelezz.omabuds`.

## Settings

The panel has a Settings section for these. A change writes to the widget's
entry in `~/.config/omarchy/shell.json`. The same keys take a value from the
command line:

```bash
omarchy bar set io.github.hopelezz.omabuds showBattery false --json
```

Booleans need `--json`; a bare value is stored as a string and reads as off.

| Key | Default | What it does |
|---|---|---|
| `showBattery` | `true` | Show the battery percent next to the bar icon |
| `earBehavior` | `One out` | When a bud out of your ear pauses the music: `One out`, `Both out`, or `Never` |

## Tested with

Galaxy Buds FE (`SM-R400N`) on Omarchy 4. Other Galaxy Buds models use the
same protocol family and are coded from their device specs, but they are not
hardware-tested here. Reports are welcome.

Coded models: Buds (2019), Buds+, Buds Live, Buds Pro, Buds2, Buds2 Pro,
Buds FE, Buds Core, Buds3, Buds3 FE, Buds3 Pro, Buds4, Buds4 Pro.

## Validation

```bash
./scripts/validate.sh
```

This runs Omarchy's plugin validator, `qmllint`, and the Python tests.

## Remove

```bash
omarchy plugin remove io.github.hopelezz.omabuds --yes
```

The plugin installs no service, privileged file, or Hyprland rule.

## Development

The live plugin folder is `~/.config/omarchy/plugins/io.github.hopelezz.omabuds`.
Point that path at this checkout (a directory symlink, same layout as omajelly)
so QML edits reload without copying. Python `watch` does not hot-reload; after
a helper change, restart the shell:

```bash
omarchy restart shell
```

## How it works

`bin/omabuds` finds a connected Galaxy Buds device, opens the Samsung SPP
RFCOMM channel, acknowledges status packets, and sends manager info so the
session stays alive. The buds answer with extended status (batteries, wear,
noise mode, EQ). Writing a control is one command packet on the same
channel, which is why `watch` reads commands from stdin.

## Credit

This plugin exists because of
[GalaxyBudsClient](https://github.com/timschneeb/GalaxyBudsClient) by Tim
Schneeb. That project did the hard part: it reverse-engineered Samsung's
RFCOMM protocol and wrote down what every packet means. The frame layout,
the message IDs, the extended-status field order, and the manager-info
handshake all come from reading its source and protocol notes.

No code was copied. The packet layouts are facts about Samsung's protocol,
and this plugin implements a small part of them in Python.

## License

MIT. See `LICENSE`.
