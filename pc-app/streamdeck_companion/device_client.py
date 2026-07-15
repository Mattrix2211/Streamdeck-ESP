"""Connexion persistante et directe au Stream Deck : ecoute les boutons et
encodeurs, execute les actions configurees localement (aucun code a ecrire,
tout se regle depuis la page de configuration - voir dashboard.py), et
pousse les libelles/la forme des boutons vers l'ecran en reutilisant CETTE
MEME connexion (pas de reconnexion separee a chaque changement).
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import yaml
from aioesphomeapi import APIClient, Event, EventInfo, SelectInfo, TextInfo

from . import actions as action_runner

LOG = logging.getLogger("streamdeck_client")

BUTTON_LABEL_NAMES = [f"Action {i} - libelle" for i in range(1, 13)]
SHAPE_ENTITY_NAME = "Forme des boutons"
ACTION_EVENT_ENTITY = "Bouton d'action ecran"
ENCODER_EVENT_ENTITIES = [f"Encodeur {i} - evenement" for i in range(1, 4)]
STATUS_ENTITY_NAME = "Statut PC"

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "dashboard_config.yaml"


def load_config(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_config(path: Path, config: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


class DeviceClient:
    """Une instance = une connexion persistante a l'ecran, vivant dans son
    propre thread/boucle asyncio (voir tray.py). La page de configuration
    (thread Flask separe) communique avec elle via `schedule_push()`, qui
    passe par asyncio.run_coroutine_threadsafe pour rester thread-safe."""

    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH):
        self.config_path = config_path
        self.config: dict = {}
        self.config_mtime: float | None = None
        self.client: APIClient | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.key_to_entity_name: dict[int, str] = {}
        self.entity_keys: dict[str, int] = {}  # nom d'entite (libelle/forme) -> key
        self.connected = False

    def _load_config(self) -> None:
        self.config = load_config(self.config_path)
        self.config_mtime = self.config_path.stat().st_mtime if self.config_path.exists() else None

    def reload_config_if_changed(self) -> None:
        if not self.config_path.exists():
            return
        mtime = self.config_path.stat().st_mtime
        if mtime != self.config_mtime:
            self._load_config()
            LOG.info("Configuration rechargee depuis %s", self.config_path)

    async def connect(self) -> None:
        self._load_config()
        conn = self.config.get("connection", {})
        self.client = APIClient(
            conn.get("host", ""),
            conn.get("port", 6053),
            "",
            noise_psk=conn.get("api_key") or None,
        )
        await self.client.connect(login=False)
        entities, _services = await self.client.list_entities_services()
        for ent in entities:
            if isinstance(ent, EventInfo) and ent.name in (ACTION_EVENT_ENTITY, *ENCODER_EVENT_ENTITIES):
                self.key_to_entity_name[ent.key] = ent.name
            if isinstance(ent, (TextInfo, SelectInfo)) and ent.name in (*BUTTON_LABEL_NAMES, SHAPE_ENTITY_NAME, STATUS_ENTITY_NAME):
                self.entity_keys[ent.name] = ent.key
        self.connected = True
        LOG.info("Connecte a %s (%d bouton/encodeur mappes)", conn.get("host"), len(self.key_to_entity_name))
        status_key = self.entity_keys.get(STATUS_ENTITY_NAME)
        if status_key is not None:
            self.client.text_command(status_key, "PC en ligne")

    def _resolve_action(self, entity_name: str, event_type: str) -> dict | None:
        if entity_name == ACTION_EVENT_ENTITY:
            try:
                idx = int(event_type.rsplit("_", 1)[1]) - 1  # "action_12" -> 11
            except (IndexError, ValueError):
                return None
            buttons = self.config.get("buttons", [])
            return buttons[idx] if 0 <= idx < len(buttons) else None
        if entity_name in ENCODER_EVENT_ENTITIES:
            enc_idx = ENCODER_EVENT_ENTITIES.index(entity_name)
            encoders = self.config.get("encoders", [])
            return encoders[enc_idx].get(event_type) if enc_idx < len(encoders) else None
        return None

    def on_state(self, state) -> None:
        if not isinstance(state, Event):
            return
        entity_name = self.key_to_entity_name.get(state.key)
        if entity_name is None:
            return
        action = self._resolve_action(entity_name, state.event_type)
        if not action or action.get("type", "none") == "none":
            return
        try:
            action_runner.run(action)
        except Exception:
            LOG.exception("Echec de l'action pour %s/%s : %r", entity_name, state.event_type, action)

    def push_labels_and_shape(self) -> None:
        """Pousse les libelles/la forme vers l'ecran via la connexion deja
        ouverte. Doit etre appelee depuis le thread/la boucle de cette
        instance (voir schedule_push pour un appel cross-thread)."""
        if self.client is None or not self.connected:
            raise RuntimeError("Pas encore connecte a l'ecran")
        buttons = self.config.get("buttons", [])
        for name, button in zip(BUTTON_LABEL_NAMES, buttons):
            key = self.entity_keys.get(name)
            label = (button or {}).get("label") or ""
            if key is not None and label:
                self.client.text_command(key, label[:24])
        shape = self.config.get("shape")
        shape_key = self.entity_keys.get(SHAPE_ENTITY_NAME)
        if shape and shape_key is not None:
            self.client.select_command(shape_key, shape)

    def schedule_push(self, timeout: float = 5.0) -> None:
        """Appelable depuis N'IMPORTE QUEL thread (ex: la page de config
        Flask) : programme push_labels_and_shape() sur la boucle asyncio de
        ce client et attend le resultat. Leve l'exception d'origine si ca
        echoue (connexion non etablie, etc.)."""
        if self.loop is None:
            raise RuntimeError("Le client n'a pas encore demarre sa boucle")
        future = asyncio.run_coroutine_threadsafe(self._push_async(), self.loop)
        future.result(timeout=timeout)

    async def _push_async(self) -> None:
        self.push_labels_and_shape()

    async def run_forever(self) -> None:
        self.loop = asyncio.get_running_loop()
        await self.connect()
        self.client.subscribe_states(self.on_state)
        try:
            while True:
                await asyncio.sleep(2)
                self.reload_config_if_changed()
        finally:
            self.connected = False
            status_key = self.entity_keys.get(STATUS_ENTITY_NAME)
            if status_key is not None:
                try:
                    self.client.text_command(status_key, "PC hors ligne")
                except Exception:
                    pass
            await self.client.disconnect()
