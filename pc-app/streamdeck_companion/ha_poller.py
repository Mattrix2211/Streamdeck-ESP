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
from . import weather as weather_module
from .device_client import DeviceClient

LOG = logging.getLogger("streamdeck_ha_poller")

POLL_INTERVAL = 15.0


def poll_once(device_client: DeviceClient) -> dict[int, str]:
    """Une passe de sondage. Retourne les valeurs poussees (utile pour les
    tests). Ne fait rien si Home Assistant n'est pas configure ou si le
    client n'est pas connecte a l'ecran. Lit les emplacements du profil
    ACTIF (pas d'un eventuel config['slots'] racine, qui n'existe plus
    depuis l'introduction des profils - voir profiles.py)."""
    config = device_client.config
    ha_conf = config.get("home_assistant") or {}
    client = ha.HomeAssistantClient(ha_conf.get("url", ""), ha_conf.get("token", ""))
    if not client.configured:
        return {}
    slots = device_client.active_profile().get("slots") or []
    values: dict[int, str] = {}
    colors: dict[int, str] = {}
    for idx, slot in enumerate(slots):
        if not slot:
            continue
        slot_type = slot.get("type", "bouton")
        if slot_type in ("barre", "texte"):
            entity_id = slot.get("ha_entity")
            if entity_id:
                try:
                    state = client.get_state(entity_id)
                except Exception:
                    LOG.exception("Echec de lecture de l'etat HA pour %s", entity_id)
                    state = None
                if state is not None:
                    values[idx] = ha.format_widget_value(state, slot_type)

        action = slot.get("action") or {}
        if action.get("type") == "home_assistant" and slot.get("show_light_color"):
            target = action.get("target") or {}
            entity_id = target.get("entity_id")
            if target.get("domain") == "light" and entity_id:
                try:
                    state = client.get_state(entity_id)
                except Exception:
                    LOG.exception("Echec de lecture de l'etat HA pour %s", entity_id)
                    state = None
                if state is not None:
                    colors[idx] = ha.light_color_hex(state)

    weather = device_client.active_profile().get("weather") or {}
    if weather.get("visible") and weather.get("entity"):
        try:
            info = weather_module.read_weather(client, weather["entity"])
        except Exception:
            LOG.exception("Echec de lecture de la carte meteo pour %s", weather.get("entity"))
            info = None
        if info is not None and device_client.connected:
            device_client.schedule_push_weather_display(
                info["icon_char"], info["animation_style"], info["temperature"]
            )

    if device_client.connected:
        if values:
            device_client.schedule_push_values(values)
        if colors:
            device_client.schedule_push_slot_colors(colors)
    return values


def run_forever(device_client: DeviceClient, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        try:
            poll_once(device_client)
        except Exception:
            LOG.exception("Echec du sondage Home Assistant")
        stop_event.wait(POLL_INTERVAL)
