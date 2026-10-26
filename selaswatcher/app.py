"""Menüleisten-App (rumps): Worker-Thread pollt, Main-Thread aktualisiert Menü/Icon.

Wiederverwendung des MVP-Kerns: poll_once() + notify_entry() bleiben unverändert.
Netz-I/O läuft NUR im Daemon-Worker-Thread; ALLE rumps-/Icon-/Menü-Mutationen
laufen NUR im Main-Thread (Timer-Callback). Übergabe neuer gemeldeter Einträge
vom Worker an den Main-Thread via queue.Queue.
"""

from __future__ import annotations

import logging
import queue
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Any, Callable

import objc
import rumps
from Foundation import NSObject

from .config import load_config
from .model import HIGH, Entry
from .notify import notify_entry
from .poller import poll_once
from .state import State

log = logging.getLogger(__name__)

# Icon-Pfade robust relativ zum Repo-Root auflösen — läuft so auch unter launchd
# (fremdes CWD). @2x-Varianten liegen daneben und werden von NSImage automatisch
# per initByReferencingFile_ für Retina gezogen.
_ICON_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"
TEMPLATE_ICON = str(_ICON_DIR / "selas-template.png")
ALERT_ICON = str(_ICON_DIR / "selas-alert.png")

APP_NAME = "SelasWATCHER"
MAX_RECENT = 30       # letzte gemeldete Einträge in der Menüliste
TITLE_LIMIT = 60      # Titel-Kürzung je Menüzeile
DRAIN_INTERVAL = 1.0  # s — Queue-Leerung im Main-Thread


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    return text[:limit].rstrip() + "…" if len(text) > limit else text


class _MenuOpenDelegate(NSObject):
    """NSMenu-Delegate: Alarm zurücksetzen, sobald der Nutzer das Menü öffnet."""

    def initWithCallback_(self, callback: Callable[[], None]):  # noqa: N802 (ObjC-Selektor)
        self = objc.super(_MenuOpenDelegate, self).init()
        if self is None:
            return None
        self._callback = callback
        return self

    def menuWillOpen_(self, menu):  # noqa: N802 (ObjC-Selektor), läuft im Main-Thread
        self._callback()


class _Worker(threading.Thread):
    """Daemon-Thread: endlos poll_once() -> warten -> wiederholen. Nie Main-Thread."""

    def __init__(
        self,
        config: dict[str, Any],
        state: State,
        out_queue: "queue.Queue[Entry]",
        poll_now: threading.Event,
    ) -> None:
        super().__init__(daemon=True)
        self.config = config
        self.state = state
        self.queue = out_queue
        self.poll_now = poll_now
        self.interval = int(config.get("poll_interval_seconds", 300))

    def run(self) -> None:
        while True:
            try:
                poll_once(self.config, self.state, notifier=self._notifier)
            except Exception as exc:  # Worker darf nie sterben (Regel #3)
                log.error("Poll-Zyklus fehlgeschlagen: %s", exc)
            # Bis zum nächsten Takt warten ODER bis "Jetzt prüfen" das Event setzt.
            self.poll_now.wait(timeout=self.interval)
            self.poll_now.clear()

    def _notifier(self, entry: Entry) -> bool:
        """Eigener notifier: OS-Notification wie gehabt UND Eintrag in die Queue."""
        sent = notify_entry(entry)
        # Entry wurde gemeldet (HIGH/MEDIUM, severity gesetzt) -> an Menüleiste geben,
        # unabhängig davon, ob die OS-Notification technisch durchkam.
        self.queue.put(entry)
        return sent


