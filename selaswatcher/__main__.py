"""CLI-Entrypoint: python -m selaswatcher {poll,watch,test-notify}."""

from __future__ import annotations

import argparse
import logging
import sys
import time

from .config import load_config
from .notify import notify_sample
from .poller import format_summary, poll_once
from .state import State


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def cmd_poll(args: argparse.Namespace) -> int:
    config = load_config()
    state = State()
    poll = poll_once(config, state)
    print(format_summary(poll))
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    config = load_config()
    state = State()
    interval = int(config.get("poll_interval_seconds", 300))
    logging.getLogger(__name__).info("watch: Intervall %ds", interval)
    while True:
        try:
            poll = poll_once(config, state)
            print(format_summary(poll), flush=True)
        except Exception as exc:  # watch läuft trotz Fehler weiter
            logging.getLogger(__name__).error("Poll-Zyklus fehlgeschlagen: %s", exc)
        time.sleep(interval)


def cmd_test_notify(args: argparse.Namespace) -> int:
    ok = notify_sample()
    print("Beispiel-HIGH-Notification gesendet." if ok else "Notification fehlgeschlagen.")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="selaswatcher", description="macOS-Frühwarn-Tool für Security-/IT-Bedrohungen.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug-Logging")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("poll", help="Ein Poll-Zyklus über alle aktivierten Quellen").set_defaults(func=cmd_poll)
    sub.add_parser("watch", help="Endlosschleife: poll alle poll_interval_seconds").set_defaults(func=cmd_watch)
    sub.add_parser("test-notify", help="Beispiel-HIGH-Notification feuern (ohne Netz)").set_defaults(func=cmd_test_notify)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _setup_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
