from __future__ import annotations

import threading
from typing import Dict, Any, Optional

import requests

from nfc_portal import NfcPortalManager, run_simulator_input_loop, PortalState


DUCK_API_BASE = "https://api.ducks.ects-cmp.com/ducks"
DEFAULT_SIMULATION_MODE = False


class ReaderService:
    def __init__(self, simulation_mode: bool = DEFAULT_SIMULATION_MODE):
        self.simulation_mode = simulation_mode

        self.manager = NfcPortalManager(simulation_mode=simulation_mode)
        self.manager.start()

        self._duck_cache: Dict[str, Dict[str, Any]] = {}

        if self.simulation_mode:
            threading.Thread(
                target=lambda: run_simulator_input_loop(self.manager),
                daemon=True,
            ).start()

    def stop(self) -> None:
        self.manager.stop()

    def _fetch_full_duck(self, duck_id: str) -> Optional[Dict[str, Any]]:
        if not duck_id:
            return None

        if duck_id in self._duck_cache:
            return self._duck_cache[duck_id]

        try:
            resp = requests.get(f"{DUCK_API_BASE}/{duck_id}", timeout=5)
            if resp.ok:
                duck = resp.json()
                if isinstance(duck, dict):
                    self._duck_cache[duck_id] = duck
                    return duck
        except Exception as e:
            print(f"Failed to fetch duck {duck_id}: {e}")

        return None

    def _portal_state_to_duck(self, portal_state: Optional[PortalState]) -> Dict[str, Any]:
        if not portal_state or not portal_state.has_tag():
            return {
                "duck": None,
                "duck_id": None,
            }

        # First try full JSON directly from the tag
        duck_obj = portal_state.first_json()
        if isinstance(duck_obj, dict):
            duck_id = (
                duck_obj.get("_id")
                or duck_obj.get("duckId")
                or portal_state.get_id()
                or None
            )

            # If the tag JSON is incomplete, fetch the full duck
            if duck_id and (
                "body" not in duck_obj
                or "stats" not in duck_obj
            ):
                full_duck = self._fetch_full_duck(duck_id)
                if full_duck:
                    return {
                        "duck": full_duck,
                        "duck_id": duck_id,
                    }

            return {
                "duck": duck_obj,
                "duck_id": duck_id,
            }

        # Otherwise use ID/text/url from tag and fetch full duck
        duck_id = portal_state.get_id() or None
        if duck_id:
            full_duck = self._fetch_full_duck(duck_id)
            if full_duck:
                return {
                    "duck": full_duck,
                    "duck_id": duck_id,
                }

        return {
            "duck": None,
            "duck_id": None,
        }

    def get_state(self) -> Dict[str, Dict[str, Any]]:
        current_states = self.manager.get_current_states()

        left_state = current_states.get("SIM_LEFT")
        right_state = current_states.get("SIM_RIGHT")

        if left_state is None or right_state is None:
            states_list = list(current_states.values())
            left_state = states_list[0] if len(states_list) > 0 else None
            right_state = states_list[1] if len(states_list) > 1 else None

        return {
            "p1": self._portal_state_to_duck(left_state),
            "p2": self._portal_state_to_duck(right_state),
        }