class SelasWatcherApp(rumps.App):
    """Menüleisten-App: Recent-Liste, Alarm-Zustand, Aktionen."""

    def __init__(self, config: dict[str, Any], state: State) -> None:
        super().__init__(APP_NAME, icon=TEMPLATE_ICON, template=True, quit_button=None)
        self.config = config
        self.state = state
        self.queue: "queue.Queue[Entry]" = queue.Queue()
        self.poll_now = threading.Event()  # "Jetzt prüfen" weckt den Worker
        self._recent: list[Entry] = []     # neueste zuerst, max MAX_RECENT
        self._unread_high = 0
        self._menu_delegate: _MenuOpenDelegate | None = None
        self._timer: rumps.Timer | None = None
        self._build_menu()
        self._install_menu_open_handler()
        self._refresh_alarm()

    # --- Menü-Aufbau -------------------------------------------------------

    def _format_entry(self, entry: Entry) -> str:
        bullet = "🔴" if entry.severity == HIGH else "•"
        return f"{bullet} {entry.source_name} — {_truncate(entry.title, TITLE_LIMIT)}"

    def _build_menu(self) -> None:
        """Menü komplett neu aufbauen (nur im Main-Thread aufrufen)."""
        self.menu.clear()
        # Recent-Einträge (neueste zuerst). Zero-Width-Space-Suffix hält die
        # Menü-Keys eindeutig, falls zwei Zeilen denselben Text ergeben.
        for i, entry in enumerate(self._recent):
            title = self._format_entry(entry) + ("​" * i)
            self.menu.add(rumps.MenuItem(title, callback=self._make_open(entry)))
        if self._recent:
            self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Jetzt prüfen", callback=self._on_check_now))
        self.menu.add(rumps.MenuItem("Alle als gelesen markieren", callback=self._on_mark_all_read))
        self.menu.add(rumps.MenuItem("Konfiguration öffnen", callback=self._on_open_config))
        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Beenden", callback=rumps.quit_application))

    def _install_menu_open_handler(self) -> None:
        """Alarm zurücksetzen, wenn das Menü geöffnet wird (NSMenu-Delegate)."""
        try:
            self._menu_delegate = _MenuOpenDelegate.alloc().initWithCallback_(self._reset_alarm)
            self.menu._menu.setDelegate_(self._menu_delegate)
        except Exception as exc:  # Fällt der Hook aus, bleiben die anderen Reset-Trigger
            log.warning("Menü-Öffnen-Handler nicht gesetzt: %s", exc)

    # --- Alarm-Zustand -----------------------------------------------------

    def _refresh_alarm(self) -> None:
        """Icon + Titel an die Zahl ungelesener HIGH-Treffer angleichen."""
        if self._unread_high > 0:
            self.template = False          # rote Alarm-Variante nicht tönen
            self.icon = ALERT_ICON
            self.title = f" {self._unread_high}"
        else:
            self.template = True           # Template-Icon: macOS tönt hell/dunkel
            self.icon = TEMPLATE_ICON
            self.title = None

    def _reset_alarm(self) -> None:
        self._unread_high = 0
        self._refresh_alarm()

    # --- Timer / Queue-Drain (Main-Thread) ---------------------------------

    def start_drain(self) -> None:
        self._timer = rumps.Timer(self._drain, DRAIN_INTERVAL)
        self._timer.start()

    def _drain(self, _timer: rumps.Timer) -> None:
        """Queue leeren, Recent-Liste + Icon/Menü aktualisieren (Main-Thread)."""
        added = False
        try:
            while True:
                entry = self.queue.get_nowait()
                self._recent.insert(0, entry)
                if entry.severity == HIGH:
                    self._unread_high += 1
                added = True
        except queue.Empty:
            pass
        if added:
            del self._recent[MAX_RECENT:]
            self._build_menu()
            self._refresh_alarm()

    # --- Menü-Callbacks ----------------------------------------------------

    def _make_open(self, entry: Entry) -> Callable[[rumps.MenuItem], None]:
        url = entry.url

        def _cb(_item: rumps.MenuItem) -> None:
            self._reset_alarm()
            if url:
                webbrowser.open(url)

        return _cb

    def _on_check_now(self, _item: rumps.MenuItem) -> None:
        self.poll_now.set()  # Worker sofort pollen lassen

    def _on_mark_all_read(self, _item: rumps.MenuItem) -> None:
        self._reset_alarm()

    def _on_open_config(self, _item: rumps.MenuItem) -> None:
        """Aktive config.toml öffnen, sonst ~/.selaswatcher/ im Finder zeigen."""
        # Reihenfolge wie in config.py: CWD vor ~/.selaswatcher/.
        for path in (Path.cwd() / "config.toml", Path.home() / ".selaswatcher" / "config.toml"):
            if path.is_file():
                subprocess.run(["open", str(path)])
                return
        target = Path.home() / ".selaswatcher"
        target.mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", str(target)])


def build_app(
    config: dict[str, Any] | None = None,
    state: State | None = None,
) -> SelasWatcherApp:
    """App + Menü aufbauen und zurückgeben — OHNE app.run(). Für Smoke-Test/Konstruktion."""
    config = config if config is not None else load_config()
    state = state if state is not None else State()
    return SelasWatcherApp(config, state)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    config = load_config()
    state = State()
    app = SelasWatcherApp(config, state)
    worker = _Worker(config, state, app.queue, app.poll_now)
    worker.start()
    app.start_drain()
    app.run()


if __name__ == "__main__":
    main()
