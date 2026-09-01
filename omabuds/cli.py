"""Omabuds command-line entry: watch, capture, selftest."""

from __future__ import annotations

import sys

from . import watch


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else "watch"
    if command == "selftest":
        watch.selftest()
        return 0
    if command == "capture":
        watch.capture()
        return 0
    if command != "watch":
        sys.stderr.write("omabuds: watch | capture | selftest\n")
        return 2
    watch.watch()
    return 0
