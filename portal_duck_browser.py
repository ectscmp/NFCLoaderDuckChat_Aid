from __future__ import annotations
import os

"""
portal_duck_browser_fixed.py

Listens for NFC portal state changes and loads the duck URL from the first
URL/link NDEF record into a single browser window.

This version fixes the pywebview main-thread requirement by running
webview.start() on the main thread and the portal manager in a background
thread.
"""

import argparse
import threading
import time
import webbrowser
from dataclasses import dataclass
from typing import Optional

from nfc_portal import NfcPortalManager, PortalState, run_simulator_input_loop

try:
    import webview  # type: ignore
except Exception:
    webview = None


DEFAULT_HOME_URL = "about:blank"
DEFAULT_POLL_INTERVAL = 0.20


@dataclass
class BrowserCommand:
    action: str
    url: Optional[str] = None


class SingleWindowBrowser:
    def __init__(self, title: str = "Duck Portal Browser", home_url: str = DEFAULT_HOME_URL):
        self.title = title
        self.home_url = home_url
        self._window = None
        self._window_ready = threading.Event()
        self._using_fallback = webview is None

    def start(self) -> None:
        """Start the browser UI. For pywebview this must run on the main thread."""
        if self._using_fallback:
            print("[browser] pywebview not installed; using default browser fallback.")
            self._window_ready.set()
            return

        self._window = webview.create_window(
            self.title, "file://" + os.path.abspath("default.html"), width=1200, height=900)
        self._window_ready.set()
        webview.start(debug=False)

    def load(self, url: str) -> None:
        self._window_ready.wait(timeout=10)

        if self._using_fallback:
            webbrowser.open(url, new=0, autoraise=True)
            print(f"[browser] Opened in default browser: {url}")
            return

        if self._window is None:
            print("[browser] Window not ready.")
            return

        try:
            self._window.load_url(url)
            print(f"[browser] Navigated to: {url}")
        except Exception as e:
            print(f"[browser] Failed to navigate: {e}")


class DuckPortalBrowserApp:
    def __init__(self, simulation_mode: bool = False, home_url: str = DEFAULT_HOME_URL):
        self.simulation_mode = simulation_mode
        self.browser = SingleWindowBrowser(home_url=home_url)
        self.manager = NfcPortalManager(
            poll_interval_seconds=DEFAULT_POLL_INTERVAL,
            on_tag_present=self.on_tag_present,
            on_state_changed=self.on_state_changed,
            simulation_mode=simulation_mode,
        )

        self._last_loaded_url: Optional[str] = None
        self._last_reader_url: dict[str, str] = {}
        self._lock = threading.Lock()

    def on_tag_present(self, state: PortalState) -> None:
        self._maybe_load_from_state(state)

    def on_state_changed(self, old_state: PortalState, new_state: PortalState) -> None:
        if not new_state.has_tag():
            with self._lock:
                # Clear remembered URL for this reader
                self._last_reader_url.pop(new_state.reader_name, None)

                # Since no duck is currently on this reader, clear global last-loaded
                # so the next duck placement is allowed to navigate.
                self._last_loaded_url = None

            if self.browser:
                self.browser.load("file://" + os.path.abspath("default.html"))

            return

        self._maybe_load_from_state(new_state)

    def _maybe_load_from_state(self, state: PortalState) -> None:
        url = state.first_url()
        if not url:
            return

        with self._lock:
            previous_for_reader = self._last_reader_url.get(state.reader_name)
            if previous_for_reader == url and self._last_loaded_url == url:
                return

            self._last_reader_url[state.reader_name] = url
            self._last_loaded_url = url

        print(
            f"[portal] reader={state.reader_name} duck={state.get_name()} id={state.get_id()} url={url}"
        )
        self.browser.load(url)

    def start_portal_threads(self) -> None:
        self.manager.start()

        if self.simulation_mode:
            threading.Thread(
                target=lambda: run_simulator_input_loop(self.manager),
                daemon=True,
            ).start()

        print("[app] Duck portal browser is running. Press Ctrl+C to quit.")

    def stop(self) -> None:
        self.manager.stop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open duck URLs from NFC portal tags in one browser window.")
    parser.add_argument("--sim", action="store_true",
                        help="Run in simulator mode.")
    parser.add_argument(
        "--home",
        default=DEFAULT_HOME_URL,
        help="Home page to show before a duck is loaded. Default: about:blank",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = DuckPortalBrowserApp(simulation_mode=args.sim, home_url=args.home)

    try:
        # Start the NFC/portal side in the background.
        threading.Thread(target=app.start_portal_threads, daemon=True).start()

        # Start the browser UI on the main thread.
        app.browser.start()
    except KeyboardInterrupt:
        print("\n[app] Stopping...")
        app.stop()


if __name__ == "__main__":
    main()
