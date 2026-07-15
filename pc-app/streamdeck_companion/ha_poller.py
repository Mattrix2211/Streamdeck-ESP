"""Sondage periodique de Home Assistant pour les emplacements de type
widget (barre/texte) : relit l'etat des entites configurees toutes les
POLL_INTERVAL secondes et pousse la valeur formatee vers l'ecran via
device_client.schedule_push_values() (thread-safe, voir device_client.py).

Tourne dans son propre thread (voir tray.py) - un simple polling REST
suffit pour rafraichir une poignee de widgets, pas besoin de websocket.
"""

from __future__ import annotations

import logging
import threading

from . import ha_client as ha
from .device_client import DeviceClient

LOG = logging.getLogger("streamdeck_ha_poller")

POLL_INTERVAL = 15.0


def poll_once(device_client: DeviceClient) -> dict[int, str]:
    """Une passe de sondage. Retourne les valeurs poussees (utile pour les
    tests). Ne fait rien si Home Assistant n'est pas configure ou si le
    client n'est pas connecte a l'ecran."""
    config = device_client.config
    ha_conf = config.get("home_assistant") or {}
    client = ha.HomeAssistantClient(ha_conf.get("url", ""), ha_conf.get("token", ""))
    if not client.configured:
        return {}
    slots = config.get("slots") or []
    values: dict[int, str] = {}
    for idx, slot in enumerate(slots):
        if not slot:
            continue
        slot_type = slot.get("type", "bouton")
        if slot_type not in ("barre", "texte"):
            continue
        entity_id = (slot.get("source") or {}).get("entity_id")
        if not entity_id:
            continue
        try:
            state = client.get_state(entity_id)
        except Exception:
            LOG.exception("Echec de lecture de l'etat HA pour %s", entity_id)
            continue
        if state is None:
            continue
        values[idx] = ha.format_widget_value(state, slot_type)
    if values and device_client.connected:
        device_client.schedule_push_values(values)
    return values


def run_forever(device_client: DeviceClient, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            poll_once(device_client)
        except Exception:
            LOG.exception("Echec du sondage Home Assistant")
        stop_event.wait(POLL_INTERVAL)
