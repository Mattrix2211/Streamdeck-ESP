"""Popup tactile adaptee au type d'entite Home Assistant liee a un
emplacement (voir firmware/ha_popup_panel.yaml) - au lieu d'un tap qui
appelle directement le service configure, un emplacement `home_assistant`
cible une ampoule (`light`) ou un lecteur (`media_player`) ouvre un
mini-panneau avec les controles pertinents (allumer/eteindre ou lecture/
pause, curseur de luminosite/volume, precedent/suivant pour un lecteur).
Inspire des popups adaptatifs de github.com/GalusPeres/HomeTiles.

Meme esprit que color_mode.py (extrait de device_client.py, opere sur
l'instance DeviceClient qui le possede) : une seule popup a la fois,
entites optimistes cote firmware, filtrage des echos de nos propres
ecritures pour ne pas dupliquer les appels a Home Assistant.
"""

from __future__ import annotations

import logging
import time

from . import ha_client

LOG = logging.getLogger("streamdeck_client")

ACTIVE_SWITCH_NAME = "Popup HA actif"
POWER_SWITCH_NAME = "Popup HA - power"
TRANSPORT_SWITCH_NAME = "Popup HA - transport"
VALUE_NUMBER_NAME = "Popup HA - valeur"
TITLE_TEXT_NAME = "Popup HA - titre"

SUPPORTED_DOMAINS = ("light", "media_player")
MIN_INTERVAL = 0.12
TIMEOUT = 15.0


class HaPopupController:
    """Une instance par DeviceClient. `self.slot`/`self.entity` non-None
    signifie "popup actuellement ouverte" (comparable a color_mode.slot)."""

    def __init__(self, dc):
        self.dc = dc
        self.slot: int | None = None
        self.entity: str | None = None
        self.domain: str | None = None
        self.power = False
        self.value = 0.0
        self._last_sent = 0.0
        self.last_activity = 0.0

    def _client(self) -> ha_client.HomeAssistantClient:
        ha_conf = self.dc.config.get("home_assistant") or {}
        return ha_client.HomeAssistantClient(ha_conf.get("url", ""), ha_conf.get("token", ""))

    def open(self, slot_idx: int, action: dict) -> None:
        """Tap sur un emplacement `home_assistant` cible light/media_player
        (voir device_client.py::on_state) : lit l'etat initial pour
        preremplir la popup plutot que de l'ouvrir a zero."""
        target = action.get("target") or {}
        domain = target.get("domain")
        entity_id = target.get("entity_id")
        if domain not in SUPPORTED_DOMAINS or not entity_id:
            return
        self.dc.color_mode.exit()  # les deux panneaux ne s'affichent jamais ensemble

        title = entity_id
        power = False
        value = 0.0
        try:
            state = self._client().get_state(entity_id)
            if state:
                attrs = state.get("attributes") or {}
                title = attrs.get("friendly_name") or entity_id
                if domain == "light":
                    power = state.get("state") == "on"
                    brightness = attrs.get("brightness")
                    value = round(float(brightness) / 255 * 100) if brightness is not None else (100.0 if power else 0.0)
                else:
                    power = state.get("state") == "playing"
                    volume = attrs.get("volume_level")
                    value = round(float(volume) * 100) if volume is not None else 50.0
        except Exception:
            LOG.exception("Echec de lecture de l'etat initial pour la popup HA (%s)", entity_id)

        self.slot = slot_idx
        self.entity = entity_id
        self.domain = domain
        self.power = power
        self.value = value
        self._last_sent = 0.0
        self.last_activity = time.monotonic()
        self._push_all(title)

    def check_timeout(self) -> None:
        if self.slot is not None and time.monotonic() - self.last_activity > TIMEOUT:
            self.close()

    def close(self) -> None:
        self.slot = None
        self.entity = None
        self.domain = None
        self._push_switch(ACTIVE_SWITCH_NAME, False)

    def _push_all(self, title: str) -> None:
        if self.dc.client is None or not self.dc.connected:
            return
        self._push_text(TITLE_TEXT_NAME, title[:32])
        self._push_number(VALUE_NUMBER_NAME, self.value)
        self._push_switch(POWER_SWITCH_NAME, self.power)
        self._push_switch(TRANSPORT_SWITCH_NAME, self.domain == "media_player")
        self._push_switch(ACTIVE_SWITCH_NAME, True)

    def _push_switch(self, name: str, value: bool) -> None:
        key = self.dc.entity_keys.get(name)
        if key is not None:
            self.dc.client.switch_command(key, value)

    def _push_number(self, name: str, value: float) -> None:
        key = self.dc.entity_keys.get(name)
        if key is not None:
            self.dc.client.number_command(key, value)

    def _push_text(self, name: str, value: str) -> None:
        key = self.dc.entity_keys.get(name)
        if key is not None:
            self.dc.client.text_command(key, value)

    def handle_power(self, value: bool) -> None:
        """Bascule de l'interrupteur power/lecture de la popup (venant de
        l'ecran, voir device_client.py::on_state SwitchState) - ignore
        l'echo de notre propre _push_switch a l'ouverture."""
        if self.entity is None or value == self.power:
            return
        self.last_activity = time.monotonic()
        self.power = value
        try:
            if self.domain == "light":
                self._client().call_service("light", "turn_on" if value else "turn_off", entity_id=self.entity)
            else:
                self._client().call_service("media_player", "media_play" if value else "media_pause", entity_id=self.entity)
        except Exception:
            LOG.exception("Echec de la bascule power/lecture pour %s", self.entity)

    def handle_value(self, value: float) -> None:
        """Glissement du curseur luminosite/volume - meme filtrage d'echo
        et limite de frequence que color_mode.py::_send_update."""
        if self.entity is None or abs(value - self.value) < 0.5:
            return
        now = time.monotonic()
        if now - self._last_sent < MIN_INTERVAL:
            return
        self._last_sent = now
        self.last_activity = now
        self.value = value
        try:
            if self.domain == "light":
                self._client().call_service("light", "turn_on", entity_id=self.entity, data={"brightness_pct": int(value)})
            else:
                self._client().call_service(
                    "media_player", "volume_set", entity_id=self.entity, data={"volume_level": value / 100}
                )
        except Exception:
            LOG.exception("Echec du reglage valeur pour %s", self.entity)

    def handle_track(self, direction: str) -> None:
        if self.entity is None or self.domain != "media_player":
            return
        self.last_activity = time.monotonic()
        service = "media_next_track" if direction == "next" else "media_previous_track"
        try:
            self._client().call_service("media_player", service, entity_id=self.entity)
        except Exception:
            LOG.exception("Echec de %s pour %s", service, self.entity)
